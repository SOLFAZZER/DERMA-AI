"""Privacidad: qué guarda (y qué no) el servidor. Cubre CP027 y CP030."""
import os
import sqlite3

from app.db.catalogo import conectar
from tests.test_api_analizar import CUENTA, con_sesion, jpeg, subir
from tests.test_exportar_pdf import exportar


def _archivos(carpeta):
    return {os.path.join(r, f) for r, _, fs in os.walk(carpeta) for f in fs}


def _tablas(ruta):
    c = sqlite3.connect(ruta)
    try:
        return {f[0] for f in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        c.close()


def _volcado(ruta):
    """Todo el contenido de la base de datos en un solo texto (para buscar datos que no deben estar)."""
    c = sqlite3.connect(ruta)
    try:
        return "\n".join(c.iterdump())
    finally:
        c.close()


def test_cp027_analizar_y_exportar_no_guardan_nada(client_completo, users_db, catalogo_db, tmp_path):
    """La imagen, el resultado y el PDF no quedan en archivos ni en las bases de datos."""
    cliente = con_sesion(client_completo)
    antes_archivos = _archivos(tmp_path)
    antes_usuarios = _volcado(users_db)
    antes_catalogo = _volcado(catalogo_db)

    foto = jpeg((321, 213))
    resultado = subir(cliente, "foto_privada.jpg", foto).json()
    pdf = exportar(cliente, resultado, foto, nombre="foto_privada.jpg")
    assert pdf.status_code == 200

    # 1) no aparecen archivos nuevos (el PDF y la imagen solo viajan en la respuesta)
    assert _archivos(tmp_path) == antes_archivos
    # 2) las bases de datos quedan idénticas
    assert _volcado(users_db) == antes_usuarios
    assert _volcado(catalogo_db) == antes_catalogo
    # 3) no existe ninguna tabla para imágenes, resultados o PDF
    tablas = _tablas(users_db) | _tablas(catalogo_db)
    assert not [t for t in tablas if any(p in t.lower() for p in ("imagen", "resultado", "analisis", "pdf"))]
    # 4) el nombre del archivo subido no se guarda
    assert "foto_privada" not in antes_usuarios + _volcado(users_db) + _volcado(catalogo_db)


def test_cp030_el_registro_solo_guarda_correo_hash_y_control(client_auth, users_db):
    """El usuario guarda correo, hash y datos de control; nunca la contraseña en texto plano."""
    assert client_auth.post("/api/auth/registro", json=CUENTA).status_code == 201

    c = conectar(users_db)
    columnas = [f["name"] for f in c.execute("PRAGMA table_info(usuario)")]
    fila = dict(c.execute("SELECT * FROM usuario").fetchone())
    total = c.execute("SELECT COUNT(*) FROM usuario").fetchone()[0]
    c.close()

    assert total == 1
    # solo estas columnas: correo, hash y datos de control (sin nombre, teléfono, etc.)
    assert columnas == ["id_usuario", "correo", "hash_contrasena", "fecha_registro",
                        "intentos_fallidos", "bloqueado_hasta"]
    assert fila["correo"] == CUENTA["correo"]
    assert fila["hash_contrasena"].startswith("$2") and len(fila["hash_contrasena"]) == 60
    # la contraseña no aparece en ningún lugar de la base de datos
    assert CUENTA["contrasena"] not in _volcado(users_db)
    assert fila["intentos_fallidos"] == 0 and fila["bloqueado_hasta"] is None
