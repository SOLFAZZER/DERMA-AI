"""Exportación del resultado en PDF (I14). No guarda nada: arma el archivo en memoria y lo devuelve."""
import json
import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from app.auth.deps import UsuarioActual
from app.config import settings
from app.exportacion.pdf import construir_pdf
from app.imagenes.validacion import ErrorImagen, leer_con_limite, validar

log = logging.getLogger("derma.exportar")
router = APIRouter(prefix="/api", tags=["exportación"])
MAX_RESULTADO = 3 * 1024 * 1024  # el mapa de calor en base64 es lo más pesado


class Categoria(BaseModel):
    codigo: str = Field(max_length=20)
    nombre: str = Field(max_length=100)
    nivel_riesgo: str | None = Field(default=None, max_length=20)
    descripcion: str | None = Field(default=None, max_length=500)


class Probabilidad(BaseModel):
    codigo: str = Field(max_length=20)
    nombre: str = Field(max_length=100)
    porcentaje: float = Field(ge=0, le=100)


class Version(BaseModel):
    id: int | None = None
    arquitectura: str | None = Field(default=None, max_length=100)


class ResultadoEntrada(BaseModel):
    categoria: Categoria
    confianza: float = Field(ge=0, le=100)
    baja_confianza: bool = False
    probabilidades: list[Probabilidad] = Field(min_length=1, max_length=10)
    mapa_calor: str = Field(default="", max_length=2_500_000)
    explicacion_mapa: str = Field(default="", max_length=600)
    mensaje: str = Field(default="", max_length=800)
    version_modelo: Version | None = None
    aviso: str = Field(default="", max_length=600)


@router.post("/exportar-pdf")
async def exportar_pdf(
    usuario: UsuarioActual,
    resultado: Annotated[str, Form(max_length=MAX_RESULTADO)],
    fecha: Annotated[str, Form(max_length=40)] = "",
    imagen: Annotated[UploadFile | None, File()] = None,
) -> Response:
    """Recibe el resultado mostrado en pantalla (y opcionalmente la imagen original) y devuelve un PDF."""
    try:
        datos = ResultadoEntrada.model_validate(json.loads(resultado)).model_dump()
    except (ValueError, ValidationError):
        raise HTTPException(400, "Los datos del resultado no son válidos.") from None
    original = None
    if imagen is not None and imagen.filename:
        try:
            contenido = await leer_con_limite(imagen, settings.max_upload_mb * 1024 * 1024)
            original = validar(imagen.filename, contenido)
        except ErrorImagen as e:
            raise HTTPException(status_code=e.codigo, detail=e.mensaje) from None
    try:
        pdf = await run_in_threadpool(construir_pdf, datos, original, fecha.strip())
    except Exception:
        log.exception("No se pudo generar el PDF")
        raise HTTPException(500, "No se pudo generar el PDF.") from None
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="derma-ai-resultado.pdf"'})
