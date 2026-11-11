"""Punto de entrada de la API de Derma-AI (prototipo académico, no es una herramienta de diagnóstico)."""
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth import seguridad, usuarios
from app.auth.rutas import router as router_auth
from app.cabeceras import CabecerasSeguridad
from app.config import settings
from app.db import catalogo
from app.deps import Conexion
from app.exportacion.rutas import MAX_RESULTADO
from app.exportacion.rutas import router as router_exportacion
from app.imagenes.limite import LimiteCuerpo
from app.imagenes.rutas import router as router_imagenes
from app.inferencia import registro


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Catálogo de las 7 clases (C08)
    conn = catalogo.conectar(settings.catalog_db)
    try:
        catalogo.crear_esquema(conn)
        catalogo.cargar_catalogo(conn)
    finally:
        conn.close()
    # Almacén de usuarios (C09) y usuario de demostración opcional
    cu = catalogo.conectar(settings.users_db)
    try:
        usuarios.crear_esquema(cu)
        if settings.demo_email and settings.demo_password:
            correo = settings.demo_email.strip().lower()
            if usuarios.buscar_por_correo(cu, correo) is None:
                usuarios.crear_usuario(cu, correo, seguridad.hash_contrasena(settings.demo_password))
    finally:
        cu.close()
    registro.precargar()  # carga el modelo una vez; si falla, la API sigue y /api/analizar responde 503
    yield


app = FastAPI(
    title="Derma-AI",
    version=settings.version,
    description="Prototipo académico de apoyo a la evaluación preliminar de lesiones cutáneas.",
    lifespan=lifespan,
)
app.include_router(router_auth)
app.include_router(router_imagenes)
app.include_router(router_exportacion)
# 5 MB de imagen + un margen para los encabezados del formulario multipart
app.add_middleware(LimiteCuerpo, ruta="/api/analizar", max_bytes=settings.max_upload_mb * 1024 * 1024 + 64 * 1024)

app.add_middleware(LimiteCuerpo, ruta="/api/exportar-pdf",
                   max_bytes=settings.max_upload_mb * 1024 * 1024 + MAX_RESULTADO + 64 * 1024)

app.add_middleware(CabecerasSeguridad)


@app.exception_handler(RequestValidationError)
async def datos_no_validos(request: Request, exc: RequestValidationError):
    """En autenticación y análisis, los datos mal formados responden 400 (como define la API)."""
    if request.url.path.startswith(("/api/auth", "/api/analizar", "/api/exportar-pdf")):
        return JSONResponse(status_code=400, content={"detail": "Los datos enviados no son válidos."})
    return await request_validation_exception_handler(request, exc)


@app.get("/api/salud")
def salud() -> dict:
    """I04. Estado del servicio."""
    return {"estado": "listo", "version": settings.version, "modelo_cargado": registro.esta_cargado()}


@app.get("/api/lesiones")
def lesiones(conn: Conexion) -> dict:
    """I02. Catálogo de categorías con su descripción."""
    return {"lesiones": catalogo.listar_lesiones(conn)}


@app.get("/api/modelo")
def modelo(conn: Conexion) -> dict:
    """I03. Versión activa del modelo y sus métricas."""
    version = catalogo.version_activa(conn)
    if version is None:
        raise HTTPException(status_code=404, detail="Aún no hay una versión del modelo registrada.")
    return version


# La interfaz web se sirve desde la raíz. Debe ir al final para no tapar las rutas de la API.
# En algunos Windows el registro del sistema asigna tipos erróneos (p. ej. .js como text/plain) y,
# con la cabecera nosniff, el navegador bloquearía el script. Se fijan explícitamente.
for extension, tipo in ((".js", "text/javascript"), (".css", "text/css"), (".html", "text/html"),
                        (".png", "image/png")):
    mimetypes.add_type(tipo, extension)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
