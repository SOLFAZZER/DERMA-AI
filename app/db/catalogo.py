"""Capa de datos (C08): catálogo de lesiones y versiones del modelo, sobre SQLite.

Durante la operación la API solo lee (I08). La escritura ocurre al inicializar los datos
(script `scripts/inicializar_datos.py`) y al registrar una versión del modelo.
"""
import json
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")

# Catálogo de las 7 clases de HAM10000 (según el documento de diseño de la base de datos).
CLASES = [
    ("MEL", "Melanoma",
     "Tumor maligno de los melanocitos; la clase más importante a detectar por su gravedad.", "maligno"),
    ("NV", "Nevus melanocítico",
     "Lunar común, generalmente benigno, formado por un cúmulo de melanocitos.", "benigno"),
    ("BCC", "Carcinoma basocelular",
     "Cáncer de piel de crecimiento lento, el más frecuente, rara vez mortal.", "maligno"),
    ("AKIEC", "Queratosis actínica",
     "Lesión causada por exposición solar prolongada, con potencial de evolucionar a carcinoma.",
     "premaligno"),
    ("BKL", "Queratosis benigna",
     "Lesión benigna de la piel relacionada con la edad, sin potencial canceroso.", "benigno"),
    ("DF", "Dermatofibroma",
     "Nódulo cutáneo benigno, firme, de causa habitualmente desconocida.", "benigno"),
    ("VASC", "Lesión vascular",
     "Alteración benigna de los vasos sanguíneos de la piel (p. ej. angiomas).", "benigno"),
]


def conectar(ruta, solo_lectura: bool = False) -> sqlite3.Connection:
    """Abre la base de datos. Con `solo_lectura=True` la abre en modo de solo lectura."""
    if str(ruta) == ":memory:":
        conn = sqlite3.connect(":memory:")
    elif solo_lectura:
        uri = Path(ruta).resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(ruta, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def crear_esquema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()


def cargar_catalogo(conn: sqlite3.Connection) -> None:
    """Inserta las 7 clases. Se puede ejecutar varias veces: no duplica."""
    conn.executemany(
        "INSERT OR IGNORE INTO clase_lesion (codigo, nombre_clase, descripcion, nivel_riesgo) "
        "VALUES (?, ?, ?, ?)",
        CLASES,
    )
    conn.commit()


# ---------------------------------------------------------------- consultas (I08)

def listar_lesiones(conn: sqlite3.Connection) -> list[dict]:
    filas = conn.execute(
        "SELECT codigo, nombre_clase, descripcion, nivel_riesgo FROM clase_lesion ORDER BY id_clase"
    ).fetchall()
    return [
        {"codigo": f["codigo"], "nombre": f["nombre_clase"],
         "descripcion": f["descripcion"], "nivel_riesgo": f["nivel_riesgo"]}
        for f in filas
    ]


def consultar_lesion(conn: sqlite3.Connection, codigo: str) -> dict | None:
    f = conn.execute(
        "SELECT codigo, nombre_clase, descripcion, nivel_riesgo FROM clase_lesion WHERE codigo = ?",
        (codigo.upper(),),
    ).fetchone()
    if f is None:
        return None
    return {"codigo": f["codigo"], "nombre": f["nombre_clase"],
            "descripcion": f["descripcion"], "nivel_riesgo": f["nivel_riesgo"]}


def version_activa(conn: sqlite3.Connection) -> dict | None:
    """Versión activa del modelo con sus métricas globales y por clase."""
    v = conn.execute(
        "SELECT id_version, nombre_arquitectura, fecha_entrenamiento, num_epoca, "
        "hiperparametros, ruta_archivo, estado FROM version_modelo "
        "WHERE estado = 'activo' ORDER BY id_version DESC LIMIT 1"
    ).fetchone()
    if v is None:
        return None
    g = conn.execute(
        "SELECT exactitud, precision, sensibilidad, f1, fecha_calculo FROM vw_metricas_globales "
        "WHERE id_version = ? ORDER BY fecha_calculo DESC LIMIT 1",
        (v["id_version"],),
    ).fetchone()
    por_clase = conn.execute(
        "SELECT c.codigo, m.precision, m.sensibilidad, m.f1 FROM metrica_evaluacion m "
        "JOIN clase_lesion c ON c.id_clase = m.id_clase WHERE m.id_version = ? ORDER BY c.id_clase",
        (v["id_version"],),
    ).fetchall()
    return {
        "id": v["id_version"],
        "arquitectura": v["nombre_arquitectura"],
        "fecha_entrenamiento": v["fecha_entrenamiento"],
        "epocas": v["num_epoca"],
        "hiperparametros": json.loads(v["hiperparametros"]) if v["hiperparametros"] else None,
        "estado": v["estado"],
        "metricas": None if g is None else {
            "exactitud": g["exactitud"], "precision": g["precision"],
            "sensibilidad": g["sensibilidad"], "f1": g["f1"], "fecha_calculo": g["fecha_calculo"],
            "por_clase": [
                {"codigo": f["codigo"], "precision": f["precision"],
                 "sensibilidad": f["sensibilidad"], "f1": f["f1"]}
                for f in por_clase
            ],
        },
    }


# ---------------------------------------------------------------- escritura

def registrar_version_modelo(conn: sqlite3.Connection, *, arquitectura: str, fecha: str,
                             epocas: int, hiperparametros: dict | None, ruta_archivo: str,
                             globales: dict, por_clase: dict[str, dict]) -> int:
    """Registra una versión del modelo como activa y archiva las anteriores.

    `globales`: exactitud, precision, sensibilidad y f1.
    `por_clase`: {codigo: {precision, sensibilidad, f1}}.
    Si ya existe la misma versión (misma arquitectura, fecha y ruta), devuelve su id.
    """
    existente = conn.execute(
        "SELECT id_version FROM version_modelo WHERE nombre_arquitectura = ? "
        "AND fecha_entrenamiento = ? AND ruta_archivo = ?",
        (arquitectura, fecha, ruta_archivo),
    ).fetchone()
    if existente:
        return existente["id_version"]
    conn.execute("UPDATE version_modelo SET estado = 'archivado' WHERE estado = 'activo'")
    cur = conn.execute(
        "INSERT INTO version_modelo (nombre_arquitectura, fecha_entrenamiento, num_epoca, "
        "hiperparametros, ruta_archivo, estado) VALUES (?, ?, ?, ?, ?, 'activo')",
        (arquitectura, fecha, epocas,
         json.dumps(hiperparametros, ensure_ascii=False) if hiperparametros else None, ruta_archivo),
    )
    id_version = cur.lastrowid
    conn.execute(
        "INSERT INTO metrica_evaluacion (id_version, id_clase, exactitud, precision, sensibilidad, "
        "f1, fecha_calculo) VALUES (?, NULL, ?, ?, ?, ?, ?)",
        (id_version, globales["exactitud"], globales["precision"], globales["sensibilidad"],
         globales["f1"], fecha),
    )
    for codigo, m in por_clase.items():
        fila = conn.execute("SELECT id_clase FROM clase_lesion WHERE codigo = ?", (codigo,)).fetchone()
        if fila is None:
            raise ValueError(f"La clase {codigo} no está en el catálogo")
        conn.execute(
            "INSERT INTO metrica_evaluacion (id_version, id_clase, exactitud, precision, "
            "sensibilidad, f1, fecha_calculo) VALUES (?, ?, NULL, ?, ?, ?, ?)",
            (id_version, fila["id_clase"], m["precision"], m["sensibilidad"], m["f1"], fecha),
        )
    conn.commit()
    return id_version


def leer_metrics_json(ruta) -> dict:
    """Convierte el `metrics.json` del cuaderno de Colab al formato de `registrar_version_modelo`.

    Las métricas globales usan el promedio ponderado (decisión del líder del proyecto).
    """
    m = json.loads(Path(ruta).read_text(encoding="utf-8"))
    return {
        "fecha": m["fecha"],
        "hiperparametros": m.get("hiperparametros"),
        "globales": {
            "exactitud": m["exactitud"], "precision": m["precision_ponderada"],
            "sensibilidad": m["sensibilidad_ponderada"], "f1": m["f1_ponderada"],
        },
        "por_clase": {
            codigo: {"precision": v["precision"], "sensibilidad": v["recall"], "f1": v["f1-score"]}
            for codigo, v in m["por_clase"].items()
        },
    }
