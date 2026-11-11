"""Dependencias de autenticación. `usuario_actual` es la interfaz interna I13 (C02 → C09)."""
import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.auth import seguridad, usuarios
from app.config import settings
from app.db.catalogo import conectar

COOKIE = "derma_sesion"


def get_users_conn() -> Iterator[sqlite3.Connection]:
    conn = conectar(settings.users_db)
    try:
        yield conn
    finally:
        conn.close()


ConexionUsuarios = Annotated[sqlite3.Connection, Depends(get_users_conn)]


def usuario_actual(request: Request, conn: ConexionUsuarios) -> dict:
    """Verifica la cookie de sesión. Devuelve la identidad del usuario o responde 401."""
    sin_sesion = HTTPException(status_code=401, detail="Inicia sesión para continuar.")
    token = request.cookies.get(COOKIE)
    if not token:
        raise sin_sesion
    carga = seguridad.leer_token(token)
    if carga is None:
        raise sin_sesion
    try:
        fila = usuarios.buscar_por_id(conn, int(carga["sub"]))
    except (KeyError, ValueError):
        raise sin_sesion from None
    if fila is None:
        raise sin_sesion
    return {"id": fila["id_usuario"], "correo": fila["correo"]}


UsuarioActual = Annotated[dict, Depends(usuario_actual)]
