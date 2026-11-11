import pytest
from fastapi.testclient import TestClient

from app.db import catalogo
from app.deps import get_conn
from app.main import app


@pytest.fixture
def db_ruta(tmp_path):
    ruta = tmp_path / "catalogo.db"
    c = catalogo.conectar(ruta)
    catalogo.crear_esquema(c)
    catalogo.cargar_catalogo(c)
    c.close()
    return ruta


@pytest.fixture
def client(db_ruta):
    def _conn():
        c = catalogo.conectar(db_ruta, solo_lectura=True)
        try:
            yield c
        finally:
            c.close()
    app.dependency_overrides[get_conn] = _conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_lesiones_devuelve_las_7_clases(client):
    r = client.get("/api/lesiones")
    assert r.status_code == 200
    lista = r.json()["lesiones"]
    assert len(lista) == 7
    assert all(x["descripcion"] for x in lista)


def test_modelo_sin_version_da_404(client):
    assert client.get("/api/modelo").status_code == 404


def test_modelo_con_version_da_200(client, db_ruta):
    c = catalogo.conectar(db_ruta)
    catalogo.registrar_version_modelo(
        c, arquitectura="MobileNetV2", fecha="2026-11-05", epocas=40, hiperparametros=None,
        ruta_archivo="models/m.keras",
        globales={"exactitud": 0.8, "precision": 0.8, "sensibilidad": 0.8, "f1": 0.8},
        por_clase={"MEL": {"precision": 0.4, "sensibilidad": 0.5, "f1": 0.45}})
    c.close()
    r = client.get("/api/modelo")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["arquitectura"] == "MobileNetV2"
    assert cuerpo["metricas"]["exactitud"] == 0.8
