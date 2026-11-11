from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_la_interfaz_se_sirve_en_la_raiz():
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Derma-AI" in r.text and "PROTOTIPO ACADÉMICO" in r.text


def test_se_sirven_los_estilos_el_script_y_el_logo():
    assert client.get("/css/estilos.css").status_code == 200
    assert client.get("/js/app.js").status_code == 200
    assert client.get("/img/logo.png").headers["content-type"] == "image/png"


def test_la_api_sigue_funcionando_con_la_interfaz_montada():
    assert client.get("/api/salud").json()["estado"] == "listo"


def test_cabeceras_de_seguridad():
    h = client.get("/").headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert "script-src 'self'" in h["content-security-policy"]
    assert client.get("/api/salud").headers["cache-control"] == "no-store"


def test_la_documentacion_de_la_api_no_lleva_csp():
    r = client.get("/docs")
    assert r.status_code == 200 and "content-security-policy" not in r.headers


def test_el_html_no_usa_scripts_ni_estilos_en_linea():
    html = client.get("/").text
    assert "style=" not in html and "onclick=" not in html
    assert html.count("<script") == 1 and "<script src=" in html


def test_los_tipos_de_archivo_son_correctos_aunque_el_sistema_los_registre_mal():
    assert client.get("/js/app.js").headers["content-type"].startswith("text/javascript")
    assert client.get("/css/estilos.css").headers["content-type"].startswith("text/css")
