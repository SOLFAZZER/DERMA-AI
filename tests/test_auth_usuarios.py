from datetime import timedelta

import pytest

from app.auth import usuarios
from app.db.catalogo import conectar


@pytest.fixture
def conn(users_db):
    c = conectar(users_db)
    yield c
    c.close()


def nuevo(conn):
    return usuarios.crear_usuario(conn, "a@b.co", "hash")


def test_cinco_fallos_bloquean_quince_minutos(conn):
    uid = nuevo(conn)
    t0 = usuarios.ahora_utc()
    for _ in range(4):
        usuarios.registrar_fallo(conn, uid, t0)
    assert usuarios.segundos_de_bloqueo(usuarios.buscar_por_id(conn, uid), t0) == 0
    usuarios.registrar_fallo(conn, uid, t0)
    u = usuarios.buscar_por_id(conn, uid)
    assert usuarios.segundos_de_bloqueo(u, t0) == 15 * 60


def test_el_bloqueo_termina_a_los_quince_minutos(conn):
    uid = nuevo(conn)
    t0 = usuarios.ahora_utc()
    for _ in range(5):
        usuarios.registrar_fallo(conn, uid, t0)
    u = usuarios.buscar_por_id(conn, uid)
    assert usuarios.segundos_de_bloqueo(u, t0 + timedelta(minutes=16)) == 0


def test_exito_reinicia_los_intentos(conn):
    uid = nuevo(conn)
    for _ in range(3):
        usuarios.registrar_fallo(conn, uid)
    usuarios.registrar_exito(conn, uid)
    assert usuarios.buscar_por_id(conn, uid)["intentos_fallidos"] == 0
