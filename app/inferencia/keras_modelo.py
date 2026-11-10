"""Modelo real: la CNN MobileNetV2 entrenada (formato .keras). TensorFlow se importa solo aquí."""
from pathlib import Path

import numpy as np

from app.inferencia.base import InferenciaNoDisponible


class ModeloKeras:
    provisional = False

    def __init__(self, ruta: str, clases: list[str]):
        if not Path(ruta).is_file():
            raise InferenciaNoDisponible(f"No se encontró el modelo en {ruta}.")
        try:
            import tensorflow as tf
        except ImportError as e:
            raise InferenciaNoDisponible(
                "TensorFlow no está instalado (usa Python 3.10 a 3.13 y requirements-ml.txt)."
            ) from e
        self._modelo = tf.keras.models.load_model(ruta, compile=False)
        salida = self._modelo.output_shape[-1]
        if salida != len(clases):
            raise InferenciaNoDisponible(f"El modelo tiene {salida} clases y class_names.json tiene {len(clases)}.")
        self.clases = clases
        self.nombre = Path(ruta).name
        self.predecir(np.zeros((1, 224, 224, 3), dtype=np.float32))  # calentamiento

    def predecir(self, tensor: np.ndarray) -> np.ndarray:
        return np.asarray(self._modelo(tensor, training=False))[0]
