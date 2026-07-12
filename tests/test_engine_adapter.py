from pathlib import Path

from app.config import Settings
from app.engine_adapter import WorldCupEngineAdapter


def test_adapter_loads_demo_matches():
    adapter = WorldCupEngineAdapter(Settings())

    matches = adapter.list_matches()

    assert len(matches) >= 3
    assert matches[0]["source"] == "demo"
    assert {"id", "num", "home", "away", "kickoff", "stage", "venue"} <= set(matches[0])


def test_adapter_generates_deterministic_report():
    adapter = WorldCupEngineAdapter(Settings())

    first = adapter.generate_report("demo-001", theme="dark")
    second = adapter.generate_report("demo-001", theme="dark")

    assert first == second
    assert first["match"]["id"] == "demo-001"
    assert set(first["probabilities"]) == {"home", "draw", "away"}
    assert round(sum(first["probabilities"].values()), 2) == 1.0
    assert len(first["score_candidates"]) == 3
    assert first["compliance_status"]["passed"] is True
    assert first["engine"]["source"] == "demo"


def test_adapter_handles_missing_skill_path_gracefully(tmp_path: Path):
    settings = Settings(skill_path=tmp_path / "missing-skill")
    adapter = WorldCupEngineAdapter(settings)

    report = adapter.generate_report("demo-001", theme="light")

    assert report["engine"]["skill_available"] is False
    assert report["engine"]["source"] == "demo"
