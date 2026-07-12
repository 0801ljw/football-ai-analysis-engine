from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class RunIndex:
    """Small rebuildable SQLite index over file-backed run artifacts."""

    def __init__(self, db_path: Path):
        self.db_path = db_path.expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    status TEXT,
                    title TEXT,
                    nums TEXT,
                    dry_run INTEGER,
                    data_quality_grade TEXT,
                    data_quality_status TEXT,
                    failure_category TEXT,
                    report_exists INTEGER,
                    prediction_exists INTEGER,
                    owner_user_id TEXT,
                    owner_username TEXT
                )
                """
            )
            conn.execute("ALTER TABLE runs ADD COLUMN owner_user_id TEXT") if not self._has_column(conn, "runs", "owner_user_id") else None
            conn.execute("ALTER TABLE runs ADD COLUMN owner_username TEXT") if not self._has_column(conn, "runs", "owner_username") else None
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_quality ON runs(data_quality_grade, data_quality_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_owner ON runs(owner_user_id)")

    @staticmethod
    def _has_column(conn, table: str, column: str) -> bool:
        return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})").fetchall())

    def upsert(self, detail: dict[str, Any], failure_category: str = "") -> None:
        request = detail.get("request", {})
        artifacts = detail.get("artifacts", {})
        quality = detail.get("data_quality") or {}
        owner = detail.get("owner") or {}
        created_at = detail.get("created_at") or request.get("created_at") or ""
        updated_at = detail.get("log", {}).get("finished_at") or detail.get("log", {}).get("started_at") or created_at
        nums = " ".join(str(x) for x in request.get("nums", []))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs(run_id, created_at, updated_at, status, title, nums, dry_run,
                                 data_quality_grade, data_quality_status, failure_category,
                                 report_exists, prediction_exists, owner_user_id, owner_username)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    status=excluded.status,
                    title=excluded.title,
                    nums=excluded.nums,
                    dry_run=excluded.dry_run,
                    data_quality_grade=excluded.data_quality_grade,
                    data_quality_status=excluded.data_quality_status,
                    failure_category=excluded.failure_category,
                    report_exists=excluded.report_exists,
                    prediction_exists=excluded.prediction_exists,
                    owner_user_id=excluded.owner_user_id,
                    owner_username=excluded.owner_username
                """,
                (
                    detail.get("run_id"), created_at, updated_at, detail.get("status"), request.get("title"), nums,
                    1 if request.get("dry_run") else 0, quality.get("grade"), quality.get("status"), failure_category,
                    1 if artifacts.get("report_exists") else 0, 1 if artifacts.get("prediction_exists") else 0,
                    owner.get("user_id") or request.get("owner_user_id") or "",
                    owner.get("username") or request.get("owner_username") or "",
                ),
            )

    def query(
        self,
        status: str = "",
        num: str = "",
        quality: str = "",
        q: str = "",
        owner_user_id: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses=[]; params=[]
        if status:
            clauses.append("status = ?"); params.append(status)
        if num:
            clauses.append("nums LIKE ?"); params.append(f"%{num}%")
        if quality:
            clauses.append("data_quality_grade = ?"); params.append(quality)
        if q:
            clauses.append("(title LIKE ? OR nums LIKE ? OR run_id LIKE ?)"); params.extend([f"%{q}%"]*3)
        if owner_user_id:
            clauses.append("owner_user_id = ?"); params.append(owner_user_id)
        sql="SELECT run_id, created_at, updated_at, status, title, nums, dry_run, data_quality_grade, data_quality_status, failure_category, report_exists, prediction_exists, owner_user_id, owner_username FROM runs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC, run_id DESC LIMIT ?"; params.append(limit)
        with self._connect() as conn:
            rows=conn.execute(sql, params).fetchall()
        keys=["run_id","created_at","updated_at","status","title","nums","dry_run","data_quality_grade","data_quality_status","failure_category","report_exists","prediction_exists","owner_user_id","owner_username"]
        return [dict(zip(keys,row)) for row in rows]

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total=conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            by_status=dict(conn.execute("SELECT status, COUNT(*) FROM runs GROUP BY status").fetchall())
        return {"total_runs_indexed": total, "by_status": by_status, "db_path": str(self.db_path)}
