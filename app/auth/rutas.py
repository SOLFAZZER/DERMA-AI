"""Rutas de autenticación: I09 (registro), I10 (login), I11 (logout) e I12 (consultar sesión)."""
import re
import sqlite3

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.auth import seguridad, usuarios
from app.auth.deps import COOKIE, ConexionUsuarios, UsuarioActual
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["autenticación"])

CORREO_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_CONTRASENA = 8


class RegistroIn(BaseModel):
    correo: str
    contrasena: str
    acepta_aviso: bool = False


class LoginIn(BaseModel):
    correo: str
    contrasena: str


def _normalizar_correo(correo: str) -> str:
    return correo.strip().lower()


def _poner_cookie(respuesta: Response, id_usuario: int, correo: str) -> None:
    respuesta.set_cookie(
        key=COOKIE,
        value=seguridad.crear_token(id_usuario, correo),
        max_age=settings.session_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/registro", status_code=201)
def registrar(datos: RegistroIn, respuesta: Response, conn: ConexionUsuarios) -> dict:
    """I09. Crea la cuenta e inicia la sesión."""
    correo = _normalizar_correo(datos.correo)
    if len(correo) > 254 or not CORREO_RE.match(correo):
        raise HTTPException(400, "El correo no tiene un formato válido.")
    if len(datos.contrasena) < MIN_CONTRASENA:
        raise HTTPException(400, f"La contraseña debe tener al menos {MIN_CONTRASENA} caracteres.")
    if len(datos.contrasena.encode("utf-8")) > seguridad.MAX_BYTES_CONTRASENA:
        raise HTTPException(400, "La contraseña es demasiado larga (máximo 72 bytes).")
    if not datos.acepta_aviso:
        raise HTTPException(400, "Debes aceptar el aviso de tratamiento de datos personales.")
    try:
        id_usuario = usuarios.crear_usuario(conn, correo, seguridad.hash_contrasena(datos.contrasena))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Ese correo ya está registrado.") from None
    _poner_cookie(respuesta, id_usuario, correo)
    return {"correo": correo, "mensaje": "Cuenta creada."}


@router.post("/login")
def iniciar_sesion(datos: LoginIn, respuesta: Response, conn: ConexionUsuarios) -> dict:
    """I10. Inicia la sesión con correo y contraseña."""
    correo = _normalizar_correo(datos.correo)
    usuario = usuarios.buscar_por_correo(conn, correo)
    credenciales_malas = HTTPException(401, "Correo o contraseña incorrectos.")
    if usuario is None:
        seguridad.verificar_contra_hash_falso(datos.contrasena)  # iguala el tiempo de respuesta
        raise credenciales_malas
    espera = usuarios.segundos_de_bloqueo(usuario)
    if espera > 0:
        raise HTTPException(429, "Demasiados intentos fallidos. Espera unos minutos para volver a intentar.",
                            headers={"Retry-After": str(espera)})
    if len(datos.contrasena.encode("utf-8")) > seguridad.MAX_BYTES_CONTRASENA or \
            not seguridad.verificar_contrasena(datos.contrasena, usuario["hash_contrasena"]):
        usuarios.registrar_fallo(conn, usuario["id_usuario"])
        raise credenciales_malas
    usuarios.registrar_exito(conn, usuario["id_usuario"])
    _poner_cookie(respuesta, usuario["id_usuario"], usuario["correo"])
    return {"correo": usuario["correo"]}


@router.post("/logout", status_code=204)
def cerrar_sesion() -> Response:
    """I11. Elimina la cookie de sesión."""
    respuesta = Response(status_code=204)
    respuesta.delete_cookie(COOKIE, path="/", httponly=True, secure=settings.cookie_secure, samesite="lax")
    return respuesta


@router.get("/yo")
def consultar_sesion(usuario: UsuarioActual) -> dict:
    """I12. Devuelve el correo de la sesión actual."""
    return {"correo": usuario["correo"]}
