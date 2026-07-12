from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class UsageTracker:
    def __init__(self, db_path: Path, plan: str = "internal", run_quota: int = 1000):
        self.db_path = db_path.expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.plan = plan
        self.run_quota = max(0, int(run_quota))
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    run_id TEXT,
                    detail TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_type ON usage_events(event_type)")

    def record(self, event_type: str, run_id: str = "", detail: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO usage_events(created_at,event_type,run_id,detail) VALUES(?,?,?,?)",
                (now_iso(), event_type, run_id, detail),
            )

    def count(self, event_type: str) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM usage_events WHERE event_type=?", (event_type,)).fetchone()[0])

    def quota_status(self) -> dict[str, Any]:
        used = self.count("real_run_created")
        remaining = max(self.run_quota - used, 0)
        return {"plan": self.plan, "run_quota": self.run_quota, "real_runs_used": used, "remaining_real_runs": remaining, "quota_exceeded": used >= self.run_quota}

    def assert_can_create_real_run(self) -> None:
        status = self.quota_status()
        if status["quota_exceeded"]:
            raise PermissionError(f"quota exceeded for plan {self.plan}: {status['real_runs_used']}/{status['run_quota']} real runs used")

    def summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            events=dict(conn.execute("SELECT event_type, COUNT(*) FROM usage_events GROUP BY event_type").fetchall())
            recent=[{"created_at":r[0],"event_type":r[1],"run_id":r[2],"detail":r[3]} for r in conn.execute("SELECT created_at,event_type,run_id,detail FROM usage_events ORDER BY id DESC LIMIT 20").fetchall()]
        return {"quota": self.quota_status(), "events": events, "recent": recent, "db_path": str(self.db_path)}
