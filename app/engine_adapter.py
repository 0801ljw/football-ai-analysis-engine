from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.compliance import assert_compliant
from app.config import Settings, get_settings
from app.content_renderer import render_content_copy


class WorldCupEngineAdapter:
    """Adapter boundary for the current demo data and the future Hermes skill engine."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.data_path = Path(self.settings.data_path)
        self.skill_path = Path(self.settings.skill_path)

    def list_matches(self) -> list[dict]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload["matches"]

    def get_match(self, match_id: str) -> dict:
        for match in self.list_matches():
            if match["id"] == match_id:
                return match
        raise KeyError(f"Unknown match_id: {match_id}")

    def generate_report(self, match_id: str, theme: str = "light") -> dict:
        match = self.get_match(match_id)
        probabilities = self._probabilities(match_id)
        score_candidates = self._score_candidates(match_id)
        market_notes = self._market_notes(match, theme)
        risk_flags = self._risk_flags()
        content_copy = render_content_copy(
            match=match,
            probabilities=probabilities,
            score_candidates=score_candidates,
            market_notes=market_notes,
            risk_flags=risk_flags,
        )
        compliance_text = json.dumps(
            {
                "match": match,
                "probabilities": probabilities,
                "score_candidates": score_candidates,
                "market_notes": market_notes,
                "risk_flags": risk_flags,
                "content_copy": content_copy,
            },
            ensure_ascii=False,
        )

        return {
            "match": match,
            "probabilities": probabilities,
            "score_candidates": score_candidates,
            "market_notes": market_notes,
            "risk_flags": risk_flags,
            "content_copy": content_copy,
            "compliance_status": assert_compliant(compliance_text),
            "engine": {
                "source": "demo",
                "skill_path": str(self.skill_path),
                "skill_available": self.skill_path.exists(),
                "mode": "deterministic_fallback",
            },
        }

    @staticmethod
    def _seed(match_id: str) -> int:
        digest = hashlib.sha256(match_id.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)

    def _probabilities(self, match_id: str) -> dict[str, float]:
        seed = self._seed(match_id)
        home = 38 + (seed % 18)
        draw = 20 + ((seed >> 4) % 11)
        away = 100 - home - draw
        values = {"home": home / 100, "draw": draw / 100, "away": away / 100}
        total = sum(values.values())
        return {key: round(value / total, 4) for key, value in values.items()}

    def _score_candidates(self, match_id: str) -> list[dict]:
        seed = self._seed(match_id)
        pool = [
            ("1-1", "均衡区间，平局权重较高"),
            ("2-1", "主队小幅优势区间"),
            ("1-0", "低比分控制区间"),
            ("2-0", "主队效率偏高区间"),
            ("0-1", "客队反击效率区间"),
            ("2-2", "开放对攻区间"),
        ]
        start = seed % len(pool)
        rotated = pool[start:] + pool[:start]
        base = [0.142, 0.116, 0.094]
        return [
            {"score": score, "probability": probability, "note": note}
            for (score, note), probability in zip(rotated[:3], base, strict=True)
        ]

    @staticmethod
    def _market_notes(match: dict, theme: str) -> list[str]:
        style_note = "深色主题适合投放推演看板" if theme == "dark" else "浅色主题适合阅读型报告"
        return [
            f"{match['num']} 号场次仍使用 demo 数据，source=demo。",
            "当前没有接入实时赔率、首发、伤停与盘口变化，因此只展示研究型概率分布。",
            style_note,
            "真实引擎接入后，adapter 会把 Hermes skill 的概率、比分网格和风险层结果映射到同一报告结构。",
        ]

    @staticmethod
    def _risk_flags() -> list[str]:
        return [
            "demo 数据不代表真实赛况。",
            "缺少实时赔率、盘口更新时间、首发与伤停信息。",
            "概率结果只能用于娱乐研究和产品演示。",
            "报告必须保留风险提示，不输出确定性承诺。",
        ]
