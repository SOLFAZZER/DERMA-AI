"""Configuración de Derma-AI. Todo se lee de variables de entorno (ver .env.example)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    version: str = "0.1.0"
    secret_key: str = os.environ.get("DERMA_SECRET_KEY", "dev-solo-para-desarrollo")
    session_minutes: int = int(os.environ.get("DERMA_SESSION_MINUTES", "60"))
    max_upload_mb: int = int(os.environ.get("DERMA_MAX_UPLOAD_MB", "5"))
    users_db: str = os.environ.get("DERMA_USERS_DB", "data/usuarios.db")
    catalog_db: str = os.environ.get("DERMA_CATALOG_DB", "data/catalogo.db")
    model_path: str = os.environ.get("DERMA_MODEL_PATH", "models/dermaai_mobilenetv2_v1.keras")


settings = Settings()
