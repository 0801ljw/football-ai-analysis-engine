from pathlib import Path

from app.config import DEFAULT_APP_NAME, get_settings


def test_get_settings_reads_env_overrides_and_expands_paths(monkeypatch, tmp_path):
    get_settings.cache_clear()
    monkeypatch.setenv("WC_APP_NAME", "Test App")
    monkeypatch.setenv("WC_DATA_PATH", str(tmp_path / "data.json"))
    monkeypatch.setenv("WC_RUNS_PATH", "~/wc-runs")
    monkeypatch.setenv("WC_SKILL_PATH", "~/wc-skill")
    monkeypatch.setenv("WC_MAX_RUN_MATCHES", "3")
    monkeypatch.setenv("WC_MAX_CONCURRENT_RUNS", "2")
    monkeypatch.setenv("WC_DEFAULT_COMMAND_TIMEOUT", "17")

    settings = get_settings()

    assert settings.app_name == "Test App"
    assert settings.data_path == tmp_path / "data.json"
    assert settings.runs_path == Path("~/wc-runs").expanduser()
    assert settings.skill_path == Path("~/wc-skill").expanduser()
    assert settings.max_run_matches == 3
    assert settings.max_concurrent_runs == 2
    assert settings.default_command_timeout == 17

    get_settings.cache_clear()


def test_get_settings_invalid_int_env_falls_back(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("WC_MAX_RUN_MATCHES", "not-an-int")
    monkeypatch.setenv("WC_MAX_CONCURRENT_RUNS", "")
    monkeypatch.setenv("WC_DEFAULT_COMMAND_TIMEOUT", "bad")

    settings = get_settings()

    assert settings.max_run_matches == 8
    assert settings.max_concurrent_runs == 1
    assert settings.default_command_timeout == 60

    get_settings.cache_clear()


def test_default_app_display_name_is_desktop_product_name(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("WC_APP_NAME", raising=False)

    settings = get_settings()

    assert DEFAULT_APP_NAME == "足球赛事 AI 推演引擎"
    assert settings.app_name == "足球赛事 AI 推演引擎"

    get_settings.cache_clear()


def test_desktop_mode_routes_paths_to_app_data_dir(monkeypatch, tmp_path):
    get_settings.cache_clear()
    app_data_dir = tmp_path / "desktop-data"
    monkeypatch.setenv("WC_DESKTOP_MODE", "1")
    monkeypatch.setenv("WC_APP_DATA_DIR", str(app_data_dir))
    for name in ("WC_DB_PATH", "WC_RUNS_PATH", "WC_CONFIG_PATH", "WC_LOGS_PATH"):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()

    assert settings.desktop_mode is True
    assert settings.app_data_dir == app_data_dir
    assert settings.db_path == app_data_dir / "data" / "app.db"
    assert settings.runs_path == app_data_dir / "runs"
    assert settings.config_path == app_data_dir / "config"
    assert settings.logs_path == app_data_dir / "logs"
    assert settings.api_key_storage_mode == "local_json"

    get_settings.cache_clear()


def test_desktop_mode_preserves_explicit_path_overrides(monkeypatch, tmp_path):
    get_settings.cache_clear()
    app_data_dir = tmp_path / "desktop-data"
    db_path = tmp_path / "explicit" / "app.db"
    runs_path = tmp_path / "explicit-runs"
    config_path = tmp_path / "explicit-config"
    logs_path = tmp_path / "explicit-logs"
    monkeypatch.setenv("WC_DESKTOP_MODE", "1")
    monkeypatch.setenv("WC_APP_DATA_DIR", str(app_data_dir))
    monkeypatch.setenv("WC_DB_PATH", str(db_path))
    monkeypatch.setenv("WC_RUNS_PATH", str(runs_path))
    monkeypatch.setenv("WC_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("WC_LOGS_PATH", str(logs_path))
    monkeypatch.setenv("WC_API_KEY_STORAGE_MODE", "env")

    settings = get_settings()

    assert settings.db_path == db_path
    assert settings.runs_path == runs_path
    assert settings.config_path == config_path
    assert settings.logs_path == logs_path
    assert settings.api_key_storage_mode == "env"

    get_settings.cache_clear()
