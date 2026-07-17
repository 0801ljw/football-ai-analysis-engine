#!/usr/bin/env python3
"""Create deterministic draft release notes from normalized release assets."""

from __future__ import annotations

import argparse
import pathlib

EXPECTED_ASSETS = [
    "PitchMind-Setup-x64.exe",
    "PitchMind-macOS-AppleSilicon.dmg",
    "PitchMind-macOS-Intel.dmg",
    "worldcup-ai-content-engine-source.tar.gz",
    "INSTALL_BETA.md",
    "SHA256SUMS.txt",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-dir", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args()


def render_notes(assets_dir: pathlib.Path) -> str:
    files = sorted(path.name for path in assets_dir.iterdir() if path.is_file() and path.name != "RELEASE_NOTES.md")
    missing = [name for name in EXPECTED_ASSETS if name not in files]
    if missing:
        raise SystemExit(f"Missing expected release asset(s): {', '.join(missing)}")
    asset_lines = "\n".join(f"- `{name}`" for name in files)
    return f"""# Desktop unsigned Beta

Draft GitHub Release generated from CI artifacts. Keep this release as a draft/prerelease until a maintainer manually reviews every file, `SHA256SUMS.txt`, and `INSTALL_BETA.md`.

## Assets

{asset_lines}

## Install and verification

1. Download the installer matching your platform.
2. Verify it against `SHA256SUMS.txt`.
3. Read `INSTALL_BETA.md` before installing this unsigned Beta.
4. Updates are manual GitHub Release downloads only; the signed automatic updater is not enabled in this stage.
"""


def main() -> int:
    args = parse_args()
    notes = render_notes(args.assets_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(notes, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
