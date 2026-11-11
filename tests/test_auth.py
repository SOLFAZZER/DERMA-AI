from app.auth import seguridad, usuarios
from app.db.catalogo import conectar

BUENO = {"correo": "ana@correo.com", "contrasena": "clave-segura-1", "acepta_aviso": True}


def registrar(client, **cambios):
    return client.post("/api/auth/registro", json={**BUENO, **cambios})


def test_registro_crea_cuenta_e_inicia_sesion(client_auth):
    r = registrar(client_auth)
    assert r.status_code == 201
    assert r.json()["correo"] == "ana@correo.com"
    yo = client_auth.get("/api/auth/yo")
    assert yo.status_code == 200 and yo.json()["correo"] == "ana@correo.com"


def test_la_cookie_es_httponly_y_samesite(client_auth):
    cookie = registrar(client_auth).headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_la_contrasena_se_guarda_con_hash(client_auth, users_db):
    registrar(client_auth)
    c = conectar(users_db)
    fila = usuarios.buscar_por_correo(c, "ana@correo.com")
    c.close()
    assert fila["hash_contrasena"] != BUENO["contrasena"]
    assert fila["hash_contrasena"].startswith("$2")
    assert seguridad.verificar_contrasena(BUENO["contrasena"], fila["hash_contrasena"])


def test_registro_rechaza_datos_no_validos(client_auth):
    assert registrar(client_auth, correo="no-es-correo").status_code == 400
    assert registrar(client_auth, contrasena="corta").status_code == 400
    assert registrar(client_auth, contrasena="a" * 73).status_code == 400
    assert registrar(client_auth, acepta_aviso=False).status_code == 400
    assert client_auth.post("/api/auth/registro", json={"correo": "x@y.co"}).status_code == 400


def test_registro_con_correo_repetido_da_409(client_auth):
    assert registrar(client_auth).status_code == 201
    assert registrar(client_auth, correo="ANA@correo.com ").status_code == 409


def test_login_correcto(client_auth):
    registrar(client_auth)
    client_auth.post("/api/auth/logout")
    r = client_auth.post("/api/auth/login", json={"correo": "ana@correo.com", "contrasena": BUENO["contrasena"]})
    assert r.status_code == 200
    assert client_auth.get("/api/auth/yo").status_code == 200


def test_login_incorrecto_da_401_con_el_mismo_mensaje(client_auth):
    registrar(client_auth)
    mala = client_auth.post("/api/auth/login", json={"correo": "ana@correo.com", "contrasena": "otra-clave-xx"})
    nadie = client_auth.post("/api/auth/login", json={"correo": "nadie@correo.com", "contrasena": "otra-clave-xx"})
    assert mala.status_code == nadie.status_code == 401
    assert mala.json() == nadie.json()


def test_cinco_fallos_bloquean_y_responde_429(client_auth):
    registrar(client_auth)
    client_auth.post("/api/auth/logout")
    for _ in range(5):
        r = client_auth.post("/api/auth/login", json={"correo": "ana@correo.com", "contrasena": "mal-mal-mal"})
        assert r.status_code == 401
    bloqueado = client_auth.post("/api/auth/login", json={"correo": "ana@correo.com", "contrasena": BUENO["contrasena"]})
    assert bloqueado.status_code == 429
    assert int(bloqueado.headers["retry-after"]) > 0


def test_logout_cierra_la_sesion(client_auth):
    registrar(client_auth)
    assert client_auth.post("/api/auth/logout").status_code == 204
    assert client_auth.get("/api/auth/yo").status_code == 401


def test_sin_sesion_da_401(client_auth):
    assert client_auth.get("/api/auth/yo").status_code == 401


def test_token_manipulado_o_vencido_da_401(client_auth):
    client_auth.cookies.set("derma_sesion", "token.falso.aqui")
    assert client_auth.get("/api/auth/yo").status_code == 401
    vencido = seguridad.crear_token(1, "ana@correo.com", minutos=-1)
    client_auth.cookies.set("derma_sesion", vencido)
    assert client_auth.get("/api/auth/yo").status_code == 401


def test_cuenta_borrada_ya_no_tiene_sesion(client_auth, users_db):
    registrar(client_auth)
    c = conectar(users_db)
    c.execute("DELETE FROM usuario")
    c.commit()
    c.close()
    assert client_auth.get("/api/auth/yo").status_code == 401
