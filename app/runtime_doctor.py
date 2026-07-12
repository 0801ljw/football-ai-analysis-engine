from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from app.config import ROOT_DIR, get_settings


PROJECT_FILES = ("app/main.py", "scripts/start.sh", "scripts/smoke.sh", "scripts/setup.sh", "scripts/package_release.sh", "scripts/external_trial_smoke.py", "pyproject.toml")
SKILL_SCRIPTS = ("scripts/fetch_sporttery.py", "scripts/gen_multi_market_report.py")
SHELL_SCRIPTS = ("scripts/start.sh", "scripts/smoke.sh", "scripts/setup.sh", "scripts/package_release.sh", "scripts/external_trial_smoke.py")
PUBLIC_HOSTS = {"0.0.0.0", "::", "*"}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def build_runtime_report() -> dict[str, Any]:
    return run_doctor()


def run_doctor(
    *,
    settings: Any | None = None,
    project_root: Path | None = None,
    python_version: tuple[int, int, int] | None = None,
) -> dict[str, Any]:
    """Inspect runtime readiness without mutating local state."""

    active_settings = settings or get_settings()
    root = (project_root or ROOT_DIR).resolve()
    version = python_version or (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

    checks = [
        _python_version_check(version),
        _project_files_check(root),
        _runs_directory_check(active_settings.runs_path),
        _settings_check(active_settings),
        _desktop_runtime_check(active_settings),
        _exposure_security_check(active_settings),
        _skill_path_check(active_settings.skill_path),
        _skill_scripts_check(active_settings.skill_path),
        _shell_scripts_check(root),
        _runs_parent_writable_check(active_settings.runs_path),
    ]
    status = _status_for_checks(checks)
    return {
        "ok": status != "not_ready",
        "status": status,
        "checks": checks,
        "summary": _summary(status, checks),
    }


def _python_version_check(version: tuple[int, int, int]) -> dict[str, Any]:
    status = "pass" if version >= (3, 11, 0) else "fail"
    return {
        "id": "python_version",
        "label": "Python version",
        "status": status,
        "summary": f"Python {version[0]}.{version[1]}.{version[2]} {'meets' if status == 'pass' else 'does not meet'} >= 3.11.",
        "detail": {"version": list(version), "minimum": [3, 11, 0]},
    }


def _project_files_check(root: Path) -> dict[str, Any]:
    files = {relative: (root / relative).exists() for relative in PROJECT_FILES}
    missing = [relative for relative, exists in files.items() if not exists]
    return {
        "id": "project_files",
        "label": "Project files",
        "status": "fail" if missing else "pass",
        "summary": "Required project files are present." if not missing else f"Missing required project files: {', '.join(missing)}.",
        "detail": {"project_root": str(root), "files": files, "missing": missing},
    }


def _runs_directory_check(runs_path: Path) -> dict[str, Any]:
    target = runs_path.expanduser()
    parent = target.parent
    target_exists = target.exists()
    parent_exists = parent.exists()
    status = "pass" if target_exists or parent_exists else "fail"
    if target_exists:
        summary = "Runs directory exists."
    elif parent_exists:
        summary = "Runs directory can be created by the app because its parent exists."
    else:
        summary = "Runs directory parent is missing."
    return {
        "id": "runs_directory",
        "label": "Runs directory",
        "status": status,
        "summary": summary,
        "detail": {"target": str(target), "exists": target_exists, "parent": str(parent), "parent_exists": parent_exists},
    }


def _settings_check(settings: Any) -> dict[str, Any]:
    return {
        "id": "settings",
        "label": "Runtime settings",
        "status": "pass",
        "summary": "Runtime settings loaded.",
        "detail": {
            "skill_path": str(settings.skill_path),
            "runs_path": str(settings.runs_path),
            "max_run_matches": settings.max_run_matches,
            "default_command_timeout": settings.default_command_timeout,
            "max_concurrent_runs": settings.max_concurrent_runs,
            "db_path": str(getattr(settings, "db_path", "")),
            "host": getattr(settings, "host", "127.0.0.1"),
            "api_token_required": bool(getattr(settings, "api_token", "")),
            "plan": getattr(settings, "plan", "internal"),
            "run_quota": getattr(settings, "run_quota", 0),
            "desktop_mode": bool(getattr(settings, "desktop_mode", False)),
            "app_data_dir": str(getattr(settings, "app_data_dir", "") or ""),
            "config_path": str(getattr(settings, "config_path", "")),
            "logs_path": str(getattr(settings, "logs_path", "")),
            "api_key_storage_mode": getattr(settings, "api_key_storage_mode", "env"),
        },
    }


def _desktop_runtime_check(settings: Any) -> dict[str, Any]:
    desktop_mode = bool(getattr(settings, "desktop_mode", False))
    if not desktop_mode:
        return {
            "id": "desktop_runtime",
            "label": "Desktop runtime",
            "status": "pass",
            "summary": "Desktop mode is disabled.",
            "detail": {"desktop_mode": False},
        }

    required_paths = {
        "app_data_dir": Path(getattr(settings, "app_data_dir", "")).expanduser(),
        "db_parent": Path(getattr(settings, "db_path", "")).expanduser().parent,
        "runs_path": Path(getattr(settings, "runs_path", "")).expanduser(),
        "config_path": Path(getattr(settings, "config_path", "")).expanduser(),
        "logs_path": Path(getattr(settings, "logs_path", "")).expanduser(),
    }
    missing = [name for name, path in required_paths.items() if not path.exists()]
    writable = {
        name: path.exists() and os.access(path, os.W_OK)
        for name, path in required_paths.items()
    }
    not_writable = [name for name, ok in writable.items() if not ok]
    ok = not missing and not not_writable
    return {
        "id": "desktop_runtime",
        "label": "Desktop runtime",
        "status": "pass" if ok else "fail",
        "summary": "Desktop user-data directories are ready." if ok else "Desktop user-data directories are missing or not writable.",
        "detail": {
            "desktop_mode": True,
            "paths": {name: str(path) for name, path in required_paths.items()},
            "missing": missing,
            "writable": writable,
        },
    }


def _exposure_security_check(settings: Any) -> dict[str, Any]:
    host = str(getattr(settings, "host", "127.0.0.1") or "127.0.0.1").strip()
    api_token_set = bool(getattr(settings, "api_token", ""))
    public_bind = host in PUBLIC_HOSTS or host not in LOCAL_HOSTS
    ok = (not public_bind) or api_token_set
    return {
        "id": "exposure_security",
        "label": "Exposure security",
        "status": "pass" if ok else "fail",
        "summary": (
            "Host binding is local or protected by WC_API_TOKEN."
            if ok
            else "Non-local WC_HOST requires WC_API_TOKEN before external trial/deployment."
        ),
        "detail": {"host": host, "public_bind": public_bind, "api_token_required": api_token_set},
    }


def assert_safe_external_binding(settings: Any | None = None) -> None:
    """Raise before serving an unsafe non-local bind without an API token."""

    active_settings = settings or get_settings()
    check = _exposure_security_check(active_settings)
    if check["status"] == "fail":
        raise RuntimeError(check["summary"])


def _skill_path_check(skill_path: Path) -> dict[str, Any]:
    exists = skill_path.expanduser().exists()
    return {
        "id": "skill_path",
        "label": "Hermes skill path",
        "status": "pass" if exists else "warn",
        "summary": "Hermes skill path exists." if exists else "Hermes skill path is missing; demo fallback remains available.",
        "detail": {"path": str(skill_path), "exists": exists},
    }


def _skill_scripts_check(skill_path: Path) -> dict[str, Any]:
    base = skill_path.expanduser()
    if not base.exists():
        return {
            "id": "skill_scripts",
            "label": "Hermes skill scripts",
            "status": "warn",
            "summary": "Hermes skill scripts were not checked because the skill path is missing; demo fallback remains available.",
            "detail": {"skill_path": str(skill_path), "scripts": {}, "missing": list(SKILL_SCRIPTS)},
        }
    scripts = {relative: (base / relative).exists() for relative in SKILL_SCRIPTS}
    missing = [relative for relative, exists in scripts.items() if not exists]
    return {
        "id": "skill_scripts",
        "label": "Hermes skill scripts",
        "status": "fail" if missing else "pass",
        "summary": "Required Hermes skill scripts exist." if not missing else f"Missing Hermes skill scripts: {', '.join(missing)}.",
        "detail": {"skill_path": str(skill_path), "scripts": scripts, "missing": missing},
    }


def _shell_scripts_check(root: Path) -> dict[str, Any]:
    scripts = {
        relative: {"exists": (root / relative).exists(), "executable": os.access(root / relative, os.X_OK)}
        for relative in SHELL_SCRIPTS
    }
    failures = [relative for relative, info in scripts.items() if not info["exists"] or not info["executable"]]
    return {
        "id": "shell_scripts",
        "label": "Shell scripts",
        "status": "fail" if failures else "pass",
        "summary": "Required shell scripts are executable." if not failures else f"Missing or non-executable shell scripts: {', '.join(failures)}.",
        "detail": {"scripts": scripts, "failures": failures},
    }


def _runs_parent_writable_check(runs_path: Path) -> dict[str, Any]:
    target = runs_path.expanduser()
    parent = target.parent
    parent_exists = parent.exists()
    writable = parent_exists and os.access(parent, os.W_OK)
    return {
        "id": "runs_parent_writable",
        "label": "Runs parent writable",
        "status": "pass" if writable else "fail",
        "summary": "Runs parent directory is writable." if writable else "Runs parent directory is missing or not writable.",
        "detail": {"target": str(target), "parent": str(parent), "parent_exists": parent_exists, "writable": writable},
    }


def _status_for_checks(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == "fail" for check in checks):
        return "not_ready"
    if any(check["status"] == "warn" for check in checks):
        return "degraded"
    return "ready"


def _summary(status: str, checks: list[dict[str, Any]]) -> str:
    counts = {name: sum(1 for check in checks if check["status"] == name) for name in ("pass", "warn", "fail")}
    if status == "ready":
        prefix = "Runtime is ready."
    elif status == "degraded":
        prefix = "Runtime is degraded but usable."
    else:
        prefix = "Runtime is not ready."
    return f"{prefix} Checks: {counts['pass']} pass, {counts['warn']} warn, {counts['fail']} fail."


def main() -> int:
    report = build_runtime_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
