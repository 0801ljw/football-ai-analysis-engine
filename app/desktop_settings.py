from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import sys
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

    def migrate_legacy(self, provider: str) -> dict:
        ...

    def cleanup_legacy(self, provider: str) -> dict:
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
        if not isinstance(data, dict):
            raise ApiKeyStoreUnavailable("desktop api key settings are temporarily unavailable")
        return data

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
    return SystemApiKeyStore(settings.config_path)


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


class SystemApiKeyStore:
    """Only native macOS/Windows backends; no auto-selected plaintext fallback."""

    def __init__(self, config_dir: Path, backend=None):
        self.legacy = LocalJsonApiKeyStore(config_dir)
        scope = hashlib.sha256(str(Path(config_dir).resolve()).encode()).hexdigest()[:24]
        self.service = f"com.pitchmind.desktop.api-keys.{scope}"
        self._backend = backend
        self._lock = threading.RLock()

    def _native_backend(self):
        if self._backend is None:
            try:
                if sys.platform == "darwin":
                    from keyring.backends.macOS import Keyring
                elif sys.platform == "win32":
                    from keyring.backends.Windows import WinVaultKeyring as Keyring
                else:
                    raise ApiKeyStoreUnavailable("system credential storage unavailable")
                self._backend = Keyring()
            except Exception:
                raise ApiKeyStoreUnavailable("system credential storage unavailable") from None
        return self._backend

    def _entry(self, provider):
        try:
            raw = self._native_backend().get_password(self.service, validate_provider(provider))
            if raw is None:
                return None
            entry = json.loads(raw)
            if not isinstance(entry, dict) or not isinstance(entry.get("api_key"), str) or not entry["api_key"]:
                raise ValueError("invalid credential")
            return entry
        except Exception:
            raise ApiKeyStoreUnavailable("system credential storage unavailable") from None

    def _legacy_entry(self, provider):
        data = self.legacy._read()
        if not isinstance(data.get("api_keys", {}), dict):
            raise ApiKeyStoreUnavailable("legacy credential storage unavailable")
        entry = data.get("api_keys", {}).get(provider)
        if entry is not None and (not isinstance(entry, dict) or not isinstance(entry.get("api_key"), str) or not entry["api_key"]):
            raise ApiKeyStoreUnavailable("legacy credential storage unavailable")
        return entry

    def get(self, provider):
        with self._lock:
            entry = self._entry(provider)
            legacy = self._legacy_entry(provider)
            status = api_key_status(provider, entry["api_key"] if entry else None, entry.get("updated_at") if entry else None)
            status.update(storage="OS credential store", legacy_present=legacy is not None,
                          legacy_cleanup_available=bool(legacy and entry and legacy["api_key"] == entry["api_key"]))
            return status

    def put(self, provider, api_key):
        with self._lock:
            legacy = self._legacy_entry(provider)
            if legacy and legacy["api_key"] != api_key:
                raise ApiKeyStoreUnavailable("migrate existing legacy credential first")
            entry = {"api_key": api_key, "updated_at": datetime.now(timezone.utc).isoformat()}
            try:
                self._native_backend().set_password(self.service, validate_provider(provider), json.dumps(entry))
                if self._entry(provider) != entry:
                    raise ValueError("credential verification failed")
            except Exception:
                raise ApiKeyStoreUnavailable("system credential storage unavailable") from None
            return self.get(provider)

    def delete(self, provider):
        with self._lock:
            if self._legacy_entry(provider):
                raise ApiKeyStoreUnavailable("migrate and explicitly clean legacy credential first")
            try:
                if self._entry(provider):
                    self._native_backend().delete_password(self.service, validate_provider(provider))
                if self._entry(provider) is not None:
                    raise ValueError("credential deletion verification failed")
            except Exception:
                raise ApiKeyStoreUnavailable("system credential storage unavailable") from None
            return self.get(provider)

    def migrate_legacy(self, provider):
        with self._lock:
            legacy = self._legacy_entry(provider)
            if not legacy:
                return self.get(provider)
            entry = self._entry(provider)
            if entry and entry["api_key"] != legacy["api_key"]:
                raise ApiKeyStoreUnavailable("conflicting credentials require manual resolution")
            return self.put(provider, legacy["api_key"])

    def cleanup_legacy(self, provider):
        # Called only after explicit user confirmation, never during startup/get/migration.
        with self._lock:
            legacy, entry = self._legacy_entry(provider), self._entry(provider)
            if legacy and (not entry or legacy["api_key"] != entry["api_key"]):
                raise ApiKeyStoreUnavailable("legacy credential not verified in system storage")
            if legacy:
                try:
                    self.legacy.delete(provider)
                except OSError:
                    raise ApiKeyStoreUnavailable("legacy credential cleanup unavailable") from None
            return self.get(provider)
