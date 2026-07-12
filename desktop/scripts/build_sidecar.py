#!/usr/bin/env python3
"""Construct deterministic PyInstaller sidecar commands for supported targets.

The default mode is --dry-run and only prints the command. Passing --execute is
reserved for release automation after dependencies have been installed outside
this task.
"""

from __future__ import annotations

import argparse
import pathlib
import shlex
import subprocess

SUPPORTED_TARGETS = {
    "x86_64-pc-windows-msvc": "pitchmind-sidecar-x86_64-pc-windows-msvc.exe",
    "aarch64-apple-darwin": "pitchmind-sidecar-aarch64-apple-darwin",
    "x86_64-apple-darwin": "pitchmind-sidecar-x86_64-apple-darwin",
}


def artifact_name_for_target(target_triple: str) -> str:
    try:
        return SUPPORTED_TARGETS[target_triple]
    except KeyError as exc:
        supported = ", ".join(sorted(SUPPORTED_TARGETS))
        raise ValueError(f"Unsupported target triple {target_triple!r}. Supported: {supported}") from exc


def build_pyinstaller_command(target_triple: str, project_root: pathlib.Path) -> list[str]:
    artifact = artifact_name_for_target(target_triple)
    executable_name = artifact.removesuffix(".exe")
    separator = ";" if target_triple.endswith("windows-msvc") else ":"
    return [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--paths",
        str(project_root),
        "--name",
        executable_name,
        "--distpath",
        str(project_root / "desktop" / "src-tauri" / "binaries"),
        "--workpath",
        str(project_root / "desktop" / "build" / "pyinstaller" / target_triple),
        "--add-data",
        f"{project_root / 'app' / 'templates'}{separator}app/templates",
        "--add-data",
        f"{project_root / 'app' / 'static'}{separator}app/static",
        "--add-data",
        f"{project_root / 'data' / 'demo_matches.json'}{separator}data",
        "--add-data",
        f"{project_root / 'app' / 'main.py'}{separator}app",
        "--add-data",
        f"{project_root / 'scripts' / 'start.sh'}{separator}scripts",
        "--add-data",
        f"{project_root / 'scripts' / 'smoke.sh'}{separator}scripts",
        "--add-data",
        f"{project_root / 'scripts' / 'setup.sh'}{separator}scripts",
        "--add-data",
        f"{project_root / 'scripts' / 'package_release.sh'}{separator}scripts",
        "--add-data",
        f"{project_root / 'scripts' / 'external_trial_smoke.py'}{separator}scripts",
        "--add-data",
        f"{project_root / 'pyproject.toml'}{separator}.",
        "--collect-submodules",
        "app",
        str(project_root / "desktop" / "sidecar_main.py"),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=sorted(SUPPORTED_TARGETS))
    parser.add_argument("--project-root", default=pathlib.Path(__file__).resolve().parents[2])
    parser.add_argument("--dry-run", action="store_true", help="print command without invoking PyInstaller")
    parser.add_argument("--execute", action="store_true", help="invoke PyInstaller; not used by tests")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = pathlib.Path(args.project_root).resolve()
    command = build_pyinstaller_command(args.target, project_root)
    print(shlex.join(command))
    if args.execute:
        return subprocess.call(command, cwd=project_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
