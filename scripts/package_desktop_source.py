#!/usr/bin/env python3
"""Create an allowlisted desktop source package without local runtime data.

This helper does not depend on Git. It copies only explicit source/documentation
paths needed to review or rebuild the unsigned desktop Beta pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import tarfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]

ALLOWLIST = [
    "README.md",
    "RELEASE_CHECKLIST.md",
    "pyproject.toml",
    ".gitignore",
    ".github/workflows/desktop-release.yml",
    "app",
    "data/demo_matches.json",
    "desktop/README.md",
    "desktop/INSTALL_BETA.md",
    "desktop/package.json",
    "desktop/package-lock.json",
    "desktop/dist/index.html",
    "desktop/sidecar_main.py",
    "desktop/scripts",
    "desktop/src-tauri/Cargo.toml",
    "desktop/src-tauri/Cargo.lock",
    "desktop/src-tauri/build.rs",
    "desktop/src-tauri/tauri.conf.json",
    "desktop/src-tauri/src",
    "desktop/src-tauri/capabilities",
    "desktop/src-tauri/icons",
    "scripts",
    "tests",
]

FORBIDDEN_PATHS = [
    ".env",
    "data/app.db",
    "runs/",
    "desktop/src-tauri/target/",
    "desktop/src-tauri/binaries/",
    "desktop/build/",
    "dist/worldcup",
    "desktop/node_modules/",
]
FORBIDDEN_NAMES = {".env", "app.db", "node_modules", "target", "binaries", "__pycache__", ".pytest_cache"}
FORBIDDEN_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3"}


def iter_allowlisted_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for item in ALLOWLIST:
        path = ROOT / item
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file() and not is_forbidden(child):
                files.append(child)
    return sorted(set(files), key=lambda p: p.relative_to(ROOT).as_posix())


def is_forbidden(path: pathlib.Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    for forbidden in FORBIDDEN_PATHS:
        if forbidden.endswith("/") and rel.startswith(forbidden):
            return True
        if rel == forbidden:
            return True
    if any(part in FORBIDDEN_NAMES for part in path.relative_to(ROOT).parts):
        return True
    if path.suffix in FORBIDDEN_SUFFIXES:
        return True
    return False


def add_file(tar: tarfile.TarFile, source: pathlib.Path, arcname: str) -> None:
    info = tar.gettarinfo(str(source), arcname)
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    info.mtime = 0
    with source.open("rb") as handle:
        tar.addfile(info, handle)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=pathlib.Path, default=ROOT / "dist")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--timestamp", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument(
        "--deterministic-name",
        action="store_true",
        help="write worldcup-ai-content-engine-source.tar.gz with a stable top-level directory for CI release aggregation",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package_name = (
        "worldcup-ai-content-engine-source"
        if args.deterministic_name
        else f"pitchmind-desktop-source-v{args.version}-{args.timestamp}"
    )
    archive_name = "worldcup-ai-content-engine-source.tar.gz" if args.deterministic_name else f"{package_name}.tar.gz"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    archive = args.output_dir / archive_name
    files = iter_allowlisted_files()
    blocked = [path.relative_to(ROOT).as_posix() for path in files if is_forbidden(path)]
    if blocked:
        raise SystemExit(f"Refusing to package runtime secrets/artifacts: {blocked}")
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        for path in files:
            rel = path.relative_to(ROOT).as_posix()
            add_file(tar, path, f"{package_name}/{rel}")
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    checksum.write_text(f"{sha256_file(archive)}  {archive.name}\n", encoding="utf-8")
    print(archive)
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
