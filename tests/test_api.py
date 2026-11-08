import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from tests.fakes import FakeComfy

PNG_1PX = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
           "nGNgYGBgAAAABQABh6FO1AAAAABJRU5ErkJggg==")

@pytest.fixture
def client(tmp_path):
    fake = FakeComfy()
    from app.task_store import TaskStore
    st = TaskStore(tmp_path / "t.db"); st.init()
    app.state.store = st
    app.state.comfy = fake
    app.state.files_dir = tmp_path / "files"; app.state.files_dir.mkdir()
    app.state.workflows_dir = Path(__file__).resolve().parents[1] / "workflows"
    app.state.registry_path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "registry_test.yaml"
    app.state.public_base = "http://127.0.0.1:8300"
    with TestClient(app) as c:
        yield c, fake

def test_models(client):
    c, _ = client
    r = c.get("/models")
    assert r.status_code == 200
    assert r.json()["models"][0]["name"] == "ltx-2.3-local"

def test_submit_poll_download(client):
    c, fake = client
    r = c.post("/contents/generations/tasks", json={
        "model": "ltx-2.3-local",
        "content": [{"type": "image_url", "image_url": {"url": PNG_1PX}},
                    {"type": "text", "text": "test"}],
        "duration": 5, "resolution": "720p"})
    assert r.status_code == 200 and r.json()["id"].startswith("t_")
    tid = r.json()["id"]
    fake.finish_ok()
    r2 = c.get(f"/contents/generations/tasks/{tid}")
    assert r2.json()["status"] == "succeeded"
    url = r2.json()["content"]["video_url"]
    r3 = c.get(url.split("8300", 1)[1])
    assert r3.status_code == 200 and r3.content.startswith(b"\x00\x00\x00")

def test_submit_400s(client):
    c, _ = client
    body = {"model": "nope", "content": [], "duration": 5, "resolution": "720p"}
    assert c.post("/contents/generations/tasks", json=body).status_code == 400
    body2 = {"model": "ltx-2.3-local",
             "content": [{"type": "image_url", "image_url": {"url": PNG_1PX}},
                         {"type": "text", "text": "t"}],
             "duration": 99, "resolution": "720p"}
    assert c.post("/contents/generations/tasks", json=body2).status_code == 400

def test_404_and_comfy_down(client):
    c, fake = client
    assert c.get("/contents/generations/tasks/t_missing").status_code == 404
    fake.down = True
    r = c.post("/contents/generations/tasks", json={
        "model": "ltx-2.3-local",
        "content": [{"type": "image_url", "image_url": {"url": PNG_1PX}},
                    {"type": "text", "text": "t"}],
        "duration": 5, "resolution": "720p"})
    assert r.status_code == 503

def test_timeout_marks_failed(client):
    c, fake = client
    r = c.post("/contents/generations/tasks", json={
        "model": "ltx-2.3-local",
        "content": [{"type": "image_url", "image_url": {"url": PNG_1PX}},
                    {"type": "text", "text": "t"}],
        "duration": 5, "resolution": "720p"})
    tid = r.json()["id"]
    app.state.store._conn.execute("UPDATE tasks SET created_at=0 WHERE id=?", (tid,))
    app.state.store._conn.commit()
    r2 = c.get(f"/contents/generations/tasks/{tid}")
    assert r2.json()["status"] == "failed" and "timeout" in r2.json()["error"]["message"]
