import json

from tests.test_api_analizar import con_sesion, jpeg, subir


def resultado(client):
    return subir(con_sesion(client), "a.jpg", jpeg()).json()


def exportar(client, cuerpo, imagen=None, nombre="a.jpg"):
    files = {"imagen": (nombre, imagen, "image/jpeg")} if imagen is not None else None
    return client.post("/api/exportar-pdf", data={"resultado": json.dumps(cuerpo), "fecha": "11/11/2026"},
                       files=files)


def test_sin_sesion_da_401(client_completo):
    assert exportar(client_completo, {}).status_code == 401


def test_devuelve_un_pdf_con_imagen_y_mapa(client_completo):
    r = resultado(client_completo)
    assert r["mapa_calor"]
    resp = exportar(client_completo, r, jpeg())
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF")
    assert resp.content.count(b"/Subtype /Image") >= 2  # imagen original y mapa de calor


def test_funciona_sin_imagen_original(client_completo):
    resp = exportar(client_completo, resultado(client_completo))
    assert resp.status_code == 200 and resp.content.startswith(b"%PDF")


def test_funciona_sin_mapa_de_calor(client_completo):
    r = resultado(client_completo)
    r["mapa_calor"] = ""
    resp = exportar(client_completo, r, jpeg())
    assert resp.status_code == 200 and resp.content.startswith(b"%PDF")


def test_mapa_corrupto_no_rompe_el_pdf(client_completo):
    r = resultado(client_completo)
    r["mapa_calor"] = "AAAA"
    assert exportar(client_completo, r).status_code == 200


def test_texto_con_marcas_no_se_interpreta(client_completo):
    r = resultado(client_completo)
    r["categoria"]["nombre"] = "<b>X</i><font>"
    assert exportar(client_completo, r).status_code == 200


def test_resultado_invalido_da_400(client_completo):
    con_sesion(client_completo)
    for malo in ({"hola": 1}, {"categoria": 3}):
        assert exportar(client_completo, malo).status_code == 400
    resp = client_completo.post("/api/exportar-pdf", data={"resultado": "no es json"})
    assert resp.status_code == 400


def test_imagen_original_invalida_se_rechaza(client_completo):
    r = resultado(client_completo)
    assert exportar(client_completo, r, b"nada", "a.jpg").status_code == 400
    assert exportar(client_completo, r, jpeg(), "a.pdf").status_code == 400


def test_cuerpo_enorme_da_413(client_completo):
    con_sesion(client_completo)
    resp = client_completo.post("/api/exportar-pdf", data={"resultado": "{}"},
                                files={"imagen": ("a.jpg", b"0" * (12 * 1024 * 1024), "image/jpeg")})
    assert resp.status_code == 413
