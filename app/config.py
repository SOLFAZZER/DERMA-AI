"""Configuración de Derma-AI. Todo se lee de variables de entorno (ver .env.example)."""
import os
from dataclasses import dataclass


def _bool(nombre: str, defecto: bool = False) -> bool:
    return os.environ.get(nombre, str(defecto)).strip().lower() in {"1", "true", "si", "sí", "yes"}


@dataclass(frozen=True)
class Settings:
    version: str = "0.1.0"
    secret_key: str = os.environ.get("DERMA_SECRET_KEY", "dev-solo-para-desarrollo-no-usar-en-produccion")
    session_minutes: int = int(os.environ.get("DERMA_SESSION_MINUTES", "60"))
    max_upload_mb: int = int(os.environ.get("DERMA_MAX_UPLOAD_MB", "5"))
    users_db: str = os.environ.get("DERMA_USERS_DB", "data/usuarios.db")
    catalog_db: str = os.environ.get("DERMA_CATALOG_DB", "data/catalogo.db")
    model_path: str = os.environ.get("DERMA_MODEL_PATH", "models/dermaai_mobilenetv2_v1.keras")
    # En producción (HTTPS) poner DERMA_COOKIE_SECURE=true. En local (http) debe ir en false.
    cookie_secure: bool = _bool("DERMA_COOKIE_SECURE", False)
    bcrypt_rounds: int = int(os.environ.get("DERMA_BCRYPT_ROUNDS", "12"))
    # Modelo: "keras" (el entrenado) o "provisional" (solo para desarrollo, sin TensorFlow).
    modelo_modo: str = os.environ.get("DERMA_MODELO", "keras")
    class_names_path: str = os.environ.get("DERMA_CLASS_NAMES", "models/class_names.json")
    # Por debajo de esta confianza se avisa al usuario. Debe calibrarse con el conjunto de validación.
    umbral_confianza: float = float(os.environ.get("DERMA_UMBRAL_CONFIANZA", "0.60"))
    inferencia_timeout: float = float(os.environ.get("DERMA_INFERENCIA_TIMEOUT", "25"))
    # Usuario de demostración opcional: se crea al arrancar si no existe (riesgo A3).
    demo_email: str = os.environ.get("DERMA_DEMO_EMAIL", "")
    demo_password: str = os.environ.get("DERMA_DEMO_PASSWORD", "")


settings = Settings()
