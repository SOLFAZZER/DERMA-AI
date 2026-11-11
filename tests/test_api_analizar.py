import base64
import io

import numpy as np
import pytest
from PIL import Image

from app.config import settings
from app.inferencia import registro
from app.inferencia.base import InferenciaNoDisponible
from app.inferencia.servicio import ServicioInferencia
from tests.conftest import ModeloFalso

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


# ---------------------------------------------------------------- errores de entrada

def test_sin_sesion_da_401(client_completo):
    assert subir(client_completo, "a.jpg", jpeg()).status_code == 401


def test_sin_archivo_da_400(client_completo):
    assert con_sesion(client_completo).post("/api/analizar").status_code == 400


def test_formato_no_permitido_da_400(client_completo):
    c = con_sesion(client_completo)
    assert subir(c, "a.gif", jpeg(), "image/gif").status_code == 400
    assert subir(c, "a.jpg", b"texto plano").status_code == 400


def test_imagen_danada_da_422(client_completo):
    c = con_sesion(client_completo)
    datos = jpeg((600, 400))
    assert subir(c, "a.jpg", datos[: len(datos) // 2]).status_code == 422
    assert subir(c, "a.jpg", b"").status_code == 422


def test_archivo_un_poco_mayor_al_limite_da_413(client_completo):
    assert subir(con_sesion(client_completo), "a.jpg", b"\xff" * (MAX + 10)).status_code == 413


def test_archivo_muy_grande_da_413_sin_procesarlo(client_completo):
    assert subir(con_sesion(client_completo), "a.jpg", b"\xff" * (MAX + 500_000)).status_code == 413


def test_cuerpo_sin_content_length_tambien_da_413(client_completo):
    c = con_sesion(client_completo)

    def trozos():
        for _ in range(8):
            yield b"x" * (1024 * 1024)

    r = c.post("/api/analizar", content=trozos(),
               headers={"content-type": "multipart/form-data; boundary=zzz"})
    assert r.status_code == 413


def test_los_errores_de_imagen_se_validan_antes_que_el_modelo(client_completo, monkeypatch):
    monkeypatch.setattr(registro, "_servicio", None)
    monkeypatch.setattr(registro, "obtener_servicio", lambda: (_ for _ in ()).throw(InferenciaNoDisponible("x")))
    assert subir(con_sesion(client_completo), "a.txt", b"hola").status_code == 400


# ---------------------------------------------------------------- respuesta correcta (I01)

def test_imagen_valida_devuelve_el_resultado(client_completo):
    r = subir(con_sesion(client_completo), "a.jpg", jpeg())
    assert r.status_code == 200
    cuerpo = r.json()
    assert set(cuerpo) == {"categoria", "confianza", "baja_confianza", "probabilidades",
                           "mapa_calor", "explicacion_mapa", "mensaje", "version_modelo", "aviso"}
    cat = cuerpo["categoria"]
    assert cat["codigo"] in {"AKIEC", "BCC", "BKL", "DF", "MEL", "NV", "VASC"}
    assert cat["nombre"] and cat["descripcion"] and cat["nivel_riesgo"]
    assert cuerpo["aviso"]


def test_las_probabilidades_suman_100_y_van_de_mayor_a_menor(client_completo):
    cuerpo = subir(con_sesion(client_completo), "a.jpg", jpeg()).json()
    pct = [p["porcentaje"] for p in cuerpo["probabilidades"]]
    assert len(pct) == 7
    assert pct == sorted(pct, reverse=True)
    assert sum(pct) == pytest.approx(100, abs=0.5)
    assert cuerpo["probabilidades"][0]["codigo"] == cuerpo["categoria"]["codigo"]
    assert cuerpo["confianza"] == pct[0]


def test_el_modelo_provisional_se_avisa_en_el_mensaje(client_completo):
    assert "PROVISIONAL" in subir(con_sesion(client_completo), "a.jpg", jpeg()).json()["mensaje"]


def test_baja_confianza_se_marca_y_se_avisa(client_completo, monkeypatch):
    modelo = ModeloFalso([0.05, 0.1, 0.05, 0.02, 0.3, 0.45, 0.03])
    monkeypatch.setattr(registro, "_servicio", ServicioInferencia(modelo, umbral=0.6))
    cuerpo = subir(con_sesion(client_completo), "a.jpg", jpeg()).json()
    assert cuerpo["categoria"]["codigo"] == "NV"
    assert cuerpo["baja_confianza"] is True
    assert "confianza del resultado es baja" in cuerpo["mensaje"]


def test_alta_confianza_no_marca_baja_confianza(client_completo, monkeypatch):
    modelo = ModeloFalso([0.01, 0.01, 0.01, 0.01, 0.02, 0.93, 0.01])
    monkeypatch.setattr(registro, "_servicio", ServicioInferencia(modelo, umbral=0.6))
    cuerpo = subir(con_sesion(client_completo), "a.jpg", jpeg()).json()
    assert cuerpo["baja_confianza"] is False and cuerpo["confianza"] == 93.0


def test_sin_modelo_da_503(client_completo, monkeypatch):
    monkeypatch.setattr(registro, "_servicio", None)
    monkeypatch.setattr(registro, "obtener_servicio", lambda: (_ for _ in ()).throw(InferenciaNoDisponible("x")))
    assert subir(con_sesion(client_completo), "a.jpg", jpeg()).status_code == 503


def test_error_inesperado_da_500(client_completo, monkeypatch):
    class Roto(ModeloFalso):
        def predecir(self, tensor):
            raise RuntimeError("falla")

    monkeypatch.setattr(registro, "_servicio", ServicioInferencia(Roto(np.zeros(7))))
    assert subir(con_sesion(client_completo), "a.jpg", jpeg()).status_code == 500


# ---------------------------------------------------------------- mapa de calor (Grad-CAM)

def test_la_respuesta_incluye_el_mapa_de_calor_como_png(client_completo):
    cuerpo = subir(con_sesion(client_completo), "a.jpg", jpeg((640, 480))).json()
    png = Image.open(io.BytesIO(base64.b64decode(cuerpo["mapa_calor"])))
    assert png.format == "PNG" and png.size == (224, 224) and png.mode == "RGB"
    assert "ayuda visual" in cuerpo["explicacion_mapa"]


def test_si_falla_el_mapa_igual_se_entrega_la_categoria(client_completo, monkeypatch):
    class SinMapa(ModeloFalso):
        def mapa_calor(self, tensor, indice):
            raise RuntimeError("falla Grad-CAM")

    modelo = SinMapa([0.01, 0.01, 0.01, 0.01, 0.02, 0.93, 0.01])
    monkeypatch.setattr(registro, "_servicio", ServicioInferencia(modelo, umbral=0.6))
    r = subir(con_sesion(client_completo), "a.jpg", jpeg())
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["mapa_calor"] == "" and cuerpo["explicacion_mapa"] == ""
    assert "No se pudo generar el mapa de calor" in cuerpo["mensaje"]
    assert cuerpo["categoria"]["codigo"] == "NV" and cuerpo["confianza"] == 93.0


def test_modelo_sin_mapa_lo_dice(client_completo, monkeypatch):
    modelo = ModeloFalso([0.01, 0.01, 0.01, 0.01, 0.02, 0.93, 0.01])
    monkeypatch.setattr(registro, "_servicio", ServicioInferencia(modelo, umbral=0.6))
    cuerpo = subir(con_sesion(client_completo), "a.jpg", jpeg()).json()
    assert cuerpo["mapa_calor"] == "" and "no ofrece mapa de calor" in cuerpo["mensaje"]
