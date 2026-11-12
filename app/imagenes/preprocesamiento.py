"""Preprocesamiento de la imagen (C04): deja la imagen como la espera el modelo.

El modelo se entrenó con MobileNetV2: entrada 224x224 en RGB, con los píxeles escalados a [-1, 1]
(`tf.keras.applications.mobilenet_v2.preprocess_input`). Ver `model_config.json`.
"""
import numpy as np
from PIL import Image, ImageOps

TAMANO = 224


def _indices(origen: int, destino: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Posiciones y pesos de la interpolación bilineal de TensorFlow (centros de píxel a la mitad)."""
    pos = (np.arange(destino, dtype=np.float32) + 0.5) * np.float32(origen / destino) - 0.5
    base = np.floor(pos)
    inferior = np.clip(base, 0, origen - 1).astype(np.int64)
    superior = np.clip(np.ceil(pos), 0, origen - 1).astype(np.int64)
    return inferior, superior, (pos - base).astype(np.float32)


def redimensionar_como_tensorflow(arreglo: np.ndarray, lado: int = TAMANO) -> np.ndarray:
    """Equivale a `tf.image.resize(img, (lado, lado))` seguido de `tf.round` y uint8, como en el entrenamiento.

    Pillow suaviza al reducir una imagen (filtro con antialiasing) y TensorFlow no, así que los píxeles
    salían un poco distintos. Se copia el método de TensorFlow para que el modelo reciba lo mismo que vio.
    """
    alto, ancho = arreglo.shape[:2]
    y0, y1, fy = _indices(alto, lado)
    x0, x1, fx = _indices(ancho, lado)
    # Primero se toman solo las filas necesarias (uint8) para no convertir una foto enorme a float.
    def fila(r: np.ndarray) -> np.ndarray:
        return (r[:, x0].astype(np.float32) * (1 - fx)[None, :, None]
                + r[:, x1].astype(np.float32) * fx[None, :, None])

    arriba, abajo = fila(arreglo[y0]), fila(arreglo[y1])
    mezcla = arriba * (1 - fy)[:, None, None] + abajo * fy[:, None, None]
    return np.clip(np.round(mezcla), 0, 255).astype(np.uint8)


def preprocesar(imagen: Image.Image) -> np.ndarray:
    """Devuelve un arreglo float32 de forma (1, 224, 224, 3) con valores en [-1, 1]."""
    imagen = ImageOps.exif_transpose(imagen)  # respeta la orientación de las fotos de celular
    if imagen.mode in ("RGBA", "LA") or (imagen.mode == "P" and "transparency" in imagen.info):
        rgba = imagen.convert("RGBA")
        fondo = Image.new("RGBA", rgba.size, (255, 255, 255, 255))  # la transparencia queda en blanco
        fondo.alpha_composite(rgba)
        imagen = fondo
    pixeles = redimensionar_como_tensorflow(np.asarray(imagen.convert("RGB")))
    arreglo = pixeles.astype(np.float32) / 127.5 - 1.0
    return arreglo[np.newaxis, ...]
