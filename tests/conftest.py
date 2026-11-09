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
