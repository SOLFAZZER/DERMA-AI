import io

import numpy as np
import pytest
from PIL import Image

from app.imagenes.preprocesamiento import TAMANO, preprocesar
from app.imagenes.validacion import ErrorImagen, validar


def imagen_bytes(formato="JPEG", modo="RGB", tamano=(300, 200), color=(120, 60, 30)):
    buf = io.BytesIO()
    Image.new(modo, tamano, color).save(buf, formato)
    return buf.getvalue()


# ---------------------------------------------------------------- validar (C03)

def test_acepta_jpg_jpeg_y_png():
    assert validar("a.jpg", imagen_bytes("JPEG")).format == "JPEG"
    assert validar("a.JPEG", imagen_bytes("JPEG")).format == "JPEG"
    assert validar("a.png", imagen_bytes("PNG")).format == "PNG"


@pytest.mark.parametrize("nombre", ["a.gif", "a.bmp", "a.txt", "a", None])
def test_rechaza_extensiones_no_permitidas(nombre):
    with pytest.raises(ErrorImagen) as e:
        validar(nombre, imagen_bytes("JPEG"))
    assert e.value.codigo == 400


def test_rechaza_texto_disfrazado_de_jpg():
    with pytest.raises(ErrorImagen) as e:
        validar("foto.jpg", b"esto no es una imagen")
    assert e.value.codigo == 400


def test_rechaza_gif_con_extension_png():
    with pytest.raises(ErrorImagen) as e:
        validar("foto.png", imagen_bytes("GIF", modo="P"))
    assert e.value.codigo == 400


def test_archivo_vacio_da_422():
    with pytest.raises(ErrorImagen) as e:
        validar("foto.jpg", b"")
    assert e.value.codigo == 422


def test_jpeg_truncado_da_422():
    datos = imagen_bytes("JPEG", tamano=(600, 400))
    with pytest.raises(ErrorImagen) as e:
        validar("foto.jpg", datos[: len(datos) // 2])
    assert e.value.codigo == 422


# ---------------------------------------------------------------- preprocesar (C04)

def test_preprocesar_forma_tipo_y_rango():
    x = preprocesar(validar("a.jpg", imagen_bytes("JPEG", tamano=(640, 480))))
    assert x.shape == (1, TAMANO, TAMANO, 3)
    assert x.dtype == np.float32
    assert x.min() >= -1.0 and x.max() <= 1.0


def test_preprocesar_escala_a_menos1_y_1():
    negro = preprocesar(validar("a.png", imagen_bytes("PNG", color=(0, 0, 0))))
    blanco = preprocesar(validar("a.png", imagen_bytes("PNG", color=(255, 255, 255))))
    assert np.allclose(negro, -1.0) and np.allclose(blanco, 1.0)


def test_preprocesar_escala_de_grises_queda_en_3_canales():
    x = preprocesar(validar("a.png", imagen_bytes("PNG", modo="L", color=128)))
    assert x.shape == (1, TAMANO, TAMANO, 3)


def test_preprocesar_transparencia_queda_en_blanco():
    x = preprocesar(validar("a.png", imagen_bytes("PNG", modo="RGBA", color=(0, 0, 0, 0))))
    assert np.allclose(x, 1.0)
