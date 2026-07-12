from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MARKET_KEYS: dict[str, tuple[str, ...]] = {
    "has_spf": ("胜平负", "spf"),
    "has_handicap": ("让球", "handicap"),
    "has_total_goals": ("总进球", "total_goals"),
    "has_correct_score": ("比分波胆", "correct_score"),
    "has_half_full": ("半全场", "half_full"),
}


def load_odds_file(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_load_error": {"type": exc.__class__.__name__, "message": str(exc)}}
    if not isinstance(payload, dict):
        return {"_format_error": "odds 文件顶层必须是 JSON object"}
    return payload


def inspect_odds_payload(payload: dict) -> dict:
    base = _empty_health()
    if not isinstance(payload, dict):
        base["summary"] = "odds 数据格式不符合预期：顶层必须是 object。"
        return base

    load_error = payload.get("_load_error")
    if isinstance(load_error, dict):
        base["summary"] = f"odds 文件读取失败：{load_error.get('message') or load_error.get('type') or '未知错误'}。"
        return base

    format_error = payload.get("_format_error")
    if format_error:
        base["summary"] = f"odds 数据格式不符合预期：{format_error}。"
        return base

    matches = payload.get("matches")
    if not isinstance(matches, dict):
        base["summary"] = "odds 数据格式不符合预期：缺少 matches object。"
        return base

    valid_nums: list[str] = []
    invalid: dict[str, str] = {}
    markets: dict[str, dict[str, bool]] = {}

    for raw_num, match in matches.items():
        num = str(raw_num)
        if _is_valid_match(match):
            valid_nums.append(num)
            markets[num] = _inspect_markets(match)
        else:
            invalid[num] = _invalid_reason(match)

    valid_count = len(valid_nums)
    invalid_count = len(invalid)
    total = valid_count + invalid_count
    return {
        "ok": valid_count > 0,
        "total": total,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "valid_nums": valid_nums,
        "invalid": invalid,
        "markets": markets,
        "summary": _summary(total, valid_count, invalid_count),
    }


def filter_valid_odds_payload(payload: dict, valid_nums: list[str]) -> dict:
    if not isinstance(payload, dict):
        return {"matches": {}}
    matches = payload.get("matches")
    if not isinstance(matches, dict):
        return {**payload, "matches": {}}
    valid_set = set(valid_nums)
    return {**payload, "matches": {num: match for num, match in matches.items() if str(num) in valid_set}}


def _empty_health() -> dict:
    return {
        "ok": False,
        "total": 0,
        "valid_count": 0,
        "invalid_count": 0,
        "valid_nums": [],
        "invalid": {},
        "markets": {},
        "summary": "odds 数据格式不符合预期。",
    }


def _is_valid_match(match: Any) -> bool:
    return isinstance(match, dict) and "error" not in match and bool(match.get("主队")) and bool(match.get("客队"))


def _invalid_reason(match: Any) -> str:
    if isinstance(match, dict):
        error = match.get("error")
        if error:
            return str(error)
        missing = [key for key in ("主队", "客队") if not match.get(key)]
        if missing:
            return "缺少" + "/".join(missing)
    return "场次数据格式不符合预期"


def _inspect_markets(match: dict) -> dict[str, bool]:
    return {
        field: any(key in match for key in aliases)
        for field, aliases in MARKET_KEYS.items()
    }


def _summary(total: int, valid_count: int, invalid_count: int) -> str:
    if total == 0:
        return "未发现可检查的场次数据。"
    if valid_count == 0:
        return f"共 {total} 场，0 场有效，{invalid_count} 场不可用；没有可用于生成报告的有效场次。"
    if invalid_count:
        return f"共 {total} 场，{valid_count} 场有效，{invalid_count} 场不可用；将仅使用有效场次生成报告。"
    return f"共 {total} 场，{valid_count} 场有效，0 场不可用；可生成报告。"
