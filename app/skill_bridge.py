from __future__ import annotations

from pathlib import Path

from app.config import get_settings


EXPECTED_SCRIPTS: tuple[str, ...] = (
    "fetch_sporttery.py",
    "gen_multi_market_report.py",
    "fuse_correct_score.py",
    "update_live_odds.py",
)


class SkillBridge:
    """Read-only boundary for the local Hermes worldcup skill."""

    def __init__(self, skill_path: str | Path | None = None):
        self.skill_path = Path(skill_path or get_settings().skill_path)
        self.scripts_path = self.skill_path / "scripts"
        self.data_path = self.skill_path / "data"

    def available(self) -> bool:
        return self.skill_path.exists() and self.skill_path.is_dir()

    def script_path(self, name: str) -> Path:
        return self.scripts_path / name

    def has_script(self, name: str) -> bool:
        script = self.script_path(name)
        return self.available() and script.exists() and script.is_file()

    def describe(self) -> dict:
        return {
            "skill_path": str(self.skill_path),
            "available": self.available(),
            "scripts": {name: self.has_script(name) for name in EXPECTED_SCRIPTS},
        }
