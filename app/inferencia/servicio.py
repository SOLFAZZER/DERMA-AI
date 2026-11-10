"""Servicio de inferencia (C05). Es la fachada (patrón Facade) que usa el servidor web: interfaz I07."""
import logging
import threading
from dataclasses import dataclass, field

import numpy as np

from app.config import settings
from app.inferencia.base import (
    InferenciaNoDisponible,
    ModeloClasificador,
    ServicioOcupado,
)

FORMA_ENTRADA = (1, 224, 224, 3)
log = logging.getLogger("derma.inferencia")


@dataclass(frozen=True)
class Resultado:
    categoria: str                       # código de la clase más probable
    confianza: float                     # de 0 a 1
    baja_confianza: bool
    probabilidades: dict[str, float]     # código -> probabilidad, de mayor a menor
    modelo: str
    provisional: bool
    mapa: np.ndarray | None = field(default=None, compare=False)  # Grad-CAM de la clase elegida
    mapa_fallo: bool = False                                       # True si se intentó y falló


class ServicioInferencia:
    def __init__(self, modelo: ModeloClasificador, umbral: float | None = None, espera: float | None = None):
        self._modelo = modelo
        self._umbral = settings.umbral_confianza if umbral is None else umbral
        self._espera = settings.inferencia_timeout if espera is None else espera
        self._cerrojo = threading.Lock()  # el modelo atiende una imagen a la vez

    def analizar(self, tensor: np.ndarray, con_mapa: bool = True) -> Resultado:
        if tensor.shape != FORMA_ENTRADA:
            raise ValueError(f"La entrada debe tener forma {FORMA_ENTRADA}, no {tensor.shape}.")
        if not self._cerrojo.acquire(timeout=self._espera):
            raise ServicioOcupado("El servicio de análisis está ocupado.")
        try:
            probs = np.asarray(self._modelo.predecir(tensor), dtype=np.float64).reshape(-1)
            clases = self._modelo.clases
            if probs.shape[0] != len(clases) or not np.all(np.isfinite(probs)):
                raise InferenciaNoDisponible("El modelo devolvió una salida no válida.")
            orden = np.argsort(-probs)
            mejor = int(orden[0])
            mapa, mapa_fallo = None, False
            if con_mapa and hasattr(self._modelo, "mapa_calor"):
                try:  # el mapa de calor es opcional: si falla, igual se entrega la categoría
                    mapa = np.asarray(self._modelo.mapa_calor(tensor, mejor), dtype=np.float32)
                except Exception:
                    log.exception("No se pudo calcular el mapa de calor")
                    mapa_fallo = True
        finally:
            self._cerrojo.release()
        return Resultado(
            categoria=clases[mejor],
            confianza=float(probs[mejor]),
            baja_confianza=bool(probs[mejor] < self._umbral),
            probabilidades={clases[i]: float(probs[i]) for i in orden},
            modelo=self._modelo.nombre,
            provisional=self._modelo.provisional,
            mapa=mapa,
            mapa_fallo=mapa_fallo,
        )
