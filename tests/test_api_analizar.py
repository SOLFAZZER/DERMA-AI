import io

from PIL import Image

from app.config import settings

MAX = settings.max_upload_mb * 1024 * 1024
CUENTA = {"correo": "ana@correo.com", "contrasena": "clave-segura-1", "acepta_aviso": True}


def jpeg(tamano=(300, 200)):
    buf = io.BytesIO()
    Image.new("RGB", tamano, (120, 60, 30)).save(buf, "JPEG")
    return buf.getvalue()


def con_sesion(client):
    assert client.post("/api/auth/registro", json=CUENTA).status_code == 201
    return client


def subir(client, nombre, contenido, tipo="image/jpeg"):
    return client.post("/api/analizar", files={"imagen": (nombre, contenido, tipo)})


def test_sin_sesion_da_401(client_auth):
    assert subir(client_auth, "a.jpg", jpeg()).status_code == 401


def test_imagen_valida_pasa_la_validacion(client_auth):
    # Todavía no hay inferencia conectada: responde 501 pero confirma que la imagen es válida.
    r = subir(con_sesion(client_auth), "a.jpg", jpeg())
    assert r.status_code == 501
    assert "[1, 224, 224, 3]" in r.json()["detail"]


def test_sin_archivo_da_400(client_auth):
    assert con_sesion(client_auth).post("/api/analizar").status_code == 400


def test_formato_no_permitido_da_400(client_auth):
    c = con_sesion(client_auth)
    assert subir(c, "a.gif", jpeg(), "image/gif").status_code == 400
    assert subir(c, "a.jpg", b"texto plano").status_code == 400


def test_imagen_danada_da_422(client_auth):
    c = con_sesion(client_auth)
    datos = jpeg((600, 400))
    assert subir(c, "a.jpg", datos[: len(datos) // 2]).status_code == 422
    assert subir(c, "a.jpg", b"").status_code == 422


def test_archivo_un_poco_mayor_al_limite_da_413(client_auth):
    # Supera 5 MB pero cabe en el margen del middleware: lo corta la lectura por trozos.
    assert subir(con_sesion(client_auth), "a.jpg", b"\xff" * (MAX + 10)).status_code == 413


def test_archivo_muy_grande_da_413_sin_procesarlo(client_auth):
    assert subir(con_sesion(client_auth), "a.jpg", b"\xff" * (MAX + 500_000)).status_code == 413


def test_cuerpo_sin_content_length_tambien_da_413(client_auth):
    c = con_sesion(client_auth)

    def trozos():
        for _ in range(8):
            yield b"x" * (1024 * 1024)

    r = c.post("/api/analizar", content=trozos(),
               headers={"content-type": "multipart/form-data; boundary=zzz"})
    assert r.status_code == 413
