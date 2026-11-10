"""Imagen del mapa de calor (parte de C06): colorea el mapa y lo superpone a la imagen analizada."""
import base64
import io

import numpy as np
from PIL import Image

ALFA = 0.4  # peso del mapa de calor sobre la imagen original


def tensor_a_imagen(tensor: np.ndarray) -> np.ndarray:
    """Invierte el preprocesamiento: (1, 224, 224, 3) en [-1, 1] -> (224, 224, 3) uint8."""
    return np.clip(np.rint((tensor[0] + 1.0) * 127.5), 0, 255).astype(np.uint8)


def colorear_jet(mapa: np.ndarray) -> np.ndarray:
    """Convierte valores de 0 a 1 en colores (azul = poca influencia, rojo = mucha)."""
    x = np.clip(mapa, 0.0, 1.0)
    r = np.clip(1.5 - np.abs(4 * x - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * x - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * x - 1), 0, 1)
    return np.stack([r, g, b], axis=-1)


def crear_png_base64(imagen_rgb: np.ndarray, mapa: np.ndarray) -> str:
    """Superpone el mapa (cualquier tamaño, valores 0 a 1) a la imagen y devuelve un PNG en base64."""
    alto, ancho = imagen_rgb.shape[:2]
    mapa = np.nan_to_num(np.asarray(mapa, dtype=np.float32), nan=0.0)
    grande = Image.fromarray(mapa, mode="F").resize((ancho, alto), Image.BILINEAR)
    calor = colorear_jet(np.asarray(grande))
    mezcla = (1 - ALFA) * imagen_rgb.astype(np.float32) / 255.0 + ALFA * calor
    salida = Image.fromarray(np.clip(np.rint(mezcla * 255), 0, 255).astype(np.uint8), "RGB")
    buf = io.BytesIO()
    salida.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")
