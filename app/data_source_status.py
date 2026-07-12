from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import Settings
from app.skill_bridge import SkillBridge


COMPLIANCE_NOTICE = "独立数据研究工具，与任何赛事组织方无官方关联；不构成任何投注建议或收益承诺。"
PUBLIC_SOURCE_NAME = "public/sporttery explicit probe"
LOCAL_FALLBACK_SOURCE = "local/demo/offline"


class PublicProbeTracker:
    """Tiny in-memory, sanitized metadata store for explicit public data probes."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            return deepcopy(self._snapshot)

    def record_discover(self, ok: bool, nums: list[str], payload: dict[str, Any]) -> dict[str, Any]:
        now = _now_iso()
        valid_nums = payload.get("valid_nums") if isinstance(payload, dict) else []
        if not isinstance(valid_nums, list):
            valid_nums = []
        metadata: dict[str, Any] = {
            "available": bool(ok),
            "status": "success" if ok else "failed",
            "checked_at": now,
            "nums_checked": [str(num) for num in nums],
            "valid_count": len(valid_nums),
            "source": PUBLIC_SOURCE_NAME,
            "realtime": False,
            "network_implicit": False,
        }
        if not ok:
            error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(error, dict):
                metadata["error_code"] = _safe_scalar(error.get("code"), default="unknown")
                metadata["reason"] = _safe_error_reason(metadata["error_code"])
            else:
                metadata["error_code"] = "unknown"
                metadata["reason"] = "explicit public data probe failed"
        with self._lock:
            self._snapshot = metadata
        return deepcopy(metadata)


def build_desktop_data_status(
    *,
    settings: Settings,
    bridge: SkillBridge,
    key_status: dict[str, Any],
    public_probe: dict[str, Any] | None,
) -> dict[str, Any]:
    local_fallback = _local_fallback_status(settings.data_path)
    public_source = _public_source_status(public_probe)
    user_key = _safe_key_status(key_status)
    skill = _skill_status(bridge)

    degraded_reasons: list[str] = []
    if not local_fallback["available"]:
        degraded_reasons.append("local demo fallback unavailable")
    if not skill["available"]:
        degraded_reasons.append(f"Hermes skill unavailable: {skill['reason']}")
    if public_source["status"] != "success":
        degraded_reasons.append(public_source.get("reason") or "public source not checked")

    degraded = bool(degraded_reasons)
    return {
        "status": "degraded" if degraded else "ready",
        "updated_at": _now_iso(),
        "sources": {
            "local_fallback": local_fallback,
            "public_source": public_source,
            "user_key": user_key,
        },
        "degraded": degraded,
        "reason": "; ".join(degraded_reasons) if degraded else None,
        "compliance_notice": COMPLIANCE_NOTICE,
    }


def _local_fallback_status(data_path: Path) -> dict[str, Any]:
    path = Path(data_path)
    available = path.exists() and path.is_file()
    return {
        "available": available,
        "source": LOCAL_FALLBACK_SOURCE,
        "realtime": False,
        "reason": (
            "local demo fallback file exists; deterministic offline data only"
            if available
            else "local demo fallback file missing; offline demo data unavailable"
        ),
    }


def _public_source_status(public_probe: dict[str, Any] | None) -> dict[str, Any]:
    base = {
        "available": False,
        "source": PUBLIC_SOURCE_NAME,
        "status": "not_checked",
        "realtime": False,
        "network_implicit": False,
        "reason": "not_checked: no explicit successful discover/fetch metadata recorded in this process",
    }
    if not public_probe:
        return base
    safe = {key: value for key, value in public_probe.items() if key in {
        "available",
        "status",
        "checked_at",
        "nums_checked",
        "valid_count",
        "source",
        "realtime",
        "network_implicit",
        "error_code",
        "reason",
    }}
    safe.setdefault("source", PUBLIC_SOURCE_NAME)
    safe.setdefault("realtime", False)
    safe.setdefault("network_implicit", False)
    safe["available"] = bool(safe.get("available")) and safe.get("status") == "success"
    if safe.get("status") != "success":
        safe["available"] = False
        safe.setdefault("reason", "explicit public data probe failed or did not complete")
    return {**base, **safe}


def _safe_key_status(key_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": "the_odds_api",
        "configured": bool(key_status.get("configured")),
        "masked": key_status.get("masked") if key_status.get("configured") else None,
        "updated_at": key_status.get("updated_at") if key_status.get("configured") else None,
        "storage": key_status.get("storage") or "local user configuration",
    }


def _skill_status(bridge: SkillBridge) -> dict[str, Any]:
    available = bridge.available()
    if available:
        return {"available": True, "reason": "skill directory exists"}
    return {"available": False, "reason": "required local skill directory is not available"}


def _safe_error_reason(code: str) -> str:
    reasons = {
        "script_unavailable": "explicit public data probe failed: required fetch script unavailable",
        "timeout": "explicit public data probe failed: fetch timed out",
        "validation_error": "explicit public data probe failed: invalid match numbers",
        "execution_error": "explicit public data probe failed: fetch execution error",
        "discover_error": "explicit public data probe failed before health inspection",
    }
    return reasons.get(code, "explicit public data probe failed")


def _safe_scalar(value: Any, default: str = "") -> str:
    if isinstance(value, (str, int, float, bool)):
        text = str(value)
    else:
        text = default
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-:."
    sanitized = "".join(char for char in text if char in allowed)
    return sanitized[:80] or default


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
