"""Preprocesamiento de la imagen (C04): deja la imagen como la espera el modelo.

El modelo se entrenó con MobileNetV2: entrada 224x224 en RGB, con los píxeles escalados a [-1, 1]
(`tf.keras.applications.mobilenet_v2.preprocess_input`). Ver `model_config.json`.
"""
import numpy as np
from PIL import Image, ImageOps

TAMANO = 224


def preprocesar(imagen: Image.Image) -> np.ndarray:
    """Devuelve un arreglo float32 de forma (1, 224, 224, 3) con valores en [-1, 1]."""
    imagen = ImageOps.exif_transpose(imagen)  # respeta la orientación de las fotos de celular
    if imagen.mode in ("RGBA", "LA") or (imagen.mode == "P" and "transparency" in imagen.info):
        rgba = imagen.convert("RGBA")
        fondo = Image.new("RGBA", rgba.size, (255, 255, 255, 255))  # la transparencia queda en blanco
        fondo.alpha_composite(rgba)
        imagen = fondo
    imagen = imagen.convert("RGB").resize((TAMANO, TAMANO), Image.BILINEAR)
    arreglo = np.asarray(imagen, dtype=np.float32) / 127.5 - 1.0
    return arreglo[np.newaxis, ...]
