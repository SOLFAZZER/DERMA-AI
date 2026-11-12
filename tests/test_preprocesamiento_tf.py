"""El servidor debe preparar la imagen igual que el entrenamiento (tf.image.resize + redondeo)."""
import numpy as np
import pytest

from app.imagenes.preprocesamiento import preprocesar, redimensionar_como_tensorflow


def test_una_imagen_de_un_solo_color_no_cambia():
    img = np.full((300, 500, 3), (10, 128, 250), dtype=np.uint8)
    out = redimensionar_como_tensorflow(img)
    assert out.shape == (224, 224, 3) and out.dtype == np.uint8
    assert (out == np.array([10, 128, 250])).all()


def test_acepta_imagenes_pequenas_y_grandes():
    for forma in [(100, 100, 3), (1, 50, 3), (2592, 3456, 3)]:
        assert redimensionar_como_tensorflow(np.zeros(forma, dtype=np.uint8)).shape == (224, 224, 3)


def test_igual_que_tensorflow():
    tf = pytest.importorskip("tensorflow")
    rng = np.random.default_rng(0)
    for forma in [(450, 600, 3), (100, 100, 3), (300, 1000, 3), (1129, 1503, 3)]:
        a = rng.integers(0, 256, forma, dtype=np.uint8)
        esperado = tf.cast(tf.round(tf.image.resize(a, (224, 224))), tf.uint8).numpy()
        obtenido = redimensionar_como_tensorflow(a)
        assert np.abs(esperado.astype(int) - obtenido).max() <= 1
        assert (esperado != obtenido).mean() < 1e-4


def test_la_salida_va_de_menos_uno_a_uno():
    from PIL import Image
    out = preprocesar(Image.new("RGB", (300, 200), (255, 0, 128)))
    assert out.shape == (1, 224, 224, 3) and out.dtype == np.float32
    assert out.min() >= -1 and out.max() <= 1
