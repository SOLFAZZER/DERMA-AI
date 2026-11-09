"""Almacén de usuarios (archivo SQLite aparte, solo lo usa C09).

Guarda únicamente correo, hash de la contraseña y datos de bloqueo (DERMA-SRS-9.3 y 12.5).
No se asocia ninguna imagen ni resultado al usuario (DERMA-SRS-9.1).
"""
import math
import sqlite3
from datetime import UTC, datetime, timedelta

MAX_INTENTOS = 5
BLOQUEO_MINUTOS = 15

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuario (
  id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
  correo TEXT NOT NULL UNIQUE,
  hash_contrasena TEXT NOT NULL,
  fecha_registro TEXT NOT NULL,
  intentos_fallidos INTEGER NOT NULL DEFAULT 0 CHECK (intentos_fallidos >= 0),
  bloqueado_hasta TEXT
);
"""


def ahora_utc() -> datetime:
    return datetime.now(UTC)


def crear_esquema(conn: sqlite3.Connection) -> None:
    conn.executescript(ESQUEMA)
    conn.commit()


def buscar_por_correo(conn: sqlite3.Connection, correo: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM usuario WHERE correo = ?", (correo,)).fetchone()


def buscar_por_id(conn: sqlite3.Connection, id_usuario: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM usuario WHERE id_usuario = ?", (id_usuario,)).fetchone()


def crear_usuario(conn: sqlite3.Connection, correo: str, hash_contrasena: str,
                  ahora: datetime | None = None) -> int:
    """Crea el usuario. Lanza sqlite3.IntegrityError si el correo ya existe."""
    ahora = ahora or ahora_utc()
    cur = conn.execute(
        "INSERT INTO usuario (correo, hash_contrasena, fecha_registro) VALUES (?, ?, ?)",
        (correo, hash_contrasena, ahora.isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def segundos_de_bloqueo(usuario: sqlite3.Row, ahora: datetime | None = None) -> int:
    """Segundos que faltan para que termine el bloqueo (0 si no está bloqueado)."""
    if not usuario["bloqueado_hasta"]:
        return 0
    ahora = ahora or ahora_utc()
    faltan = (datetime.fromisoformat(usuario["bloqueado_hasta"]) - ahora).total_seconds()
    return math.ceil(faltan) if faltan > 0 else 0


def registrar_fallo(conn: sqlite3.Connection, id_usuario: int, ahora: datetime | None = None) -> None:
    """Suma un intento fallido; al llegar a 5 bloquea la cuenta 15 minutos."""
    ahora = ahora or ahora_utc()
    actual = buscar_por_id(conn, id_usuario)["intentos_fallidos"] + 1
    if actual >= MAX_INTENTOS:
        hasta = (ahora + timedelta(minutes=BLOQUEO_MINUTOS)).isoformat()
        conn.execute("UPDATE usuario SET intentos_fallidos = 0, bloqueado_hasta = ? WHERE id_usuario = ?",
                     (hasta, id_usuario))
    else:
        conn.execute("UPDATE usuario SET intentos_fallidos = ? WHERE id_usuario = ?", (actual, id_usuario))
    conn.commit()


def registrar_exito(conn: sqlite3.Connection, id_usuario: int) -> None:
    conn.execute("UPDATE usuario SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id_usuario = ?",
                 (id_usuario,))
    conn.commit()
