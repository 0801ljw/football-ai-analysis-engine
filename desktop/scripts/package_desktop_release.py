#!/usr/bin/env python3
"""Normalize a single Tauri installer into the desktop release artifact layout.

The CI build output filenames are platform/tool dependent. This helper selects
exactly one installer from a bundle directory, copies it to a stable public
filename, and includes the unsigned Beta installation notes beside it.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
INSTALL_BETA = ROOT / "desktop" / "INSTALL_BETA.md"

FILENAME_BY_TARGET_BUNDLE = {
    ("x86_64-pc-windows-msvc", "nsis"): "足球赛事AI推演引擎-Setup-x64.exe",
    ("aarch64-apple-darwin", "dmg"): "足球赛事AI推演引擎-macOS-AppleSilicon.dmg",
    ("x86_64-apple-darwin", "dmg"): "足球赛事AI推演引擎-macOS-Intel.dmg",
}
EXTENSION_BY_BUNDLE = {
    "nsis": ".exe",
    "dmg": ".dmg",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, type=pathlib.Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    return parser.parse_args()


def select_installer(bundle_dir: pathlib.Path, bundle: str) -> pathlib.Path:
    suffix = EXTENSION_BY_BUNDLE.get(bundle)
    if suffix is None:
        raise SystemExit(f"Unsupported bundle type: {bundle}")
    candidates = sorted(path for path in bundle_dir.glob(f"*{suffix}") if path.is_file())
    if len(candidates) != 1:
        names = ", ".join(path.name for path in candidates) or "none"
        raise SystemExit(
            f"Expected exactly one {suffix} installer in {bundle_dir}, found {len(candidates)}: {names}"
        )
    return candidates[0]


def normalize(bundle_dir: pathlib.Path, target: str, bundle: str, output_dir: pathlib.Path) -> list[pathlib.Path]:
    release_name = FILENAME_BY_TARGET_BUNDLE.get((target, bundle))
    if release_name is None:
        raise SystemExit(f"Unsupported target/bundle pair: {target} {bundle}")
    if not INSTALL_BETA.is_file():
        raise SystemExit(f"Missing install notes: {INSTALL_BETA}")
    installer = select_installer(bundle_dir, bundle)
    output_dir.mkdir(parents=True, exist_ok=True)
    installer_out = output_dir / release_name
    notes_out = output_dir / "INSTALL_BETA.md"
    shutil.copy2(installer, installer_out)
    shutil.copy2(INSTALL_BETA, notes_out)
    return [installer_out, notes_out]


def main() -> int:
    args = parse_args()
    try:
        outputs = normalize(args.bundle_dir, args.target, args.bundle, args.output_dir)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
