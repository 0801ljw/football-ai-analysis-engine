from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import ROOT_DIR, get_settings


def build_setup_guide(settings: Any | None = None) -> dict[str, Any]:
    active_settings = settings or get_settings()
    missing = []

    if not Path(active_settings.data_path).expanduser().exists():
        missing.append(
            {
                "id": "data_path",
                "path": str(active_settings.data_path),
                "fatal": True,
                "summary": "Demo match data is missing.",
            }
        )

    if not Path(active_settings.runs_path).expanduser().parent.exists():
        missing.append(
            {
                "id": "runs_parent",
                "path": str(Path(active_settings.runs_path).expanduser().parent),
                "fatal": True,
                "summary": "Runs directory parent is missing.",
            }
        )

    if not Path(active_settings.skill_path).expanduser().exists():
        missing.append(
            {
                "id": "skill_path",
                "path": str(active_settings.skill_path),
                "fatal": False,
                "summary": "Skill path is missing. demo fallback still works; real mode needs the skill scripts.",
            }
        )

    fatal_missing = any(item["fatal"] for item in missing)
    status = "not_ready" if fatal_missing else "degraded" if missing else "ready"

    return {
        "status": status,
        "steps": [
            "Copy .env.example to .env and adjust WC_* values for this machine.",
            "Run scripts/doctor.sh to inspect local readiness.",
            "Start the app with scripts/start.sh.",
            "Open /api/system/doctor or the setup guide panel to verify runtime state.",
            "Missing WC_SKILL_PATH is not fatal: demo fallback works, but real mode requires fetch_sporttery.py and gen_multi_market_report.py under the skill scripts directory.",
        ],
        "config": {
            "app_name": active_settings.app_name,
            "data_path": str(active_settings.data_path),
            "runs_path": str(active_settings.runs_path),
            "skill_path": str(active_settings.skill_path),
            "max_run_matches": active_settings.max_run_matches,
            "max_concurrent_runs": active_settings.max_concurrent_runs,
            "default_command_timeout": active_settings.default_command_timeout,
            "db_path": str(getattr(active_settings, "db_path", "")),
            "host": getattr(active_settings, "host", "127.0.0.1"),
            "api_token_required": bool(getattr(active_settings, "api_token", "")),
            "plan": getattr(active_settings, "plan", "internal"),
            "run_quota": getattr(active_settings, "run_quota", 0),
            "project_root": str(ROOT_DIR),
        },
        "missing": missing,
        "commands": [
            "cp .env.example .env",
            "scripts/doctor.sh",
            "scripts/start.sh",
            "curl /api/system/doctor",
        ],
    }
