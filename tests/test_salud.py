from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_salud_responde_ok():
    r = client.get("/api/salud")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "ok"
    assert "version" in cuerpo
