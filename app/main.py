"""Punto de entrada de la API de Derma-AI (prototipo académico, no es una herramienta de diagnóstico)."""
from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title="Derma-AI",
    version=settings.version,
    description="Prototipo académico de apoyo a la evaluación preliminar de lesiones cutáneas.",
)


@app.get("/api/salud")
def salud() -> dict:
    """Comprobación de que el servicio está vivo."""
    return {"estado": "ok", "version": settings.version, "modelo_cargado": False}
