from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.odds_health import MARKET_KEYS

SCHEMA_VERSION = "1.1"

_MATCH_MARKET_FIELDS = ("has_1x2", "has_handicap", "has_total_goals", "has_correct_score", "has_half_full")
_MARKET_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "has_1x2": MARKET_KEYS["has_spf"],
    "has_handicap": MARKET_KEYS["has_handicap"],
    "has_total_goals": MARKET_KEYS["has_total_goals"],
    "has_correct_score": MARKET_KEYS["has_correct_score"],
    "has_half_full": MARKET_KEYS["has_half_full"],
}
_MARKET_FIELD_LABELS: dict[str, str] = {
    "has_1x2": "胜平负",
    "has_handicap": "让球",
    "has_total_goals": "总进球",
    "has_correct_score": "比分波胆",
    "has_half_full": "半全场",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _match_markets(match: dict) -> dict[str, bool]:
    return {
        field: any(key in match for key in aliases)
        for field, aliases in _MARKET_FIELD_ALIASES.items()
    }


def _match_missing(markets: dict[str, bool]) -> list[str]:
    return [_MARKET_FIELD_LABELS[field] for field in _MATCH_MARKET_FIELDS if not markets.get(field)]


def _match_grade(markets: dict[str, bool]) -> str:
    signal_count = sum(1 for field in _MATCH_MARKET_FIELDS if markets.get(field))
    if signal_count >= 4:
        return "A"
    if signal_count >= 3:
        return "B"
    if signal_count >= 1:
        return "C"
    return "D"


def _aggregate_grade_status(valid_count: int, invalid_count: int, signal_count: int) -> tuple[str, str]:
    all_valid = valid_count > 0 and invalid_count == 0
    if valid_count == 0:
        return "D", "insufficient"
    if signal_count == 0:
        return "D", "insufficient"
    if all_valid and signal_count >= 4:
        return "A", "publishable"
    if all_valid and signal_count >= 3:
        return "B", "publishable"
    return "C", "internal_reference"


def build_prediction(
    run_id: str,
    valid_odds_payload: dict,
    odds_health: dict,
    odds_path: str,
    valid_odds_path: str,
    report_path: str,
) -> dict:
    """Build the deterministic prediction.json payload from odds health + valid odds.

    Does not fabricate a prediction when there are no valid matches (odds_health["ok"] is False);
    callers should check odds_health before calling this, but this function still returns a
    well-formed D-grade/insufficient artifact in that case rather than raising.
    """
    valid_count = int(odds_health.get("valid_count", 0))
    invalid_count = int(odds_health.get("invalid_count", 0))

    matches_payload = valid_odds_payload.get("matches")
    matches_payload = matches_payload if isinstance(matches_payload, dict) else {}

    matches: list[dict[str, Any]] = []
    aggregate_signal_counts = {field: 0 for field in _MATCH_MARKET_FIELDS}

    for raw_num, match in matches_payload.items():
        if not isinstance(match, dict):
            continue
        num = str(raw_num)
        markets = _match_markets(match)
        for field in _MATCH_MARKET_FIELDS:
            if markets.get(field):
                aggregate_signal_counts[field] += 1
        matches.append(
            {
                "num": num,
                "home": match.get("主队", ""),
                "away": match.get("客队", ""),
                "markets": markets,
                "data_quality": {
                    "grade": _match_grade(markets),
                    "missing": _match_missing(markets),
                },
            }
        )

    matches.sort(key=lambda item: item["num"])

    aggregate_signals = {
        field: aggregate_signal_counts[field] > 0 for field in _MATCH_MARKET_FIELDS
    }
    signal_count = sum(1 for present in aggregate_signals.values() if present)

    grade, status = _aggregate_grade_status(valid_count, invalid_count, signal_count)

    missing = [_MARKET_FIELD_LABELS[field] for field in _MATCH_MARKET_FIELDS if not aggregate_signals[field]]

    if valid_count == 0:
        summary = "没有有效场次，数据不足以生成可发布的推演结果。"
    elif invalid_count > 0:
        summary = f"共 {valid_count} 场有效、{invalid_count} 场不可用，市场信号 {signal_count}/5，仅作内部参考。"
    else:
        summary = f"共 {valid_count} 场全部有效，市场信号 {signal_count}/5，评级 {grade}。"

    source_type = "sporttery_official_api"
    source_label = "竞彩公开接口实时抓取"
    trust_level = {"A": "高", "B": "中高", "C": "中低", "D": "低"}[grade]
    limitations = []
    if missing:
        limitations.append("缺失盘口：" + "、".join(missing))
    if invalid_count > 0:
        limitations.append(f"{invalid_count} 场编号不可用，已剔除。")
    if status != "publishable":
        limitations.append("仅供内部参考，不建议直接发布。")
    if not limitations:
        limitations.append("仍需结合临场阵容、天气与盘口变化复核。")

    score = round((valid_count / max(valid_count + invalid_count, 1)) * 60 + (signal_count / 5) * 40)

    publish_blocked = status == "insufficient"
    warnings: list[str] = []
    if invalid_count > 0:
        warnings.append(f"{invalid_count} 场次数据不可用，已从推演结果中剔除。")
    if status == "internal_reference":
        warnings.append("数据质量未达到发布标准，仅供内部参考。")

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at": _now_iso(),
        "source": {
            "odds_path": odds_path,
            "valid_odds_path": valid_odds_path,
            "report_path": report_path,
            "source_type": source_type,
            "source_label": source_label,
            "captured_at": _now_iso(),
            "demo_fallback": False,
        },
        "data_quality": {
            "grade": grade,
            "status": status,
            "score": score,
            "summary": summary,
            "missing": missing,
            "signals": {
                "valid_match_count": valid_count,
                "invalid_match_count": invalid_count,
                "has_1x2": aggregate_signals["has_1x2"],
                "has_handicap": aggregate_signals["has_handicap"],
                "has_total_goals": aggregate_signals["has_total_goals"],
                "has_correct_score": aggregate_signals["has_correct_score"],
                "has_half_full": aggregate_signals["has_half_full"],
            },
        },
        "matches": matches,
        "data_trust": {
            "grade": grade,
            "trust_level": trust_level,
            "source_label": source_label,
            "summary": summary,
            "missing_markets": missing,
            "limitations": limitations,
            "plain_language": f"数据可信度{trust_level}：{summary}",
        },
        "compliance": {
            "positioning": "体育数据推演与娱乐研究，不构成下注建议",
            "publish_blocked": publish_blocked,
            "warnings": warnings,
        },
    }
