from pathlib import Path

from app.skill_bridge import SkillBridge


def test_skill_bridge_describes_expected_scripts(tmp_path: Path):
    skill_path = tmp_path / "skill"
    scripts_path = skill_path / "scripts"
    data_path = skill_path / "data"
    scripts_path.mkdir(parents=True)
    data_path.mkdir()
    (scripts_path / "fetch_sporttery.py").write_text("# test\n", encoding="utf-8")
    (scripts_path / "gen_multi_market_report.py").write_text("# test\n", encoding="utf-8")

    bridge = SkillBridge(skill_path)

    assert bridge.available() is True
    assert bridge.scripts_path == scripts_path
    assert bridge.data_path == data_path
    assert bridge.script_path("fetch_sporttery.py") == scripts_path / "fetch_sporttery.py"
    assert bridge.has_script("fetch_sporttery.py") is True
    description = bridge.describe()
    assert description["skill_path"] == str(skill_path)
    assert description["available"] is True
    assert description["scripts"]["fetch_sporttery.py"] is True
    assert description["scripts"]["gen_multi_market_report.py"] is True
    assert description["scripts"]["fuse_correct_score.py"] is False
    assert description["scripts"]["update_live_odds.py"] is False


def test_skill_bridge_missing_path_is_unavailable(tmp_path: Path):
    bridge = SkillBridge(tmp_path / "missing")

    assert bridge.available() is False
    assert bridge.has_script("fetch_sporttery.py") is False
    assert bridge.describe()["available"] is False
