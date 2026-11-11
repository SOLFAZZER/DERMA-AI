"""Hash de contraseñas (bcrypt) y token de sesión (JWT firmado)."""
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings

RONDAS = settings.bcrypt_rounds
ALGORITMO = "HS256"
MAX_BYTES_CONTRASENA = 72  # límite de bcrypt


def hash_contrasena(contrasena: str) -> str:
    return bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt(rounds=RONDAS)).decode("ascii")


def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(contrasena.encode("utf-8"), hash_guardado.encode("ascii"))
    except ValueError:
        return False


# Hash falso para igualar el tiempo de respuesta cuando el correo no existe.
_HASH_FALSO = hash_contrasena("contrasena-falsa-para-igualar-tiempos")


def verificar_contra_hash_falso(contrasena: str) -> None:
    verificar_contrasena(contrasena, _HASH_FALSO)


def crear_token(id_usuario: int, correo: str, minutos: int | None = None) -> str:
    ahora = datetime.now(UTC)
    vence = ahora + timedelta(minutes=settings.session_minutes if minutos is None else minutos)
    carga = {"sub": str(id_usuario), "correo": correo, "iat": ahora, "exp": vence}
    return jwt.encode(carga, settings.secret_key, algorithm=ALGORITMO)


def leer_token(token: str) -> dict | None:
    """Devuelve la carga del token o None si es inválido o venció."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITMO])
    except jwt.PyJWTError:
        return None
