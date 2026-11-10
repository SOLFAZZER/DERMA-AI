import pytest
from fastapi.testclient import TestClient

from app.auth import seguridad, usuarios
from app.auth.deps import get_users_conn
from app.db.catalogo import conectar
from app.main import app


@pytest.fixture(autouse=True)
def rondas_bajas(monkeypatch):
    """bcrypt con pocas rondas para que las pruebas sean rápidas."""
    monkeypatch.setattr(seguridad, "RONDAS", 4)


@pytest.fixture
def users_db(tmp_path):
    ruta = tmp_path / "usuarios.db"
    c = conectar(ruta)
    usuarios.crear_esquema(c)
    c.close()
    return ruta


@pytest.fixture
def client_auth(users_db):
    def _conn():
        c = conectar(users_db)
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_users_conn] = _conn
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------- análisis (catálogo + modelo)
import numpy as np

from app.db import catalogo
from app.deps import get_conn
from app.inferencia import registro
from app.inferencia.provisional import ModeloProvisional
from app.inferencia.servicio import ServicioInferencia

CLASES_MODELO = ["AKIEC", "BCC", "BKL", "DF", "MEL", "NV", "VASC"]


class ModeloFalso:
    """Modelo de prueba que devuelve siempre las mismas probabilidades."""

    nombre = "falso"
    provisional = False

    def __init__(self, probs, clases=None):
        self.probs = np.asarray(probs, dtype=float)
        self.clases = clases or CLASES_MODELO

    def predecir(self, tensor):
        return self.probs


@pytest.fixture
def catalogo_db(tmp_path):
    ruta = tmp_path / "catalogo.db"
    c = catalogo.conectar(ruta)
    catalogo.crear_esquema(c)
    catalogo.cargar_catalogo(c)
    c.close()
    return ruta


@pytest.fixture
def client_completo(client_auth, catalogo_db, monkeypatch):
    """Cliente con usuarios y catálogo temporales y el modelo provisional ya cargado."""
    def _conn():
        c = catalogo.conectar(catalogo_db, solo_lectura=True)
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_conn] = _conn
    monkeypatch.setattr(registro, "_servicio", ServicioInferencia(ModeloProvisional(CLASES_MODELO), umbral=0.0))
    return client_auth
