"""Dependencias compartidas de la API."""
import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends

from app.config import settings
from app.db.catalogo import conectar


def get_conn() -> Iterator[sqlite3.Connection]:
    """Conexión de solo lectura al catálogo (C08 es de solo lectura durante la operación)."""
    conn = conectar(settings.catalog_db, solo_lectura=True)
    try:
        yield conn
    finally:
        conn.close()


Conexion = Annotated[sqlite3.Connection, Depends(get_conn)]
