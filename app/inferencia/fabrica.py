"""Creación del modelo según la configuración (patrón Factory Method)."""
import json
from pathlib import Path

from app.config import settings
from app.inferencia.base import InferenciaNoDisponible, ModeloClasificador
from app.inferencia.keras_modelo import ModeloKeras
from app.inferencia.provisional import ModeloProvisional


def leer_clases(ruta: str) -> list[str]:
    try:
        clases = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise InferenciaNoDisponible(f"No se pudo leer {ruta}.") from e
    if not isinstance(clases, list) or not clases or not all(isinstance(c, str) for c in clases):
        raise InferenciaNoDisponible(f"{ruta} debe ser una lista de códigos de clase.")
    return clases


def crear_modelo(modo: str | None = None, ruta_modelo: str | None = None,
                 ruta_clases: str | None = None) -> ModeloClasificador:
    modo = (modo or settings.modelo_modo).strip().lower()
    clases = leer_clases(ruta_clases or settings.class_names_path)
    if modo == "keras":
        return ModeloKeras(ruta_modelo or settings.model_path, clases)
    if modo == "provisional":
        return ModeloProvisional(clases)
    raise ValueError(f"Modo de modelo desconocido: {modo!r} (usa 'keras' o 'provisional').")
