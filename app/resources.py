from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    """Return the base directory for bundled read-only resources.

    PyInstaller extracts --add-data payloads under sys._MEIPASS. In source mode
    the same relative resource paths live under the repository root.
    """
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return ROOT_DIR


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)
