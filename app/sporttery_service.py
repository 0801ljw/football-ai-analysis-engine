from __future__ import annotations

import re
import subprocess
from pathlib import Path
from subprocess import TimeoutExpired

from app.skill_bridge import SkillBridge


NUM_PATTERN = re.compile(r"^\d{3}$")
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)=\S+"),
)


class SportteryService:
    def __init__(self, bridge: SkillBridge | None = None):
        self.bridge = bridge or SkillBridge()

    def parse_nums(self, raw: str) -> list[str]:
        return [part for part in re.split(r"[\s,]+", raw.strip()) if part]

    def build_fetch_odds_command(self, nums: list[str], out: Path | None = None) -> list[str]:
        self._validate_nums(nums)
        command = [
            "python3",
            str(self.bridge.script_path("fetch_sporttery.py")),
            "odds",
            "--nums",
            *nums,
        ]
        if out is not None:
            command.extend(["--out", str(out)])
        return command

    def fetch_odds(self, nums: list[str], out: Path | None = None, timeout: int = 30) -> dict:
        try:
            command = self.build_fetch_odds_command(nums, out)
        except ValueError as exc:
            return self._failed("validation_error", str(exc))

        if not self.bridge.has_script("fetch_sporttery.py"):
            return self._failed("script_unavailable", "fetch_sporttery.py is not available")

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except TimeoutExpired:
            return self._failed("timeout", f"fetch_sporttery.py timed out after {timeout}s")
        except OSError as exc:
            return self._failed("execution_error", str(exc))

        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "command": command,
            "stdout": scrub_output(completed.stdout),
            "stderr": scrub_output(completed.stderr),
        }

    @staticmethod
    def _validate_nums(nums: list[str]) -> None:
        if not nums:
            raise ValueError("nums must include at least one 3-digit match number")
        invalid = [num for num in nums if not NUM_PATTERN.fullmatch(num)]
        if invalid:
            raise ValueError("nums must be 3-digit numeric strings")

    @staticmethod
    def _failed(code: str, message: str) -> dict:
        return {"ok": False, "error": {"code": code, "message": message}}


def scrub_output(value: str | None) -> str:
    text = value or ""
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda match: f"{match.group(1)}=[redacted]", text)
    return text
