"""Crea la base de datos del catálogo, carga las 7 clases y registra la versión del modelo.

Uso (desde la carpeta raíz del repositorio):
    python -m scripts.inicializar_datos
    python -m scripts.inicializar_datos --metrics docs/modelo_v2/metrics.json --epocas 40
"""
import argparse
from pathlib import Path

from app.config import settings
from app.db import catalogo


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=settings.catalog_db, help="Ruta de la base SQLite del catálogo")
    p.add_argument("--metrics", default="docs/modelo_v2/metrics.json", help="metrics.json del cuaderno")
    p.add_argument("--epocas", type=int, default=40, help="Épocas realmente entrenadas (fase 1 + fase 2)")
    p.add_argument("--ruta-modelo", default=settings.model_path, help="Ruta del archivo .keras")
    p.add_argument("--arquitectura", default="MobileNetV2")
    a = p.parse_args()

    conn = catalogo.conectar(a.db)
    try:
        catalogo.crear_esquema(conn)
        catalogo.cargar_catalogo(conn)
        print(f"Catálogo listo en {a.db}: {len(catalogo.listar_lesiones(conn))} clases.")
        if Path(a.metrics).exists():
            datos = catalogo.leer_metrics_json(a.metrics)
            id_version = catalogo.registrar_version_modelo(
                conn, arquitectura=a.arquitectura, fecha=datos["fecha"], epocas=a.epocas,
                hiperparametros=datos["hiperparametros"], ruta_archivo=a.ruta_modelo,
                globales=datos["globales"], por_clase=datos["por_clase"],
            )
            print(f"Versión del modelo registrada (id {id_version}) con las métricas de {a.metrics}.")
        else:
            print(f"No se encontró {a.metrics}: no se registró ninguna versión del modelo.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
