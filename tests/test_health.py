from fastapi.testclient import TestClient
from app.main import app

def test_healthz():
    c = TestClient(app)
    r = c.get("/healthz")
    assert r.status_code == 200 and r.json() == {"ok": True, "comfy": "http://127.0.0.1:8188"}
