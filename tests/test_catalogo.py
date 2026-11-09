import json
import sqlite3

import pytest

from app.db import catalogo

CODIGOS = {"MEL", "NV", "BCC", "AKIEC", "BKL", "DF", "VASC"}
GLOBALES = {"exactitud": 0.799, "precision": 0.821, "sensibilidad": 0.799, "f1": 0.808}
POR_CLASE = {"MEL": {"precision": 0.39, "sensibilidad": 0.56, "f1": 0.46},
             "NV": {"precision": 0.93, "sensibilidad": 0.89, "f1": 0.91}}


@pytest.fixture
def conn():
    c = catalogo.conectar(":memory:")
    catalogo.crear_esquema(c)
    catalogo.cargar_catalogo(c)
    yield c
    c.close()


def registrar(conn, fecha="2026-11-05", ruta="models/m.keras"):
    return catalogo.registrar_version_modelo(
        conn, arquitectura="MobileNetV2", fecha=fecha, epocas=40, hiperparametros={"lr": 1e-4},
        ruta_archivo=ruta, globales=GLOBALES, por_clase=POR_CLASE)


def test_catalogo_tiene_las_7_clases(conn):
    assert {x["codigo"] for x in catalogo.listar_lesiones(conn)} == CODIGOS


def test_cargar_catalogo_no_duplica(conn):
    catalogo.cargar_catalogo(conn)
    catalogo.cargar_catalogo(conn)
    assert len(catalogo.listar_lesiones(conn)) == 7


def test_consultar_lesion(conn):
    mel = catalogo.consultar_lesion(conn, "mel")
    assert mel["nivel_riesgo"] == "maligno"
    assert catalogo.consultar_lesion(conn, "XX") is None


def test_nivel_de_riesgo_invalido_se_rechaza(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO clase_lesion (codigo, nombre_clase, descripcion, nivel_riesgo) "
                     "VALUES ('X', 'x', 'x', 'raro')")


def test_llave_foranea_se_respeta(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO metrica_evaluacion (id_version, fecha_calculo) VALUES (999, '2026-11-05')")


def test_sin_version_no_hay_modelo_activo(conn):
    assert catalogo.version_activa(conn) is None


def test_registrar_version_y_leer_metricas(conn):
    registrar(conn)
    v = catalogo.version_activa(conn)
    assert v["arquitectura"] == "MobileNetV2" and v["estado"] == "activo"
    assert v["hiperparametros"] == {"lr": 1e-4}
    assert v["metricas"]["exactitud"] == pytest.approx(0.799)
    assert [c["codigo"] for c in v["metricas"]["por_clase"]] == ["MEL", "NV"]


def test_nueva_version_archiva_la_anterior(conn):
    id1 = registrar(conn, fecha="2026-11-04", ruta="models/v1.keras")
    id2 = registrar(conn, fecha="2026-11-05", ruta="models/v2.keras")
    assert catalogo.version_activa(conn)["id"] == id2
    estado = conn.execute("SELECT estado FROM version_modelo WHERE id_version = ?", (id1,)).fetchone()[0]
    assert estado == "archivado"


def test_registrar_la_misma_version_no_duplica(conn):
    assert registrar(conn) == registrar(conn)
    assert conn.execute("SELECT COUNT(*) FROM version_modelo").fetchone()[0] == 1


def test_clase_desconocida_se_rechaza(conn):
    with pytest.raises(ValueError):
        catalogo.registrar_version_modelo(
            conn, arquitectura="X", fecha="2026-11-05", epocas=1, hiperparametros=None,
            ruta_archivo="r", globales=GLOBALES, por_clase={"ZZZ": POR_CLASE["MEL"]})


def test_leer_metrics_json(tmp_path):
    datos = {"fecha": "2026-11-05", "exactitud": 0.799, "precision_ponderada": 0.82,
             "sensibilidad_ponderada": 0.799, "f1_ponderada": 0.808, "hiperparametros": {"batch": 32},
             "por_clase": {"MEL": {"precision": 0.39, "recall": 0.56, "f1-score": 0.46, "support": 146}}}
    ruta = tmp_path / "metrics.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    r = catalogo.leer_metrics_json(ruta)
    assert r["globales"]["f1"] == 0.808
    assert r["por_clase"]["MEL"]["sensibilidad"] == 0.56
