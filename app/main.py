"""Punto de entrada de la API de Derma-AI (prototipo académico, no es una herramienta de diagnóstico)."""
import sqlite3
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from app.config import settings
from app.db import catalogo
from app.deps import get_conn

Conexion = Annotated[sqlite3.Connection, Depends(get_conn)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al arrancar se asegura que exista el esquema y el catálogo de las 7 clases.
    conn = catalogo.conectar(settings.catalog_db)
    try:
        catalogo.crear_esquema(conn)
        catalogo.cargar_catalogo(conn)
    finally:
        conn.close()
    yield


app = FastAPI(
    title="Derma-AI",
    version=settings.version,
    description="Prototipo académico de apoyo a la evaluación preliminar de lesiones cutáneas.",
    lifespan=lifespan,
)


@app.get("/api/salud")
def salud() -> dict:
    """I04. Estado del servicio."""
    return {"estado": "listo", "version": settings.version, "modelo_cargado": False}


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
