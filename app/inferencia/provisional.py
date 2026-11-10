"""Modelo provisional SOLO para desarrollo y pruebas: no está entrenado y sus resultados no significan nada."""
import numpy as np


class ModeloProvisional:
    nombre = "provisional"
    provisional = True

    def __init__(self, clases: list[str]):
        self.clases = clases
        self._pesos = np.random.default_rng(0).normal(size=(3, len(clases)))

    def predecir(self, tensor: np.ndarray) -> np.ndarray:
        medias = tensor.reshape(-1, 3).mean(axis=0)  # color medio de la imagen, en [-1, 1]
        logits = medias @ self._pesos * 4.0
        e = np.exp(logits - logits.max())
        return e / e.sum()
