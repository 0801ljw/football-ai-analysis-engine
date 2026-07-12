from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


INTERNAL_BRAND_NAME = "PitchMind"


@dataclass(frozen=True)
class DesktopPaths:
    app_data_dir: Path
    db_path: Path
    runs_path: Path
    config_path: Path
    logs_path: Path


def default_app_data_dir() -> Path:
    """Return the default per-user desktop data directory for PitchMind."""

    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / INTERNAL_BRAND_NAME
    if sys.platform.startswith("win"):
        return home / "AppData" / "Roaming" / INTERNAL_BRAND_NAME
    return home / ".local" / "share" / INTERNAL_BRAND_NAME


def desktop_paths(app_data_dir: str | Path | None = None) -> DesktopPaths:
    root = Path(app_data_dir).expanduser() if app_data_dir else default_app_data_dir()
    return DesktopPaths(
        app_data_dir=root,
        db_path=root / "data" / "app.db",
        runs_path=root / "runs",
        config_path=root / "config",
        logs_path=root / "logs",
    )


def initialize_user_data(app_data_dir: str | Path | None = None) -> DesktopPaths:
    """Create required desktop user-data directories and return their paths."""

    paths = desktop_paths(app_data_dir)
    paths.db_path.parent.mkdir(parents=True, exist_ok=True)
    paths.runs_path.mkdir(parents=True, exist_ok=True)
    paths.config_path.mkdir(parents=True, exist_ok=True)
    paths.logs_path.mkdir(parents=True, exist_ok=True)
    return paths
