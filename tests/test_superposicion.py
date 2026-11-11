import base64
import io

import numpy as np
from PIL import Image

from app.explicabilidad.superposicion import (
    colorear_jet,
    crear_png_base64,
    tensor_a_imagen,
)


def decodificar(b64):
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(b64))))


def test_tensor_a_imagen_invierte_el_preprocesamiento():
    original = np.random.default_rng(1).integers(0, 256, size=(224, 224, 3), dtype=np.uint8)
    tensor = (original.astype(np.float32) / 127.5 - 1.0)[np.newaxis]
    assert np.array_equal(tensor_a_imagen(tensor), original)


def test_colores_extremos():
    azul, rojo = colorear_jet(np.array([0.0, 1.0]))
    assert azul[2] > azul[0] and rojo[0] > rojo[2]


def test_png_del_tamano_de_la_imagen():
    img = np.full((224, 224, 3), 128, dtype=np.uint8)
    salida = decodificar(crear_png_base64(img, np.random.default_rng(0).random((7, 7))))
    assert salida.shape == (224, 224, 3)


def test_zona_caliente_se_ve_mas_roja_que_la_fria():
    img = np.full((224, 224, 3), 128, dtype=np.uint8)
    mapa = np.zeros((7, 7))
    mapa[:, 3:] = 1.0  # derecha caliente, izquierda fría
    salida = decodificar(crear_png_base64(img, mapa)).astype(int)
    izquierda, derecha = salida[:, :40], salida[:, -40:]
    assert derecha[..., 0].mean() > izquierda[..., 0].mean()
    assert izquierda[..., 2].mean() > derecha[..., 2].mean()


def test_valores_raros_no_rompen():
    img = np.full((224, 224, 3), 128, dtype=np.uint8)
    mapa = np.full((7, 7), np.nan)
    assert crear_png_base64(img, mapa)
