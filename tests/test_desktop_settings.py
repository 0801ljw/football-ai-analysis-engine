import json
import os
import threading
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.desktop_settings import CONFIG_FILENAME, LocalJsonApiKeyStore
from app.main import app


client = TestClient(app)
RAW_KEY = "sk_test_desktop_secret_12345"


def _desktop_settings(tmp_path: Path, desktop_mode: bool = True) -> Settings:
    return Settings(
        desktop_mode=desktop_mode,
        app_data_dir=tmp_path,
        config_path=tmp_path / "config",
        db_path=tmp_path / "data" / "app.db",
        runs_path=tmp_path / "runs",
        logs_path=tmp_path / "logs",
        api_key_storage_mode="local_json",
    )


def _install_settings(monkeypatch, tmp_path: Path, desktop_mode: bool = True) -> Settings:
    settings = _desktop_settings(tmp_path, desktop_mode=desktop_mode)
    settings.config_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.main.settings", settings)
    monkeypatch.setattr("app.main._desktop_api_key_store", None)
    return settings


def _assert_safe_shape(payload: dict, configured: bool):
    assert payload["provider"] == "the_odds_api"
    assert payload["configured"] is configured
    assert payload["storage"] == "local user configuration"
    assert "api_key" not in payload
    assert "raw" not in payload
    assert RAW_KEY not in str(payload)
    assert set(payload) == {"provider", "configured", "masked", "updated_at", "storage"}


def test_desktop_api_keys_are_404_when_not_in_desktop_mode(monkeypatch, tmp_path):
    _install_settings(monkeypatch, tmp_path, desktop_mode=False)

    for method in (client.get, client.delete):
        response = method("/api/desktop/settings/api-keys/the_odds_api")
        assert response.status_code == 404
    response = client.put("/api/desktop/settings/api-keys/the_odds_api", json={"api_key": RAW_KEY})
    assert response.status_code == 404
    assert RAW_KEY not in response.text


def test_desktop_api_keys_are_404_when_not_in_desktop_mode_even_for_malformed_put_bodies(monkeypatch, tmp_path):
    _install_settings(monkeypatch, tmp_path, desktop_mode=False)

    malformed_bodies = [
        {},
        {"api_key": ""},
        {"api_key": 123},
        {"api_key": RAW_KEY, "extra": {"raw": RAW_KEY}},
        "not-an-object",
    ]
    for body in malformed_bodies:
        response = client.put("/api/desktop/settings/api-keys/the_odds_api", json=body)
        assert response.status_code == 404
        assert RAW_KEY not in response.text


def test_desktop_api_key_crud_never_returns_raw_key_and_persists(monkeypatch, tmp_path):
    settings = _install_settings(monkeypatch, tmp_path)

    missing = client.get("/api/desktop/settings/api-keys/the_odds_api")
    assert missing.status_code == 200
    missing_payload = missing.json()
    _assert_safe_shape(missing_payload, configured=False)
    assert missing_payload["masked"] is None
    assert missing_payload["updated_at"] is None

    put = client.put("/api/desktop/settings/api-keys/the_odds_api", json={"api_key": RAW_KEY})
    assert put.status_code == 200
    put_payload = put.json()
    _assert_safe_shape(put_payload, configured=True)
    assert put_payload["masked"] != RAW_KEY
    assert put_payload["masked"].startswith("sk_t")
    assert put_payload["masked"].endswith("2345")
    assert put_payload["updated_at"]
    assert RAW_KEY not in put.text

    config_file = settings.config_path / "desktop_api_keys.json"
    assert config_file.exists()
    assert RAW_KEY in config_file.read_text(encoding="utf-8")
    if os.name == "posix" and hasattr(config_file.stat(), "st_mode"):
        assert config_file.stat().st_mode & 0o777 == 0o600

    get = client.get("/api/desktop/settings/api-keys/the_odds_api")
    assert get.status_code == 200
    get_payload = get.json()
    _assert_safe_shape(get_payload, configured=True)
    assert get_payload["masked"] == put_payload["masked"]
    assert get_payload["updated_at"] == put_payload["updated_at"]
    assert RAW_KEY not in get.text

    delete = client.delete("/api/desktop/settings/api-keys/the_odds_api")
    assert delete.status_code == 200
    delete_payload = delete.json()
    _assert_safe_shape(delete_payload, configured=False)
    assert delete_payload["masked"] is None
    assert delete_payload["updated_at"] is None
    assert RAW_KEY not in delete.text

    after_delete = client.get("/api/desktop/settings/api-keys/the_odds_api")
    assert after_delete.status_code == 200
    _assert_safe_shape(after_delete.json(), configured=False)


def test_desktop_api_keys_reject_unknown_or_path_injection_provider(monkeypatch, tmp_path):
    _install_settings(monkeypatch, tmp_path)

    for provider in ("unknown", "%2E%2E/the_odds_api", "the_odds_api/evil"):
        response = client.get(f"/api/desktop/settings/api-keys/{provider}")
        assert response.status_code == 422
        assert RAW_KEY not in response.text


def test_desktop_api_key_validation_rejects_empty_non_string_and_too_long_without_echo(monkeypatch, tmp_path):
    _install_settings(monkeypatch, tmp_path)

    cases = [
        {"api_key": ""},
        {"api_key": "   "},
        {"api_key": 123},
        {"api_key": "x" * 4097},
    ]
    for body in cases:
        response = client.put("/api/desktop/settings/api-keys/the_odds_api", json=body)
        assert response.status_code == 422
        assert RAW_KEY not in response.text
        if isinstance(body["api_key"], str) and body["api_key"]:
            assert body["api_key"] not in response.text


def test_corrupt_existing_api_key_file_blocks_put_delete_without_overwrite(monkeypatch, tmp_path):
    settings = _install_settings(monkeypatch, tmp_path)
    config_file = settings.config_path / CONFIG_FILENAME
    original = '{"api_keys":{"the_odds_api":{"api_key":"sk_liv..._raw","updated_at":"old"}'
    config_file.write_text(original, encoding="utf-8")

    put = client.put("/api/desktop/settings/api-keys/the_odds_api", json={"api_key": RAW_KEY})
    assert put.status_code == 503
    assert put.json() == {"detail": "desktop api key settings are temporarily unavailable"}
    assert RAW_KEY not in put.text
    assert "sk_liv..._raw" not in put.text
    assert str(config_file) not in put.text
    assert config_file.read_text(encoding="utf-8") == original

    delete = client.delete("/api/desktop/settings/api-keys/the_odds_api")
    assert delete.status_code == 503
    assert delete.json() == {"detail": "desktop api key settings are temporarily unavailable"}
    assert "sk_liv..._raw" not in delete.text
    assert str(config_file) not in delete.text
    assert config_file.read_text(encoding="utf-8") == original


def test_api_key_store_concurrent_writes_use_unique_temps_and_preserve_valid_json(tmp_path, monkeypatch):
    store = LocalJsonApiKeyStore(tmp_path)
    temp_names: list[str] = []
    temp_names_lock = threading.Lock()
    real_replace = LocalJsonApiKeyStore._replace

    def recording_replace(self: LocalJsonApiKeyStore, temp_path: Path) -> None:
        with temp_names_lock:
            temp_names.append(temp_path.name)
        real_replace(self, temp_path)

    monkeypatch.setattr(LocalJsonApiKeyStore, "_replace", recording_replace)

    threads = [
        threading.Thread(target=store.put, args=("the_odds_api", f"sk_thread_{index:02d}"))
        for index in range(12)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()

    assert len(temp_names) == len(threads)
    assert len(set(temp_names)) == len(temp_names)
    assert not list(tmp_path.glob(f".{CONFIG_FILENAME}.*.tmp"))
    config_file = tmp_path / CONFIG_FILENAME
    if os.name == "posix":
        assert config_file.stat().st_mode & 0o777 == 0o600
    payload = json.loads(config_file.read_text(encoding="utf-8"))
    assert payload["api_keys"]["the_odds_api"]["api_key"].startswith("sk_thread_")
