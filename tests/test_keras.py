"""Pruebas con TensorFlow real. Se omiten si no está instalado (por ejemplo en la integración continua)."""
import numpy as np
import pytest

tf = pytest.importorskip("tensorflow")

from app.inferencia.base import InferenciaNoDisponible
from app.inferencia.keras_modelo import ModeloKeras
from tests.conftest import CLASES_MODELO


@pytest.fixture
def ruta_modelo(tmp_path):
    entrada = tf.keras.Input((224, 224, 3))
    x = tf.keras.layers.GlobalAveragePooling2D()(entrada)
    salida = tf.keras.layers.Dense(7, activation="softmax")(x)
    ruta = tmp_path / "pequeno.keras"
    tf.keras.Model(entrada, salida).save(ruta)
    return str(ruta)


def test_carga_y_predice(ruta_modelo):
    m = ModeloKeras(ruta_modelo, CLASES_MODELO)
    p = m.predecir(np.zeros((1, 224, 224, 3), dtype=np.float32))
    assert p.shape == (7,) and p.sum() == pytest.approx(1.0, abs=1e-4)


def test_numero_de_clases_distinto_da_error(ruta_modelo):
    with pytest.raises(InferenciaNoDisponible):
        ModeloKeras(ruta_modelo, CLASES_MODELO[:5])


def test_archivo_inexistente(tmp_path):
    with pytest.raises(InferenciaNoDisponible):
        ModeloKeras(str(tmp_path / "nada.keras"), CLASES_MODELO)
