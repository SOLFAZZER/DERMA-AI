"""Ruta de análisis (I01). Por ahora valida y preprocesa; la inferencia se conecta en el siguiente paso."""
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.auth.deps import UsuarioActual
from app.config import settings
from app.imagenes.preprocesamiento import preprocesar
from app.imagenes.validacion import ErrorImagen, leer_con_limite, validar

router = APIRouter(prefix="/api", tags=["análisis"])


@router.post("/analizar")
async def analizar(usuario: UsuarioActual, imagen: Annotated[UploadFile, File()]) -> dict:
    """I01. Recibe una imagen (requiere sesión), la valida y la prepara para el modelo."""
    try:
        contenido = await leer_con_limite(imagen, settings.max_upload_mb * 1024 * 1024)
        pil = validar(imagen.filename, contenido)
    except ErrorImagen as e:
        raise HTTPException(status_code=e.codigo, detail=e.mensaje) from None
    del contenido  # la imagen no se guarda en ningún lado
    entrada = preprocesar(pil)
    # TODO (paso siguiente): enviar `entrada` al servicio de inferencia y devolver el resultado.
    raise HTTPException(
        status_code=501,
        detail=f"La imagen es válida (entrada {list(entrada.shape)}), pero el servicio de inferencia aún no está conectado.",
    )
