from __future__ import annotations

from dataclasses import dataclass


BANNED_TERMS: tuple[str, ...] = (
    "稳赚",
    "必中",
    "跟单",
    "荐号",
    "回本",
    "梭哈",
    "包中",
    "带单",
    "盈利承诺",
)


@dataclass(frozen=True)
class ComplianceResult:
    passed: bool
    status: str
    matches: list[str]
    message: str

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "status": self.status,
            "matches": self.matches,
            "message": self.message,
        }


def scan_text(text: str | None) -> dict:
    """Scan text for product-level banned terms without raising."""

    value = text or ""
    matches = [term for term in BANNED_TERMS if term in value]
    passed = not matches
    message = "合规通过" if passed else "命中禁词，请改写为概率推演与风险提示口径"
    return ComplianceResult(
        passed=passed,
        status="passed" if passed else "failed",
        matches=matches,
        message=message,
    ).as_dict()


def assert_compliant(text: str | None) -> dict:
    """Return a compliance status object; callers decide how to handle failure."""

    return scan_text(text)
