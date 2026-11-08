from __future__ import annotations
import json, sqlite3, time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks(
  id TEXT PRIMARY KEY, prompt_id TEXT, model TEXT, status TEXT,
  params TEXT, video_file TEXT DEFAULT '', error TEXT DEFAULT '',
  created_at REAL, updated_at REAL);
"""

class TaskStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def init(self):
        self._conn.execute(_SCHEMA); self._conn.commit()

    def create(self, task_id: str, prompt_id: str, model: str, params: dict):
        now = time.time()
        self._conn.execute(
            "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)",
            (task_id, prompt_id, model, "queued", json.dumps(params), "", "", now, now))
        self._conn.commit()

    def get(self, task_id: str) -> dict | None:
        r = self._conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(r) if r else None

    def set_status(self, task_id: str, status: str, error: str = "", video_file: str = ""):
        self._conn.execute(
            "UPDATE tasks SET status=?, error=?, video_file=?, updated_at=? WHERE id=?",
            (status, error, video_file, time.time(), task_id))
        self._conn.commit()

    def fail_pending(self, reason: str):
        self._conn.execute(
            "UPDATE tasks SET status='failed', error=?, updated_at=? "
            "WHERE status IN ('queued','running')", (reason, time.time()))
        self._conn.commit()
