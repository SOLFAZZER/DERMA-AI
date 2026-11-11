import json

import pytest

from app.inferencia import registro
from app.inferencia.base import InferenciaNoDisponible
from app.inferencia.fabrica import crear_modelo, leer_clases
from app.inferencia.provisional import ModeloProvisional
from app.inferencia.servicio import ServicioInferencia
from tests.conftest import CLASES_MODELO, ModeloFalso


@pytest.fixture
def clases_json(tmp_path):
    ruta = tmp_path / "class_names.json"
    ruta.write_text(json.dumps(CLASES_MODELO), encoding="utf-8")
    return str(ruta)


@pytest.fixture(autouse=True)
def limpio():
    registro.reiniciar()
    yield
    registro.reiniciar()


def test_fabrica_crea_el_modelo_provisional(clases_json):
    m = crear_modelo("provisional", ruta_clases=clases_json)
    assert isinstance(m, ModeloProvisional) and m.clases == CLASES_MODELO


def test_fabrica_modo_desconocido(clases_json):
    with pytest.raises(ValueError):
        crear_modelo("magico", ruta_clases=clases_json)


def test_fabrica_keras_sin_archivo_no_se_cae_en_silencio(clases_json, tmp_path):
    with pytest.raises(InferenciaNoDisponible):
        crear_modelo("keras", ruta_modelo=str(tmp_path / "no_existe.keras"), ruta_clases=clases_json)


def test_clases_invalidas(tmp_path):
    malo = tmp_path / "x.json"
    malo.write_text("{no es json", encoding="utf-8")
    with pytest.raises(InferenciaNoDisponible):
        leer_clases(str(malo))
    with pytest.raises(InferenciaNoDisponible):
        leer_clases(str(tmp_path / "no_hay.json"))
    malo.write_text('{"a": 1}', encoding="utf-8")
    with pytest.raises(InferenciaNoDisponible):
        leer_clases(str(malo))


def test_singleton_carga_una_sola_vez(monkeypatch):
    llamadas = []

    def falsa_fabrica():
        llamadas.append(1)
        return ModeloFalso([1 / 7] * 7)

    monkeypatch.setattr(registro, "crear_modelo", falsa_fabrica)
    assert not registro.esta_cargado()
    a = registro.obtener_servicio()
    b = registro.obtener_servicio()
    assert a is b and isinstance(a, ServicioInferencia) and len(llamadas) == 1
    assert registro.esta_cargado()


def test_si_falla_la_carga_no_queda_en_cache(monkeypatch):
    def rota():
        raise RuntimeError("disco dañado")

    monkeypatch.setattr(registro, "crear_modelo", rota)
    with pytest.raises(InferenciaNoDisponible):
        registro.obtener_servicio()
    assert not registro.esta_cargado()
    registro.precargar()  # no debe lanzar excepción
