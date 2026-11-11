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


# ---------------------------------------------------------------- Grad-CAM con la misma estructura que el modelo real

@pytest.fixture
def ruta_modelo_anidado(tmp_path):
    """Réplica pequeña del modelo entrenado: un cuerpo convolucional anidado y una cabeza con GAP y Dense."""
    cuerpo_in = tf.keras.Input((224, 224, 3))
    x = tf.keras.layers.Conv2D(8, 3, strides=8, activation="relu")(cuerpo_in)  # (28, 28, 8)
    x = tf.keras.layers.Conv2D(16, 3, strides=4, activation="relu", name="out_relu")(x)  # (7, 7, 16)
    cuerpo = tf.keras.Model(cuerpo_in, x, name="cuerpo")
    entrada = tf.keras.Input((224, 224, 3))
    h = cuerpo(entrada, training=False)
    h = tf.keras.layers.GlobalAveragePooling2D()(h)
    h = tf.keras.layers.Dropout(0.3)(h)
    salida = tf.keras.layers.Dense(7, activation="softmax")(h)
    ruta = tmp_path / "anidado.keras"
    tf.keras.Model(entrada, salida).save(ruta)
    return str(ruta)


def imagen_aleatoria():
    return np.random.default_rng(3).uniform(-1, 1, size=(1, 224, 224, 3)).astype(np.float32)


def test_gradcam_devuelve_un_mapa_de_0_a_1(ruta_modelo_anidado):
    m = ModeloKeras(ruta_modelo_anidado, CLASES_MODELO)
    mapa = m.mapa_calor(imagen_aleatoria(), 2)
    assert mapa.shape == (7, 7)
    assert mapa.min() >= 0.0 and mapa.max() <= 1.0 + 1e-6


def test_gradcam_es_repetible_y_no_cambia_la_prediccion(ruta_modelo_anidado):
    m = ModeloKeras(ruta_modelo_anidado, CLASES_MODELO)
    x = imagen_aleatoria()
    antes = m.predecir(x)
    assert np.allclose(m.mapa_calor(x, 1), m.mapa_calor(x, 1))
    assert np.allclose(antes, m.predecir(x))


def test_gradcam_clase_fuera_de_rango(ruta_modelo_anidado):
    m = ModeloKeras(ruta_modelo_anidado, CLASES_MODELO)
    with pytest.raises(ValueError):
        m.mapa_calor(imagen_aleatoria(), 9)


def test_modelo_sin_cuerpo_anidado_clasifica_pero_sin_mapa(ruta_modelo):
    m = ModeloKeras(ruta_modelo, CLASES_MODELO)
    assert m.predecir(imagen_aleatoria()).shape == (7,)
    with pytest.raises(RuntimeError):
        m.mapa_calor(imagen_aleatoria(), 0)


def test_servicio_completo_con_keras_real(ruta_modelo_anidado):
    from app.inferencia.servicio import ServicioInferencia

    r = ServicioInferencia(ModeloKeras(ruta_modelo_anidado, CLASES_MODELO)).analizar(imagen_aleatoria())
    assert r.mapa is not None and r.mapa.shape == (7, 7) and not r.mapa_fallo
    assert sum(r.probabilidades.values()) == pytest.approx(1.0, abs=1e-4)


def test_gradcam_marca_la_zona_que_decide_el_resultado(tmp_path):
    """Prueba con respuesta conocida: la clase 0 solo "ve" el brillo, así que el mapa debe
    iluminar la mitad izquierda (brillante) y dejar apagada la derecha (oscura)."""
    k = tf.keras.initializers.Constant
    cuerpo_in = tf.keras.Input((224, 224, 3))
    f = tf.keras.layers.Conv2D(1, 1, strides=32, use_bias=False, kernel_initializer=k(1.0), name="out_relu")(cuerpo_in)
    f = tf.keras.layers.ReLU()(f)  # (7, 7, 1): 3 donde la imagen es clara, 0 donde es oscura
    cuerpo = tf.keras.Model(cuerpo_in, f, name="cuerpo")
    entrada = tf.keras.Input((224, 224, 3))
    h = tf.keras.layers.GlobalAveragePooling2D()(cuerpo(entrada, training=False))
    peso = np.zeros((1, 7), dtype=np.float32)
    peso[0, 0] = 5.0  # solo la clase 0 depende del brillo
    salida = tf.keras.layers.Dense(7, activation="softmax", use_bias=False,
                                   kernel_initializer=k(peso))(h)
    ruta = tmp_path / "conocido.keras"
    tf.keras.Model(entrada, salida).save(ruta)

    x = -np.ones((1, 224, 224, 3), dtype=np.float32)
    x[:, :, :112, :] = 1.0  # mitad izquierda clara
    mapa = ModeloKeras(str(ruta), CLASES_MODELO).mapa_calor(x, 0)
    assert mapa[:, :4].min() == pytest.approx(1.0)
    assert mapa[:, 4:].max() == pytest.approx(0.0)


def test_gradcam_no_se_apaga_con_resultados_muy_seguros(tmp_path):
    """Con un softmax saturado (probabilidad 1.0) el mapa igual debe tener señal."""
    k = tf.keras.initializers.Constant
    cuerpo_in = tf.keras.Input((224, 224, 3))
    f = tf.keras.layers.Conv2D(1, 1, strides=32, use_bias=False, kernel_initializer=k(1.0), name="out_relu")(cuerpo_in)
    cuerpo = tf.keras.Model(cuerpo_in, tf.keras.layers.ReLU()(f), name="cuerpo")
    entrada = tf.keras.Input((224, 224, 3))
    h = tf.keras.layers.GlobalAveragePooling2D()(cuerpo(entrada, training=False))
    peso = np.zeros((1, 7), dtype=np.float32)
    peso[0, 0] = 500.0  # logit enorme: softmax = 1.0 exacto
    salida = tf.keras.layers.Dense(7, activation="softmax", use_bias=False, kernel_initializer=k(peso))(h)
    ruta = tmp_path / "saturado.keras"
    tf.keras.Model(entrada, salida).save(ruta)
    m = ModeloKeras(str(ruta), CLASES_MODELO)
    x = np.ones((1, 224, 224, 3), dtype=np.float32)
    assert m.predecir(x)[0] == 1.0
    assert m.mapa_calor(x, 0).max() == pytest.approx(1.0)
