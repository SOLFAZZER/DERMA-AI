"""Contrato común de los modelos (patrón Strategy) y errores del servicio de inferencia."""
from typing import Protocol

import numpy as np


class InferenciaNoDisponible(Exception):
    """El modelo no se pudo cargar o el servicio está iniciando (responde 503)."""


class ServicioOcupado(InferenciaNoDisponible):
    """El servicio está atendiendo otra solicitud y no se liberó a tiempo (responde 503)."""


class ModeloClasificador(Protocol):
    nombre: str
    clases: list[str]
    provisional: bool

    def predecir(self, tensor: np.ndarray) -> np.ndarray:
        """Recibe (1, 224, 224, 3) y devuelve las probabilidades de cada clase."""
