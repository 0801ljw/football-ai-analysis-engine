import os
from pathlib import Path
from types import SimpleNamespace

from app.setup_guide import build_setup_guide


def test_build_setup_guide_ready_when_required_paths_exist(tmp_path):
    data_path = tmp_path / "data.json"
    data_path.write_text("{}", encoding="utf-8")
    runs_path = tmp_path / "runs"
    skill_path = tmp_path / "skill"
    skill_path.mkdir()
    settings = SimpleNamespace(
        app_name="Test App",
        data_path=data_path,
        runs_path=runs_path,
        skill_path=skill_path,
        max_run_matches=8,
        max_concurrent_runs=1,
        default_command_timeout=60,
    )

    guide = build_setup_guide(settings)

    assert guide["status"] == "ready"
    assert guide["missing"] == []
    assert {"status", "steps", "config", "missing", "commands"} <= set(guide)
    assert "scripts/doctor.sh" in guide["commands"]


def test_build_setup_guide_missing_skill_is_degraded_not_fatal(tmp_path):
    data_path = tmp_path / "data.json"
    data_path.write_text("{}", encoding="utf-8")
    settings = SimpleNamespace(
        app_name="Test App",
        data_path=data_path,
        runs_path=tmp_path / "runs",
        skill_path=tmp_path / "missing-skill",
        max_run_matches=8,
        max_concurrent_runs=1,
        default_command_timeout=60,
    )

    guide = build_setup_guide(settings)

    assert guide["status"] == "degraded"
    skill_missing = next(item for item in guide["missing"] if item["id"] == "skill_path")
    assert skill_missing["fatal"] is False
    assert "demo fallback" in skill_missing["summary"].lower()


def test_setup_script_exists_and_is_executable():
    setup_script = Path("scripts/setup.sh")
    assert setup_script.exists()
    assert os.access(setup_script, os.X_OK)
