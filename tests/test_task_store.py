from pathlib import Path
from app.task_store import TaskStore

def test_lifecycle(tmp_path: Path):
    st = TaskStore(tmp_path / "t.db")
    st.init()
    st.create("t1", "p1", "ltx-2.3-local", {"duration": 5})
    assert st.get("t1")["status"] == "queued"
    st.set_status("t1", "running")
    st.set_status("t1", "succeeded", video_file="files/t1.mp4")
    row = st.get("t1")
    assert row["status"] == "succeeded" and row["video_file"] == "files/t1.mp4"
    assert st.get("missing") is None

def test_fail_pending_on_boot(tmp_path: Path):
    st = TaskStore(tmp_path / "t.db")
    st.init()
    st.create("t1", "p1", "m", {})
    st.create("t2", "p2", "m", {})
    st.set_status("t2", "succeeded", video_file="x")
    st.fail_pending("gateway restart")
    assert st.get("t1")["status"] == "failed"
    assert "restart" in st.get("t1")["error"]
    assert st.get("t2")["status"] == "succeeded"   # 已完成不动

def test_timeout_uses_updated_at(tmp_path: Path):
    st = TaskStore(tmp_path / "t.db"); st.init()
    st.create("t1", "p1", "m", {})
    st.set_status("t1", "running")
    row = st.get("t1")
    assert row["updated_at"] > 0
