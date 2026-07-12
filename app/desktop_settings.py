from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Protocol

from app.config import Settings


ALLOWED_API_KEY_PROVIDERS = frozenset({"the_odds_api"})
STORAGE_LABEL = "local user configuration"
CONFIG_FILENAME = "desktop_api_keys.json"


class ApiKeyStoreUnavailable(RuntimeError):
    """Raised when existing desktop API key storage cannot be safely read."""


class ApiKeyStore(Protocol):
    def get(self, provider: str) -> dict:
        ...

    def put(self, provider: str, api_key: str) -> dict:
        ...

    def delete(self, provider: str) -> dict:
        ...


class LocalJsonApiKeyStore:
    """Minimal replaceable local JSON storage for desktop API keys."""

    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.path = self.config_dir / CONFIG_FILENAME
        self._lock = threading.RLock()

    def get(self, provider: str) -> dict:
        with self._lock:
            data = self._read()
        entry = data.get("api_keys", {}).get(provider)
        if not entry:
            return api_key_status(provider, None, None)
        api_key = entry.get("api_key") if isinstance(entry, dict) else None
        updated_at = entry.get("updated_at") if isinstance(entry, dict) else None
        return api_key_status(provider, api_key if isinstance(api_key, str) else None, updated_at)

    def put(self, provider: str, api_key: str) -> dict:
        with self._lock:
            data = self._read()
            api_keys = data.setdefault("api_keys", {})
            updated_at = datetime.now(timezone.utc).isoformat()
            api_keys[provider] = {"api_key": api_key, "updated_at": updated_at}
            self._write(data)
        return api_key_status(provider, api_key, updated_at)

    def delete(self, provider: str) -> dict:
        with self._lock:
            data = self._read()
            api_keys = data.setdefault("api_keys", {})
            api_keys.pop(provider, None)
            self._write(data)
        return api_key_status(provider, None, None)

    def _read(self) -> dict:
        try:
            with self.path.open("r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
        except FileNotFoundError:
            return {"api_keys": {}}
        except (OSError, json.JSONDecodeError) as exc:
            raise ApiKeyStoreUnavailable("desktop api key settings are temporarily unavailable") from exc
        return data if isinstance(data, dict) else {"api_keys": {}}

    def _write(self, data: dict) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.{os.getpid()}.",
            suffix=".tmp",
            dir=self.config_dir,
            text=True,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file_obj:
                file_obj.write(payload)
                file_obj.write("\n")
            _chmod_0600(temp_path)
            self._replace(temp_path)
        except Exception:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _replace(self, temp_path: Path) -> None:
        os.replace(temp_path, self.path)
        _chmod_0600(self.path)


def validate_provider(provider: str) -> str:
    if provider not in ALLOWED_API_KEY_PROVIDERS:
        raise ValueError("unsupported api key provider")
    return provider


def build_api_key_store(settings: Settings) -> ApiKeyStore:
    return LocalJsonApiKeyStore(settings.config_path)


def api_key_status(provider: str, api_key: str | None, updated_at: str | None) -> dict:
    configured = bool(api_key)
    return {
        "provider": provider,
        "configured": configured,
        "masked": mask_api_key(api_key) if configured else None,
        "updated_at": updated_at if configured else None,
        "storage": STORAGE_LABEL,
    }


def mask_api_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "•" * len(api_key)
    return f"{api_key[:4]}{'•' * 8}{api_key[-4:]}"


def _chmod_0600(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass
