from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _token_preview(token: str) -> str:
    if len(token) <= 10:
        return token
    return f"{token[:3]}...{token[-4:]}"


class AuthManager:
    """Small SQLite-backed API-token user store.

    This is intentionally simple: per-user API tokens, roles, plans and quotas.
    It is enough for private beta / self-hosted commercial trials without adding
    external auth providers or payment integrations.
    """

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
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    run_quota INTEGER NOT NULL,
                    token_hash TEXT UNIQUE NOT NULL,
                    token_preview TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "token_preview" not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN token_preview TEXT NOT NULL DEFAULT ''")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    run_id TEXT,
                    detail TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_usage ON user_usage_events(user_id,event_type)")

    def has_users(self) -> bool:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM users WHERE active=1").fetchone()[0]) > 0

    def create_user(self, username: str, role: str = "user", plan: str = "free", run_quota: int = 20) -> dict[str, Any]:
        username = username.strip()
        if not username:
            raise ValueError("username is required")
        user_id = secrets.token_hex(8)
        token = "wc_" + secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        token_preview = _token_preview(token)
        created_at = _now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users(user_id,username,role,plan,run_quota,token_hash,token_preview,active,created_at) VALUES(?,?,?,?,?,?,?,1,?)",
                (user_id, username, role, plan, int(run_quota), token_hash, token_preview, created_at),
            )
        return {"user": self.get_user(user_id), "token": token}

    def authenticate(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        token_hash = _hash_token(token)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id,username,role,plan,run_quota,active,created_at,token_preview FROM users WHERE token_hash=? AND active=1",
                (token_hash,),
            ).fetchone()
        return self._row_to_user(row) if row else None

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id,username,role,plan,run_quota,active,created_at,token_preview FROM users WHERE user_id=?",
                (user_id,),
            ).fetchone()
        user = self._row_to_user(row) if row else None
        if user:
            user["quota"] = self.quota_status(user)
        return user

    def list_users(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT user_id,username,role,plan,run_quota,active,created_at,token_preview FROM users ORDER BY created_at DESC"
            ).fetchall()
        users = [self._row_to_user(row) for row in rows]
        for user in users:
            user["quota"] = self.quota_status(user)
        return users

    def update_user(
        self,
        user_id: str,
        role: str | None = None,
        plan: str | None = None,
        run_quota: int | None = None,
        active: bool | None = None,
    ) -> dict[str, Any]:
        updates: list[str] = []
        values: list[Any] = []
        if role is not None:
            updates.append("role=?")
            values.append(role)
        if plan is not None:
            updates.append("plan=?")
            values.append(plan)
        if run_quota is not None:
            updates.append("run_quota=?")
            values.append(int(run_quota))
        if active is not None:
            updates.append("active=?")
            values.append(1 if active else 0)
        if not updates:
            user = self.get_user(user_id)
            if not user:
                raise ValueError("user not found")
            return {"user": user}
        values.append(user_id)
        with self._connect() as conn:
            cursor = conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id=?", values)
            if cursor.rowcount == 0:
                raise ValueError("user not found")
        return {"user": self.get_user(user_id)}

    def reset_token(self, user_id: str) -> dict[str, Any]:
        token = "wc_" + secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        token_preview = _token_preview(token)
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE users SET token_hash=?, token_preview=? WHERE user_id=?",
                (token_hash, token_preview, user_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("user not found")
        return {"user": self.get_user(user_id), "token": token}

    def record_usage(self, user_id: str, event_type: str, run_id: str = "", detail: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO user_usage_events(user_id,created_at,event_type,run_id,detail) VALUES(?,?,?,?,?)",
                (user_id, _now_iso(), event_type, run_id, detail),
            )

    def quota_status(self, user: dict[str, Any]) -> dict[str, Any]:
        user_id = user["user_id"]
        with self._connect() as conn:
            used = int(
                conn.execute(
                    "SELECT COUNT(*) FROM user_usage_events WHERE user_id=? AND event_type='real_run_created'",
                    (user_id,),
                ).fetchone()[0]
            )
        quota = int(user.get("run_quota", 0))
        return {
            "user_id": user_id,
            "username": user.get("username"),
            "role": user.get("role"),
            "plan": user.get("plan"),
            "run_quota": quota,
            "real_runs_used": used,
            "remaining_real_runs": max(quota - used, 0),
            "quota_exceeded": used >= quota,
        }

    def assert_can_create_real_run(self, user: dict[str, Any]) -> None:
        status = self.quota_status(user)
        if status["quota_exceeded"]:
            raise PermissionError(
                f"quota exceeded for user {status['username']}: {status['real_runs_used']}/{status['run_quota']} real runs used"
            )

    def summary(self) -> dict[str, Any]:
        users = self.list_users()
        return {"users": users, "total_users": len(users), "db_path": str(self.db_path)}

    @staticmethod
    def _row_to_user(row) -> dict[str, Any]:
        keys = ["user_id", "username", "role", "plan", "run_quota", "active", "created_at", "token_preview"]
        return dict(zip(keys, row))
