from pathlib import Path
import tempfile

from fastapi.testclient import TestClient

from app.config import Settings
from app.data_source_status import (
    COMPLIANCE_NOTICE,
    PublicProbeTracker,
    build_desktop_data_status,
)
from app.desktop_settings import LocalJsonApiKeyStore
from app.main import app
from app.skill_bridge import SkillBridge


client = TestClient(app)
RAW_KEY = "sk_live_secret_1234567890"


def _settings(tmp_path: Path, desktop_mode: bool = True, skill_path: Path | None = None) -> Settings:
    return Settings(
        data_path=tmp_path / "data" / "demo_matches.json",
        skill_path=skill_path if skill_path is not None else tmp_path / "missing-skill",
        desktop_mode=desktop_mode,
        app_data_dir=tmp_path,
        config_path=tmp_path / "config",
        db_path=tmp_path / "data" / "app.db",
        runs_path=tmp_path / "runs",
        logs_path=tmp_path / "logs",
        api_key_storage_mode="local_json",
    )


def _write_demo(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"matches":[{"id":"demo-001","num":"086","source":"demo"}]}', encoding="utf-8")


def _install_settings(monkeypatch, tmp_path: Path, desktop_mode: bool = True, skill_path: Path | None = None) -> Settings:
    settings = _settings(tmp_path, desktop_mode=desktop_mode, skill_path=skill_path)
    settings.config_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.main.settings", settings)
    monkeypatch.setattr("app.main._desktop_api_key_store", None)
    monkeypatch.setattr("app.main._public_probe_tracker", PublicProbeTracker())
    return settings


def test_build_status_is_honest_when_only_demo_exists_and_no_probe_or_key(tmp_path):
    settings = _settings(tmp_path)
    _write_demo(settings.data_path)
    bridge = SkillBridge(settings.skill_path)
    key_store = LocalJsonApiKeyStore(settings.config_path)

    status = build_desktop_data_status(
        settings=settings,
        bridge=bridge,
        key_status=key_store.get("the_odds_api"),
        public_probe=None,
    )

    assert status["status"] == "degraded"
    assert status["degraded"] is True
    assert "Hermes skill unavailable" in status["reason"]
    assert status["compliance_notice"] == COMPLIANCE_NOTICE
    assert status["sources"]["local_fallback"] == {
        "available": True,
        "source": "local/demo/offline",
        "realtime": False,
        "reason": "local demo fallback file exists; deterministic offline data only",
    }
    assert "path" not in status["sources"]["local_fallback"]
    assert status["sources"]["public_source"]["available"] is False
    assert status["sources"]["public_source"]["status"] == "not_checked"
    assert status["sources"]["public_source"]["realtime"] is False
    assert status["sources"]["public_source"]["network_implicit"] is False
    assert status["sources"]["user_key"]["configured"] is False
    assert RAW_KEY not in str(status)


def test_local_fallback_unavailable_when_demo_file_missing_even_if_skill_exists(tmp_path):
    skill_path = tmp_path / "skill"
    (skill_path / "scripts").mkdir(parents=True)
    (skill_path / "scripts" / "fetch_sporttery.py").write_text("# placeholder", encoding="utf-8")
    settings = _settings(tmp_path, skill_path=skill_path)
    key_store = LocalJsonApiKeyStore(settings.config_path)

    status = build_desktop_data_status(
        settings=settings,
        bridge=SkillBridge(settings.skill_path),
        key_status=key_store.get("the_odds_api"),
        public_probe=None,
    )

    assert status["degraded"] is True
    assert "local demo fallback unavailable" in status["reason"]
    assert status["sources"]["local_fallback"]["available"] is False
    assert status["sources"]["local_fallback"]["source"] == "local/demo/offline"
    assert status["sources"]["local_fallback"]["realtime"] is False


def test_public_probe_tracker_sanitizes_success_and_failure_metadata():
    tracker = PublicProbeTracker()
    assert tracker.snapshot() is None

    tracker.record_discover(
        ok=True,
        nums=["086", "091"],
        payload={
            "ok": True,
            "valid_nums": ["091"],
            "summary": "ok api_key=SHOULD_NOT_LEAK",
            "fetch": {
                "ok": True,
                "returncode": 0,
                "stdout": "raw secret",
                "stderr": "raw secret",
                "command": ["python", "fetch", "--api-key", RAW_KEY],
            },
        },
    )
    success = tracker.snapshot()
    assert success["status"] == "success"
    assert success["available"] is True
    assert success["nums_checked"] == ["086", "091"]
    assert success["valid_count"] == 1
    assert "fetch" not in success
    assert "stdout" not in str(success)
    assert RAW_KEY not in str(success)
    assert "SHOULD_NOT_LEAK" not in str(success)

    tracker.record_discover(
        ok=False,
        nums=["086"],
        payload={"error": {"code": "script_unavailable", "message": f"missing {RAW_KEY}"}},
    )
    failure = tracker.snapshot()
    assert failure["status"] == "failed"
    assert failure["available"] is False
    assert failure["error_code"] == "script_unavailable"
    assert RAW_KEY not in str(failure)


def test_data_status_endpoint_404_when_not_desktop(monkeypatch, tmp_path):
    _install_settings(monkeypatch, tmp_path, desktop_mode=False)

    response = client.get("/api/desktop/data-status")

    assert response.status_code == 404


def test_data_status_endpoint_returns_safe_desktop_shape_with_key_and_probe(monkeypatch, tmp_path):
    home_skill_path = Path.home() / "missing-secret-skill"
    settings = _install_settings(monkeypatch, tmp_path, skill_path=home_skill_path)
    _write_demo(settings.data_path)
    key_store = LocalJsonApiKeyStore(settings.config_path)
    key_store.put("the_odds_api", RAW_KEY)
    tracker = PublicProbeTracker()
    tracker.record_discover(ok=True, nums=["086"], payload={"ok": True, "valid_nums": ["086"], "summary": f"secret {RAW_KEY}"})
    monkeypatch.setattr("app.main._public_probe_tracker", tracker)

    response = client.get("/api/desktop/data-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["compliance_notice"] == COMPLIANCE_NOTICE
    assert payload["updated_at"]
    assert payload["sources"]["public_source"]["status"] == "success"
    assert payload["sources"]["public_source"]["available"] is True
    assert payload["sources"]["user_key"]["configured"] is True
    assert payload["sources"]["user_key"]["masked"] != RAW_KEY
    assert "api_key" not in payload["sources"]["user_key"]
    assert RAW_KEY not in response.text
    assert str(settings.data_path) not in response.text
    assert str(tmp_path) not in response.text
    assert tempfile.gettempdir() not in response.text
    assert str(Path.home()) not in response.text
    assert str(home_skill_path) not in response.text
    assert "missing-secret-skill" not in response.text


def test_discover_hook_records_only_sanitized_probe_in_desktop_mode(monkeypatch, tmp_path):
    settings = _install_settings(monkeypatch, tmp_path)
    _write_demo(settings.data_path)

    def fake_fetch(self, nums, out=None, timeout=30):
        assert out is not None
        out.write_text('{"matches":{"086":{"主队":"巴西","客队":"德国","胜平负":{}}}}', encoding="utf-8")
        return {"ok": True, "command": ["fetch", RAW_KEY], "stdout": RAW_KEY, "stderr": RAW_KEY}

    monkeypatch.setattr("app.main.SportteryService.fetch_odds", fake_fetch)

    discover = client.post("/api/odds/discover", json={"nums": "086"})
    assert discover.status_code == 200
    assert RAW_KEY not in discover.text
    assert "command" not in discover.json()["fetch"]
    assert "stdout" not in discover.json()["fetch"]
    assert "stderr" not in discover.json()["fetch"]

    status = client.get("/api/desktop/data-status")
    assert status.status_code == 200
    assert status.json()["sources"]["public_source"]["status"] == "success"
    assert RAW_KEY not in status.text
