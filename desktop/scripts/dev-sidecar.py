#!/usr/bin/env python3
"""Run the existing FastAPI app as a localhost desktop-development sidecar.

This helper intentionally does not install dependencies. Developer builds must
prepare the Python environment separately before invoking it.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
STYLE_PATH = ROOT / "app" / "static" / "style.css"  # documented path: app/static/style.css


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="localhost bind address only")
    parser.add_argument("--port", default=os.environ.get("PORT", "8765"), help="localhost port")
    parser.add_argument(
        "--app-data-dir",
        default=None,
        help="explicit desktop app data directory; temporary directory is used when omitted",
    )
    return parser.parse_args()


def run_uvicorn(app_data_dir: pathlib.Path, host: str, port: str) -> int:
    if host != "127.0.0.1":
        raise SystemExit("dev sidecar must bind to 127.0.0.1")
    if not STYLE_PATH.exists():
        raise SystemExit(f"expected documented stylesheet path to exist: {STYLE_PATH.relative_to(ROOT)}")

    env = os.environ.copy()
    env.update(
        {
            "WC_DESKTOP_MODE": "1",
            "WC_APP_DATA_DIR": str(app_data_dir),
            "WC_HOST": host,
            "PORT": str(port),
        }
    )
    command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)]
    return subprocess.call(command, cwd=ROOT, env=env)


def main() -> int:
    args = parse_args()
    if args.app_data_dir:
        app_data_dir = pathlib.Path(args.app_data_dir).expanduser().resolve()
        app_data_dir.mkdir(parents=True, exist_ok=True)
        return run_uvicorn(app_data_dir, args.host, args.port)

    with tempfile.TemporaryDirectory(prefix="pitchmind-desktop-dev-") as temp_dir:
        return run_uvicorn(pathlib.Path(temp_dir), args.host, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
