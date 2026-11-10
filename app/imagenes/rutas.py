"""Ruta de análisis (I01): valida la imagen, la prepara, la clasifica y arma la respuesta."""
import logging
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.auth.deps import UsuarioActual
from app.config import settings
from app.deps import Conexion
from app.imagenes.preprocesamiento import preprocesar
from app.imagenes.validacion import ErrorImagen, leer_con_limite, validar
from app.inferencia import registro
from app.inferencia.base import InferenciaNoDisponible
from app.resultados import armar_respuesta

log = logging.getLogger("derma.analizar")
router = APIRouter(prefix="/api", tags=["análisis"])


def _servicio():
    """Obtiene el servicio de inferencia (la primera vez carga el modelo). Sin modelo: 503."""
    try:
        return registro.obtener_servicio()
    except InferenciaNoDisponible:
        raise HTTPException(503, "El servicio de análisis está iniciando o no disponible. "
                                 "Intenta de nuevo en unos minutos.") from None


@router.post("/analizar")
async def analizar(usuario: UsuarioActual, conn: Conexion, imagen: Annotated[UploadFile, File()]) -> dict:
    """I01. Recibe una imagen (requiere sesión) y devuelve categoría, confianza y probabilidades."""
    try:
        contenido = await leer_con_limite(imagen, settings.max_upload_mb * 1024 * 1024)
        pil = validar(imagen.filename, contenido)
    except ErrorImagen as e:
        raise HTTPException(status_code=e.codigo, detail=e.mensaje) from None
    del contenido  # la imagen no se guarda en ningún lado
    entrada = preprocesar(pil)
    servicio = await run_in_threadpool(_servicio)
    try:
        resultado = await run_in_threadpool(servicio.analizar, entrada)
    except InferenciaNoDisponible:
        raise HTTPException(503, "El servicio de análisis está ocupado o no disponible. Intenta de nuevo.") from None
    except Exception:
        log.exception("Error al analizar la imagen")
        raise HTTPException(500, "Ocurrió un error al analizar la imagen.") from None
    return armar_respuesta(resultado, conn)
