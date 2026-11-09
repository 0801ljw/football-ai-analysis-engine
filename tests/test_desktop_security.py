from dataclasses import replace
import json

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.config import Settings
from app.desktop_settings import SystemApiKeyStore, LocalJsonApiKeyStore, ApiKeyStoreUnavailable

NATIVE_BACKEND = SystemApiKeyStore._native_backend

TOKEN = "a" * 64
KEY = "test-key-not-real-1234567890"


@pytest.fixture
def desktop(monkeypatch, tmp_path):
    settings = Settings(desktop_mode=True, desktop_session_token=TOKEN, config_path=tmp_path,
                        db_path=tmp_path / "app.db", runs_path=tmp_path / "runs")
    monkeypatch.setattr(main, "settings", settings)
    monkeypatch.setattr(main, "_auth_manager", None)
    monkeypatch.setattr(main, "_desktop_api_key_store", None)
    return TestClient(main.app, base_url="http://127.0.0.1:8765"), settings


def test_every_non_shell_route_requires_session_before_validation_or_side_effects(desktop):
    client, _ = desktop
    checked = 0
    for route in main.app.routes:
        path = getattr(route, "path", "")
        if not path or path in {"/", "/static"}:
            continue
        path = path.replace("{provider:path}", "the_odds_api").replace("{provider}", "the_odds_api")
        path = path.replace("{run_id}", "fake").replace("{match_id}", "fake").replace("{user_id}", "fake")
        for method in getattr(route, "methods", []):
            for token in [None, "wrong"]:
                response = client.request(method, path, headers={"X-Desktop-Session": token} if token else {})
                assert response.status_code == 401, (method, path, response.status_code)
            checked += 1
    assert checked > 35


@pytest.mark.parametrize("headers", [
    {"Host": "evil.example:8765"}, {"Host": "localhost:8765"},
    {"Host": "127.0.0.1:8765@evil.example"}, {"Host": "127.0.0.1:bad"},
    {"Origin": "https://evil.example"}, {"Origin": "null"},
    {"Origin": "http://127.0.0.1:9999"}, {"Sec-Fetch-Site": "cross-site"},
])
def test_bad_host_origin_rejected_even_with_valid_token(desktop, headers):
    client, _ = desktop
    response = client.get("/api/matches", headers={"X-Desktop-Session": TOKEN, **headers})
    assert response.status_code == 403
    assert TOKEN not in response.text


def test_legitimate_session_restart_and_missing_bootstrap(desktop, monkeypatch):
    client, settings = desktop
    for origin in [None, "http://127.0.0.1:8765"]:
        headers = {"X-Desktop-Session": TOKEN}
        if origin: headers["Origin"] = origin
        response = client.get("/api/matches", headers=headers)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
    monkeypatch.setattr(main, "settings", replace(settings, desktop_session_token="b" * 64))
    assert client.get("/api/matches", headers={"X-Desktop-Session": TOKEN}).status_code == 401
    monkeypatch.setattr(main, "settings", replace(settings, desktop_session_token=""))
    assert client.get("/").status_code == 503
    assert TOKEN not in repr(settings)


def test_public_shell_contains_only_bundled_demo_no_custom_paths_or_session(desktop, monkeypatch, tmp_path):
    client, settings = desktop
    private = tmp_path / "private.json"
    private.write_text('{"matches": [{"id": "private-fixture"}]}')
    monkeypatch.setattr(main, "settings", replace(settings, data_path=private))
    response = client.get("/")
    assert response.status_code == 200
    for value in [TOKEN, "private-fixture", str(tmp_path)]:
        assert value not in response.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/api/matches", headers={"X-Desktop-Session": TOKEN}).json()["matches"][0]["id"] == "private-fixture"


def test_migration_keeps_old_copy_until_explicit_verified_cleanup(desktop, tmp_path):
    client, _ = desktop
    legacy = LocalJsonApiKeyStore(tmp_path)
    legacy.put("the_odds_api", KEY)
    old = legacy.path.read_bytes()
    headers = {"X-Desktop-Session": TOKEN}
    response = client.post("/api/desktop/settings/key-migration/the_odds_api", headers=headers)
    assert response.status_code == 200
    assert response.json()["legacy_cleanup_available"] is True
    assert legacy.path.read_bytes() == old
    assert KEY not in response.text
    path = "/api/desktop/settings/key-cleanup/the_odds_api"
    assert client.post(path, headers=headers).status_code == 409
    assert legacy.path.read_bytes() == old
    assert client.post(path, headers={**headers, "X-Confirm-Legacy-Cleanup": "delete-verified-legacy-copy"}).status_code == 200
    assert KEY not in legacy.path.read_text()
    assert client.get("/api/desktop/settings/api-keys/the_odds_api", headers=headers).json()["configured"] is True


def test_failed_migration_keeps_data_and_retry_is_safe(tmp_path, memory_keyring, monkeypatch):
    legacy = LocalJsonApiKeyStore(tmp_path)
    legacy.put("the_odds_api", KEY)
    old = legacy.path.read_bytes()
    store = SystemApiKeyStore(tmp_path)
    real = memory_keyring.get_password
    def denied(*args): raise RuntimeError(KEY)
    monkeypatch.setattr(memory_keyring, "get_password", denied)
    with pytest.raises(ApiKeyStoreUnavailable) as error:
        store.migrate_legacy("the_odds_api")
    assert KEY not in str(error.value)
    assert legacy.path.read_bytes() == old
    monkeypatch.setattr(memory_keyring, "get_password", real)
    assert store.migrate_legacy("the_odds_api")["configured"]
    assert store.migrate_legacy("the_odds_api")["configured"]
    assert legacy.path.read_bytes() == old


@pytest.mark.parametrize("raw", ["not json", "[]", '{"api_keys": []}', '{"api_keys": {"the_odds_api": "bad"}}'])
def test_bad_legacy_data_never_overwritten(tmp_path, raw):
    legacy = LocalJsonApiKeyStore(tmp_path)
    legacy.path.write_text(raw)
    store = SystemApiKeyStore(tmp_path)
    for action in [lambda: store.put("the_odds_api", KEY), lambda: store.migrate_legacy("the_odds_api"), lambda: store.cleanup_legacy("the_odds_api")]:
        with pytest.raises(ApiKeyStoreUnavailable): action()
        assert legacy.path.read_text() == raw


def test_failed_readback_and_conflict_never_cleanup(tmp_path, memory_keyring, monkeypatch):
    legacy = LocalJsonApiKeyStore(tmp_path)
    legacy.put("the_odds_api", KEY)
    old = legacy.path.read_bytes()
    store = SystemApiKeyStore(tmp_path)
    monkeypatch.setattr(memory_keyring, "set_password", lambda *args: None)
    with pytest.raises(ApiKeyStoreUnavailable): store.migrate_legacy("the_odds_api")
    with pytest.raises(ApiKeyStoreUnavailable): store.cleanup_legacy("the_odds_api")
    memory_keyring.values[store.service, "the_odds_api"] = json.dumps({"api_key": "different"})
    with pytest.raises(ApiKeyStoreUnavailable): store.migrate_legacy("the_odds_api")
    assert legacy.path.read_bytes() == old


def test_cleanup_write_failure_keeps_old_copy_and_retry(tmp_path, monkeypatch):
    legacy = LocalJsonApiKeyStore(tmp_path)
    legacy.put("the_odds_api", KEY)
    old = legacy.path.read_bytes()
    store = SystemApiKeyStore(tmp_path)
    store.migrate_legacy("the_odds_api")
    original = store.legacy._replace
    def denied(*args): raise OSError("simulated permission denial")
    monkeypatch.setattr(store.legacy, "_replace", denied)
    with pytest.raises(ApiKeyStoreUnavailable): store.cleanup_legacy("the_odds_api")
    assert legacy.path.read_bytes() == old
    assert not list(tmp_path.glob(".*.tmp"))
    monkeypatch.setattr(store.legacy, "_replace", original)
    assert not store.cleanup_legacy("the_odds_api")["legacy_present"]


def test_native_write_denied_does_not_create_plaintext_fallback(tmp_path, memory_keyring, monkeypatch):
    def denied(*args): raise PermissionError(KEY)
    monkeypatch.setattr(memory_keyring, "set_password", denied)
    store = SystemApiKeyStore(tmp_path)
    with pytest.raises(ApiKeyStoreUnavailable) as error: store.put("the_odds_api", KEY)
    assert KEY not in str(error.value)
    assert not list(tmp_path.iterdir())



def test_unsupported_platform_fails_closed_without_keyring_autoselection(tmp_path, monkeypatch):
    import keyring
    import app.desktop_settings as module
    monkeypatch.setattr(module.sys, "platform", "linux")
    def forbidden(): raise AssertionError("must not auto-select fallback backend")
    monkeypatch.setattr(keyring, "get_keyring", forbidden)
    with pytest.raises(ApiKeyStoreUnavailable): NATIVE_BACKEND(SystemApiKeyStore(tmp_path))
    assert not list(tmp_path.iterdir())
