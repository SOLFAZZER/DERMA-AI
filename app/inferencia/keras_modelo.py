"""Modelo real: la CNN MobileNetV2 entrenada (formato .keras). TensorFlow se importa solo aquí."""
import logging
from pathlib import Path

import numpy as np

from app.inferencia.base import InferenciaNoDisponible

log = logging.getLogger("derma.keras")


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
        self._tf = tf
        self._modelo = tf.keras.models.load_model(ruta, compile=False)
        salida = self._modelo.output_shape[-1]
        if salida != len(clases):
            raise InferenciaNoDisponible(f"El modelo tiene {salida} clases y class_names.json tiene {len(clases)}.")
        self.clases = clases
        self.nombre = Path(ruta).name
        self._gradcam_listo = self._preparar_gradcam()
        self.predecir(np.zeros((1, 224, 224, 3), dtype=np.float32))  # calentamiento
        if self._gradcam_listo:
            try:
                self.mapa_calor(np.zeros((1, 224, 224, 3), dtype=np.float32), 0)
            except Exception:  # el modelo sirve para clasificar aunque Grad-CAM no funcione
                log.exception("Grad-CAM no funciona con este modelo; se desactiva el mapa de calor.")
                self._gradcam_listo = False

    def predecir(self, tensor: np.ndarray) -> np.ndarray:
        return np.asarray(self._modelo(tensor, training=False))[0]

    # ------------------------------------------------------------------ Grad-CAM (C06)

    def _preparar_gradcam(self) -> bool:
        """Separa la red en 'cuerpo convolucional' y 'cabeza' para poder derivar la salida
        respecto al último mapa de características (en MobileNetV2, la capa `out_relu`)."""
        tf = self._tf
        capas = self._modelo.layers
        for i, capa in enumerate(capas):
            if isinstance(capa, tf.keras.Model):  # el MobileNetV2 va anidado dentro del modelo
                self._cuerpo = capa
                self._previas = capas[i + 1:-1]   # GAP, Dropout, ...
                self._ultima = capas[-1]           # Dense con softmax
                return True
        log.warning("No se encontró un cuerpo convolucional anidado: Grad-CAM desactivado.")
        return False

    def mapa_calor(self, tensor: np.ndarray, indice_clase: int) -> np.ndarray:
        """Mapa Grad-CAM de la clase indicada: matriz pequeña (7x7 en MobileNetV2) con valores de 0 a 1."""
        if not self._gradcam_listo:
            raise RuntimeError("Grad-CAM no está disponible para este modelo.")
        if not 0 <= indice_clase < len(self.clases):
            raise ValueError("Clase fuera de rango.")
        tf = self._tf
        entrada = tf.convert_to_tensor(tensor, dtype=tf.float32)
        with tf.GradientTape() as cinta:
            mapas = self._cuerpo(entrada, training=False)  # (1, 7, 7, 1280)
            cinta.watch(mapas)
            x = mapas
            for capa in self._previas:
                x = capa(x, training=False)
            # Se usa la salida ANTES del softmax: con un resultado muy seguro, el softmax
            # satura y su gradiente se anula, y el mapa saldría vacío.
            if isinstance(self._ultima, tf.keras.layers.Dense):
                z = tf.matmul(x, self._ultima.kernel)
                if self._ultima.use_bias:
                    z = z + self._ultima.bias
            else:
                z = self._ultima(x, training=False)
            puntaje = z[:, indice_clase]
        grad = cinta.gradient(puntaje, mapas)
        pesos = tf.reduce_mean(grad, axis=(1, 2), keepdims=True)
        cam = tf.nn.relu(tf.reduce_sum(pesos * mapas, axis=-1))[0].numpy()
        maximo = float(cam.max())
        return cam / maximo if maximo > 0 else np.zeros_like(cam)
