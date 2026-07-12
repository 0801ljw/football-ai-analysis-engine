import sys
from pathlib import Path
from types import SimpleNamespace

from app import runtime_doctor


def _settings(tmp_path, skill_path):
    return SimpleNamespace(
        skill_path=skill_path,
        runs_path=tmp_path / "runs",
        max_run_matches=8,
        default_command_timeout=60,
        max_concurrent_runs=1,
    )


def test_runtime_doctor_reports_ready_when_required_paths_are_present(tmp_path):
    skill_path = tmp_path / "skill"
    (skill_path / "scripts").mkdir(parents=True)
    (skill_path / "scripts" / "fetch_sporttery.py").write_text("", encoding="utf-8")
    (skill_path / "scripts" / "gen_multi_market_report.py").write_text("", encoding="utf-8")

    result = runtime_doctor.run_doctor(
        settings=_settings(tmp_path, skill_path),
        project_root=Path.cwd(),
        python_version=(3, 11, 0),
    )

    assert result["ok"] is True
    assert result["status"] == "ready"
    assert {check["id"] for check in result["checks"]} >= {
        "python_version",
        "project_files",
        "runs_directory",
        "settings",
        "exposure_security",
        "skill_path",
        "skill_scripts",
        "shell_scripts",
        "runs_parent_writable",
    }


def test_runtime_doctor_degrades_when_skill_path_is_missing(tmp_path):
    result = runtime_doctor.run_doctor(
        settings=_settings(tmp_path, tmp_path / "missing-skill"),
        project_root=Path.cwd(),
        python_version=(3, 11, 0),
    )

    assert result["ok"] is True
    assert result["status"] == "degraded"
    assert _check(result, "skill_path")["status"] == "warn"
    assert "demo fallback" in _check(result, "skill_path")["summary"]


def test_runtime_doctor_not_ready_when_required_project_file_is_missing(tmp_path):
    root = tmp_path / "project"
    (root / "app").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "app" / "main.py").write_text("", encoding="utf-8")
    (root / "scripts" / "start.sh").write_text("", encoding="utf-8")
    (root / "scripts" / "smoke.sh").write_text("", encoding="utf-8")

    result = runtime_doctor.run_doctor(
        settings=_settings(tmp_path, tmp_path / "missing-skill"),
        project_root=root,
        python_version=(sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
    )

    assert result["ok"] is False
    assert result["status"] == "not_ready"
    assert _check(result, "project_files")["status"] == "fail"


def test_runtime_doctor_fails_public_bind_without_api_token(tmp_path):
    settings = _settings(tmp_path, tmp_path / "missing-skill")
    settings.host = "0.0.0.0"
    settings.api_token = ""

    result = runtime_doctor.run_doctor(
        settings=settings,
        project_root=Path.cwd(),
        python_version=(3, 11, 0),
    )

    assert result["ok"] is False
    assert result["status"] == "not_ready"
    assert _check(result, "exposure_security")["status"] == "fail"


def test_runtime_doctor_allows_public_bind_with_api_token(tmp_path):
    settings = _settings(tmp_path, tmp_path / "missing-skill")
    settings.host = "0.0.0.0"
    settings.api_token = "secret-token"

    result = runtime_doctor.run_doctor(
        settings=settings,
        project_root=Path.cwd(),
        python_version=(3, 11, 0),
    )

    assert _check(result, "exposure_security")["status"] == "pass"


def test_runtime_doctor_adds_desktop_runtime_check(tmp_path):
    settings = _settings(tmp_path, tmp_path / "missing-skill")
    settings.desktop_mode = True
    settings.app_data_dir = tmp_path / "desktop-data"
    settings.db_path = settings.app_data_dir / "data" / "app.db"
    settings.runs_path = settings.app_data_dir / "runs"
    settings.config_path = settings.app_data_dir / "config"
    settings.logs_path = settings.app_data_dir / "logs"
    for path in (settings.db_path.parent, settings.runs_path, settings.config_path, settings.logs_path):
        path.mkdir(parents=True)

    result = runtime_doctor.run_doctor(
        settings=settings,
        project_root=Path.cwd(),
        python_version=(3, 11, 0),
    )

    check = _check(result, "desktop_runtime")
    assert check["status"] == "pass"
    assert check["detail"]["desktop_mode"] is True
    assert result["status"] == "degraded"
    assert _check(result, "skill_path")["status"] == "warn"


def _check(result, check_id):
    return next(check for check in result["checks"] if check["id"] == check_id)
