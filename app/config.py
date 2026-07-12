from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from app.desktop_runtime import default_app_data_dir, initialize_user_data
from app.resources import ROOT_DIR, resource_path


DEFAULT_APP_NAME = "足球赛事 AI 推演引擎"
DEFAULT_DATA_PATH = resource_path("data", "demo_matches.json")
DEFAULT_RUNS_PATH = ROOT_DIR / "runs"
DEFAULT_SKILL_PATH = Path.home() / ".hermes" / "skills" / "leisure" / "worldcup2026-betting-analyst"
DEFAULT_MAX_RUN_MATCHES = 8
DEFAULT_MAX_CONCURRENT_RUNS = 1
DEFAULT_DEFAULT_COMMAND_TIMEOUT = 60
DEFAULT_DB_PATH = ROOT_DIR / "data" / "app.db"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PLAN = "internal"
DEFAULT_RUN_QUOTA = 1000
DEFAULT_CONFIG_PATH = ROOT_DIR / "config"
DEFAULT_LOGS_PATH = ROOT_DIR / "logs"
DEFAULT_API_KEY_STORAGE_MODE = "env"
DEFAULT_DESKTOP_API_KEY_STORAGE_MODE = "local_json"


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the local MVP."""

    app_name: str = DEFAULT_APP_NAME
    data_path: Path = DEFAULT_DATA_PATH
    runs_path: Path = DEFAULT_RUNS_PATH
    skill_path: Path = DEFAULT_SKILL_PATH
    max_run_matches: int = DEFAULT_MAX_RUN_MATCHES
    max_concurrent_runs: int = DEFAULT_MAX_CONCURRENT_RUNS
    default_command_timeout: int = DEFAULT_DEFAULT_COMMAND_TIMEOUT
    db_path: Path = DEFAULT_DB_PATH
    host: str = DEFAULT_HOST
    api_token: str = ""
    plan: str = DEFAULT_PLAN
    run_quota: int = DEFAULT_RUN_QUOTA
    desktop_mode: bool = False
    app_data_dir: Path | None = None
    config_path: Path = DEFAULT_CONFIG_PATH
    logs_path: Path = DEFAULT_LOGS_PATH
    api_key_storage_mode: str = DEFAULT_API_KEY_STORAGE_MODE


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    desktop_mode = _env_bool("WC_DESKTOP_MODE", False)
    app_data_dir = _env_path("WC_APP_DATA_DIR", default_app_data_dir()) if desktop_mode else _env_optional_path("WC_APP_DATA_DIR")
    desktop_defaults = initialize_user_data(app_data_dir) if desktop_mode else None

    return Settings(
        app_name=os.environ.get("WC_APP_NAME", DEFAULT_APP_NAME),
        data_path=_env_path("WC_DATA_PATH", DEFAULT_DATA_PATH),
        runs_path=_env_path("WC_RUNS_PATH", desktop_defaults.runs_path if desktop_defaults else DEFAULT_RUNS_PATH),
        skill_path=_env_path("WC_SKILL_PATH", DEFAULT_SKILL_PATH),
        max_run_matches=_env_int("WC_MAX_RUN_MATCHES", DEFAULT_MAX_RUN_MATCHES),
        max_concurrent_runs=_env_int("WC_MAX_CONCURRENT_RUNS", DEFAULT_MAX_CONCURRENT_RUNS),
        default_command_timeout=_env_int("WC_DEFAULT_COMMAND_TIMEOUT", DEFAULT_DEFAULT_COMMAND_TIMEOUT),
        db_path=_env_path("WC_DB_PATH", desktop_defaults.db_path if desktop_defaults else DEFAULT_DB_PATH),
        host=os.environ.get("WC_HOST", DEFAULT_HOST),
        api_token=os.environ.get("WC_API_TOKEN", ""),
        plan=os.environ.get("WC_PLAN", DEFAULT_PLAN),
        run_quota=_env_int("WC_RUN_QUOTA", DEFAULT_RUN_QUOTA),
        desktop_mode=desktop_mode,
        app_data_dir=desktop_defaults.app_data_dir if desktop_defaults else app_data_dir,
        config_path=_env_path("WC_CONFIG_PATH", desktop_defaults.config_path if desktop_defaults else DEFAULT_CONFIG_PATH),
        logs_path=_env_path("WC_LOGS_PATH", desktop_defaults.logs_path if desktop_defaults else DEFAULT_LOGS_PATH),
        api_key_storage_mode=os.environ.get(
            "WC_API_KEY_STORAGE_MODE",
            DEFAULT_DESKTOP_API_KEY_STORAGE_MODE if desktop_mode else DEFAULT_API_KEY_STORAGE_MODE,
        ),
    )


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    if not value:
        return default
    return Path(value).expanduser()


def _env_optional_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value).expanduser()


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
