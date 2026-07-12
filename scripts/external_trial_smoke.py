#!/usr/bin/env python3
"""First external-user trial smoke flow.

Runs against an already-started server. It bootstraps/uses an admin token,
creates a trial user, verifies auth boundaries, creates a dry-run report, and
exports the run zip. It intentionally does not fetch real odds.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8787").rstrip("/")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
TRIAL_USERNAME = os.environ.get("TRIAL_USERNAME", f"trial-{int(time.time())}")
TIMEOUT = float(os.environ.get("TRIAL_TIMEOUT", "10"))


@dataclass
class HttpResult:
    status: int
    data: object
    headers: dict[str, str]


def request(method: str, path: str, payload: dict | None = None, token: str = "", expect: int | tuple[int, ...] = 200) -> HttpResult:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-API-Token"] = token
    req = urllib.request.Request(BASE_URL + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            content_type = resp.headers.get("content-type", "")
            data: object
            if "application/json" in content_type:
                data = json.loads(raw.decode("utf-8")) if raw else {}
            else:
                data = {"bytes": len(raw), "content_type": content_type}
            result = HttpResult(resp.status, data, dict(resp.headers.items()))
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            data = {"body": raw.decode("utf-8", errors="replace")}
        result = HttpResult(exc.code, data, dict(exc.headers.items()))
    expected = (expect,) if isinstance(expect, int) else expect
    if result.status not in expected:
        raise AssertionError(f"{method} {path} expected {expected}, got {result.status}: {result.data}")
    return result


def main() -> int:
    print(f"BASE_URL={BASE_URL}")
    doctor = request("GET", "/api/system/doctor")
    print(f"doctor.status={doctor.data.get('status') if isinstance(doctor.data, dict) else 'unknown'}")

    admin_token = ADMIN_TOKEN
    if not admin_token:
        created_admin = request(
            "POST",
            "/api/admin/users",
            {"username": f"trial-admin-{int(time.time())}", "role": "admin", "plan": "internal", "run_quota": 100},
            expect=(200, 401, 403),
        )
        if created_admin.status != 200:
            raise AssertionError("ADMIN_TOKEN is required because bootstrap admin creation is no longer allowed by this server")
        admin_token = created_admin.data["token"]
        print("admin.bootstrap=created")
    else:
        print("admin.bootstrap=provided-token")

    me = request("GET", "/api/me", token=admin_token)
    assert me.data["user"]["role"] == "admin", me.data

    created_user = request(
        "POST",
        "/api/admin/users",
        {"username": TRIAL_USERNAME, "role": "user", "plan": "free", "run_quota": 3},
        token=admin_token,
    )
    user_token = created_user.data["token"]
    print(f"trial_user={TRIAL_USERNAME} token_preview={created_user.data['user']['token_preview']}")

    user_me = request("GET", "/api/me", token=user_token)
    assert user_me.data["user"]["username"] == TRIAL_USERNAME, user_me.data

    forbidden = request("GET", "/api/admin/users", token=user_token, expect=403)
    assert "admin" in str(forbidden.data).lower(), forbidden.data

    run = request(
        "POST",
        "/api/runs",
        {"nums": "086", "title": "外部用户试用 dry-run", "theme": "dark", "dry_run": True, "timeout": 20},
        token=user_token,
    )
    run_id = run.data["run_id"]
    print(f"run_id={run_id} status={run.data['status']}")

    export = request("GET", f"/api/runs/{run_id}/export.zip", token=user_token)
    assert export.data["bytes"] > 100, export.data
    print(f"export_zip_bytes={export.data['bytes']}")

    print("external_trial_smoke=PASS")
    print("Save the one-time trial user token securely; it will not be shown again.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - command-line smoke should print concise failure.
        print(f"external_trial_smoke=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
