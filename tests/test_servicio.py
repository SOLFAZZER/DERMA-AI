import numpy as np
import pytest

from app.inferencia.base import InferenciaNoDisponible, ServicioOcupado
from app.inferencia.servicio import ServicioInferencia
from tests.conftest import ModeloFalso

TENSOR = np.zeros((1, 224, 224, 3), dtype=np.float32)


def test_elige_la_clase_mas_probable():
    s = ServicioInferencia(ModeloFalso([0.1, 0.1, 0.1, 0.0, 0.5, 0.1, 0.1]), umbral=0.4)
    r = s.analizar(TENSOR)
    assert r.categoria == "MEL" and r.confianza == pytest.approx(0.5)
    assert r.baja_confianza is False
    assert next(iter(r.probabilidades)) == "MEL"


def test_marca_baja_confianza_bajo_el_umbral():
    s = ServicioInferencia(ModeloFalso([0.2, 0.1, 0.1, 0.0, 0.35, 0.15, 0.1]), umbral=0.6)
    assert s.analizar(TENSOR).baja_confianza is True


def test_rechaza_una_entrada_con_forma_incorrecta():
    s = ServicioInferencia(ModeloFalso(np.ones(7) / 7))
    with pytest.raises(ValueError):
        s.analizar(np.zeros((1, 100, 100, 3), dtype=np.float32))


def test_salida_del_modelo_no_valida():
    with pytest.raises(InferenciaNoDisponible):
        ServicioInferencia(ModeloFalso([0.5, 0.5])).analizar(TENSOR)
    with pytest.raises(InferenciaNoDisponible):
        ServicioInferencia(ModeloFalso([np.nan] * 7)).analizar(TENSOR)


def test_si_esta_ocupado_responde_servicio_ocupado():
    s = ServicioInferencia(ModeloFalso(np.ones(7) / 7), espera=0.05)
    with s._cerrojo, pytest.raises(ServicioOcupado):
        s.analizar(TENSOR)
