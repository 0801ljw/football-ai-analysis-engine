from __future__ import annotations

import subprocess
from pathlib import Path
from subprocess import TimeoutExpired

from app.skill_bridge import SkillBridge
from app.sporttery_service import scrub_output


ALLOWED_THEMES: frozenset[str] = frozenset({"dark", "purple", "blue"})


class ReportService:
    def __init__(self, bridge: SkillBridge | None = None):
        self.bridge = bridge or SkillBridge()

    def build_report_command(
        self,
        odds_path: Path,
        out_path: Path,
        title: str,
        theme: str = "dark",
        intel_path: Path | None = None,
    ) -> list[str]:
        if theme not in ALLOWED_THEMES:
            raise ValueError("theme must be one of: blue, dark, purple")
        command = [
            "python3",
            str(self.bridge.script_path("gen_multi_market_report.py")),
            "--odds",
            str(odds_path),
            "--out",
            str(out_path),
            "--title",
            title,
            "--theme",
            theme,
        ]
        if intel_path is not None:
            command.extend(["--intel", str(intel_path)])
        return command

    def generate_report_file(
        self,
        odds_path: Path,
        out_path: Path,
        title: str,
        theme: str = "dark",
        intel_path: Path | None = None,
        timeout: int = 30,
    ) -> dict:
        try:
            command = self.build_report_command(odds_path, out_path, title, theme, intel_path)
        except ValueError as exc:
            return self._failed("validation_error", str(exc))

        if not self.bridge.has_script("gen_multi_market_report.py"):
            return self._failed("script_unavailable", "gen_multi_market_report.py is not available")

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except TimeoutExpired:
            return self._failed("timeout", f"gen_multi_market_report.py timed out after {timeout}s")
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
    def _failed(code: str, message: str) -> dict:
        return {"ok": False, "error": {"code": code, "message": message}}
