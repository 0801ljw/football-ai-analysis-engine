from __future__ import annotations

import os
import pathlib
import sys

import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_PORT = 65535


def ensure_project_root_on_sys_path() -> pathlib.Path:
    """Allow source execution from desktop/ while PyInstaller bundles app.*.

    PyInstaller discovers app.* from --paths in desktop/scripts/build_sidecar.py.
    This runtime path insertion keeps direct execution of this entrypoint stable
    when the current working directory is desktop/ or another non-root folder.
    """
    project_root = pathlib.Path(__file__).resolve().parents[1]
    project_root_text = str(project_root)
    if project_root_text not in sys.path:
        sys.path.insert(0, project_root_text)
    return project_root


def parse_port(value: str | None) -> int:
    if value is None:
        return DEFAULT_PORT
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"PORT must be a valid integer from 0 to {MAX_PORT}") from exc
    if not 0 <= port <= MAX_PORT:
        raise ValueError(f"PORT must be a valid integer from 0 to {MAX_PORT}")
    return port


def main() -> int:
    ensure_project_root_on_sys_path()
    host = os.environ.get("WC_HOST", DEFAULT_HOST) or DEFAULT_HOST
    port = parse_port(os.environ.get("PORT"))
    uvicorn.run("app.main:app", host=host, port=port, log_level=os.environ.get("WC_LOG_LEVEL", "info"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
