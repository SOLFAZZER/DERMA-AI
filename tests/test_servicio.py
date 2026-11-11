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


def test_el_servicio_calcula_el_mapa_de_la_clase_elegida():
    llamadas = []

    class ConMapa(ModeloFalso):
        def mapa_calor(self, tensor, indice):
            llamadas.append(indice)
            return np.ones((7, 7))

    r = ServicioInferencia(ConMapa([0.1, 0.1, 0.1, 0.0, 0.5, 0.1, 0.1])).analizar(TENSOR)
    assert llamadas == [4] and r.mapa.shape == (7, 7) and r.mapa_fallo is False


def test_si_el_mapa_falla_se_marca_y_no_se_cae():
    class Roto(ModeloFalso):
        def mapa_calor(self, tensor, indice):
            raise RuntimeError("x")

    r = ServicioInferencia(Roto([0.1, 0.1, 0.1, 0.0, 0.5, 0.1, 0.1])).analizar(TENSOR)
    assert r.mapa is None and r.mapa_fallo is True and r.categoria == "MEL"


def test_se_puede_pedir_sin_mapa():
    class ConMapa(ModeloFalso):
        def mapa_calor(self, tensor, indice):
            raise AssertionError("no debía llamarse")

    r = ServicioInferencia(ConMapa(np.ones(7) / 7)).analizar(TENSOR, con_mapa=False)
    assert r.mapa is None and r.mapa_fallo is False
