"""Carga y validación de imágenes (C03).

Reglas (DERMA-SRS-6.x): solo JPG, JPEG o PNG, hasta 5 MB, y que el archivo sea realmente
una imagen legible (se valida por contenido, no solo por la extensión). La imagen se procesa
en memoria y no se guarda (DERMA-SRS-9.1).
"""
import io
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

EXTENSIONES = {".jpg", ".jpeg", ".png"}
FORMATOS = {"JPEG", "PNG"}
TROZO = 64 * 1024
MIN_LADO = 100  # píxeles: por debajo de esto la imagen no sirve para el análisis

# Protección contra imágenes con un número absurdo de píxeles (Pillow falla a partir del doble).
Image.MAX_IMAGE_PIXELS = 40_000_000


class ErrorImagen(Exception):
    """Error de validación con el código HTTP que corresponde."""

    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


async def leer_con_limite(archivo: UploadFile, max_bytes: int) -> bytes:
    """Lee el archivo por trozos y corta la lectura apenas supera el límite (413)."""
    partes: list[bytes] = []
    total = 0
    while trozo := await archivo.read(TROZO):
        total += len(trozo)
        if total > max_bytes:
            raise ErrorImagen(413, f"La imagen supera el tamaño máximo de {max_bytes // (1024 * 1024)} MB.")
        partes.append(trozo)
    return b"".join(partes)


def validar(nombre: str | None, contenido: bytes) -> Image.Image:
    """Comprueba extensión, contenido y legibilidad. Devuelve la imagen ya decodificada.

    400: la extensión o el contenido no corresponden a JPG/PNG.
    422: el archivo parece JPG/PNG pero está vacío, dañado, no se puede leer o es demasiado pequeño.
    """
    if Path(nombre or "").suffix.lower() not in EXTENSIONES:
        raise ErrorImagen(400, "Formato no permitido. Usa una imagen JPG, JPEG o PNG.")
    if not contenido:
        raise ErrorImagen(422, "El archivo está vacío.")
    try:
        imagen = Image.open(io.BytesIO(contenido))
    except UnidentifiedImageError:
        raise ErrorImagen(400, "El archivo no es una imagen JPG o PNG válida.") from None
    except (OSError, Image.DecompressionBombError):
        raise ErrorImagen(422, "No se pudo leer la imagen.") from None
    if imagen.format not in FORMATOS:
        raise ErrorImagen(400, "Formato no permitido. Usa una imagen JPG, JPEG o PNG.")
    try:
        imagen.load()  # decodifica todo: detecta archivos truncados o dañados
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise ErrorImagen(422, "La imagen está dañada o no se pudo leer.") from None
    if min(imagen.size) < MIN_LADO:
        raise ErrorImagen(422, f"La imagen es demasiado pequeña (mínimo {MIN_LADO} × {MIN_LADO} píxeles).")
    return imagen
