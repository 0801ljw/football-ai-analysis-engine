from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

import pytest

from app.report_service import ReportService
from app.skill_bridge import SkillBridge
from app.sporttery_service import SportteryService


def make_skill(tmp_path: Path, *scripts: str) -> Path:
    skill_path = tmp_path / "skill"
    scripts_path = skill_path / "scripts"
    scripts_path.mkdir(parents=True)
    for script in scripts:
        (scripts_path / script).write_text("# test\n", encoding="utf-8")
    return skill_path


def test_parse_nums_accepts_spaces_and_commas(tmp_path: Path):
    service = SportteryService(SkillBridge(tmp_path / "missing"))

    assert service.parse_nums("086 087,088") == ["086", "087", "088"]


def test_build_fetch_odds_command_validates_nums(tmp_path: Path):
    skill_path = make_skill(tmp_path, "fetch_sporttery.py")
    service = SportteryService(SkillBridge(skill_path))

    command = service.build_fetch_odds_command(["086", "087"], out=tmp_path / "odds.json")

    assert command == [
        "python3",
        str(skill_path / "scripts" / "fetch_sporttery.py"),
        "odds",
        "--nums",
        "086",
        "087",
        "--out",
        str(tmp_path / "odds.json"),
    ]
    with pytest.raises(ValueError):
        service.build_fetch_odds_command(["86"])
    with pytest.raises(ValueError):
        service.build_fetch_odds_command(["08a"])


def test_fetch_odds_gracefully_handles_missing_script(tmp_path: Path):
    service = SportteryService(SkillBridge(tmp_path / "missing"))

    result = service.fetch_odds(["086"])

    assert result["ok"] is False
    assert result["error"]["code"] == "script_unavailable"


def test_fetch_odds_runs_subprocess_without_shell(monkeypatch, tmp_path: Path):
    skill_path = make_skill(tmp_path, "fetch_sporttery.py")
    service = SportteryService(SkillBridge(skill_path))
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return CompletedProcess(command, 0, stdout="done", stderr="")

    monkeypatch.setattr("app.sporttery_service.subprocess.run", fake_run)

    result = service.fetch_odds(["086"], timeout=7)

    assert result["ok"] is True
    assert result["returncode"] == 0
    assert result["stdout"] == "done"
    assert calls[0][1]["capture_output"] is True
    assert calls[0][1]["text"] is True
    assert calls[0][1]["timeout"] == 7
    assert "shell" not in calls[0][1]


def test_fetch_odds_handles_timeout(monkeypatch, tmp_path: Path):
    skill_path = make_skill(tmp_path, "fetch_sporttery.py")
    service = SportteryService(SkillBridge(skill_path))

    def fake_run(command, **kwargs):
        raise TimeoutExpired(command, timeout=3)

    monkeypatch.setattr("app.sporttery_service.subprocess.run", fake_run)

    result = service.fetch_odds(["086"], timeout=3)

    assert result["ok"] is False
    assert result["error"]["code"] == "timeout"


def test_build_report_command_and_theme_validation(tmp_path: Path):
    skill_path = make_skill(tmp_path, "gen_multi_market_report.py")
    service = ReportService(SkillBridge(skill_path))

    command = service.build_report_command(
        odds_path=tmp_path / "odds.json",
        out_path=tmp_path / "report.html",
        title="世界杯数据推演",
        theme="blue",
        intel_path=tmp_path / "intel.md",
    )

    assert command == [
        "python3",
        str(skill_path / "scripts" / "gen_multi_market_report.py"),
        "--odds",
        str(tmp_path / "odds.json"),
        "--out",
        str(tmp_path / "report.html"),
        "--title",
        "世界杯数据推演",
        "--theme",
        "blue",
        "--intel",
        str(tmp_path / "intel.md"),
    ]
    with pytest.raises(ValueError):
        service.build_report_command(tmp_path / "odds.json", tmp_path / "report.html", "x", "light")


def test_generate_report_file_gracefully_handles_missing_script(tmp_path: Path):
    service = ReportService(SkillBridge(tmp_path / "missing"))

    result = service.generate_report_file(tmp_path / "odds.json", tmp_path / "report.html", "title")

    assert result["ok"] is False
    assert result["error"]["code"] == "script_unavailable"
