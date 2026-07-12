#!/usr/bin/env python3
"""Mount and verify a macOS DMG has the expected installer root layout.

The valid user-facing Tauri DMG root is the app bundle itself, optionally plus
an Applications drop-link. A DMG whose root contains the app bundle's internal
``Contents/`` directory is invalid because it was built from the ``.app`` as the
source folder instead of from a folder containing the ``.app``.
"""

from __future__ import annotations

import argparse
import pathlib
import plistlib
import subprocess
import sys
from collections.abc import Iterable

DEFAULT_APP_NAME = "足球赛事 AI 推演引擎.app"
ALLOWED_VISIBLE_ROOT_ITEMS = {DEFAULT_APP_NAME, "Applications"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dmg", type=pathlib.Path, help="DMG file to attach read-only and verify")
    source.add_argument(
        "--mounted-root",
        type=pathlib.Path,
        help="Already-mounted DMG root; intended for tests/debugging only",
    )
    parser.add_argument("--expected-app-name", default=DEFAULT_APP_NAME)
    return parser.parse_args()


def fail(message: str) -> None:
    raise SystemExit(f"DMG layout verification failed: {message}")


def visible_root_items(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        (path for path in root.iterdir() if not path.name.startswith(".")),
        key=lambda path: path.name,
    )


def validate_mount_root(root: pathlib.Path, expected_app_name: str = DEFAULT_APP_NAME) -> None:
    if not root.is_dir():
        fail(f"mounted root does not exist or is not a directory: {root}")

    items = visible_root_items(root)
    names = {path.name for path in items}
    expected = {expected_app_name}
    allowed = {expected_app_name, "Applications"}

    if "Contents" in names:
        fail(
            "mounted root contains bare Contents/; the DMG source was likely the .app bundle "
            "itself instead of a parent folder containing the .app"
        )

    missing = expected - names
    if missing:
        fail(f"mounted root is missing expected app bundle(s): {', '.join(sorted(missing))}")

    unexpected = names - allowed
    if unexpected:
        fail(
            "mounted root contains unexpected visible item(s): "
            f"{', '.join(sorted(unexpected))}; expected only {expected_app_name}"
            " and optional Applications link"
        )

    app_path = root / expected_app_name
    if not app_path.is_dir():
        fail(f"expected app bundle is not a directory: {app_path}")
    if not (app_path / "Contents" / "Info.plist").is_file():
        fail(f"expected app bundle lacks Contents/Info.plist: {app_path}")

    applications = root / "Applications"
    if applications.exists() and not (applications.is_symlink() or applications.is_dir()):
        fail("Applications drop-link exists but is neither a symlink nor a directory-like Finder alias")

    print(
        "DMG layout verified: "
        + ", ".join(path.name for path in items)
        + f" at {root}"
    )


def attach_dmg(dmg: pathlib.Path) -> tuple[pathlib.Path, str | None]:
    if not dmg.is_file():
        fail(f"DMG does not exist: {dmg}")
    command = ["hdiutil", "attach", "-plist", "-nobrowse", "-readonly", str(dmg)]
    result = subprocess.run(command, text=False, capture_output=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        fail(f"hdiutil attach failed for {dmg}: {stderr.strip()}")
    try:
        plist = plistlib.loads(result.stdout)
    except Exception as exc:  # pragma: no cover - defensive around hdiutil output
        fail(f"could not parse hdiutil attach plist output: {exc}")

    entities: Iterable[dict[str, object]] = plist.get("system-entities", [])
    for entity in entities:
        mount_point = entity.get("mount-point")
        if isinstance(mount_point, str) and mount_point:
            device = entity.get("dev-entry")
            return pathlib.Path(mount_point), device if isinstance(device, str) else None
    fail(f"hdiutil attach did not report a mount point for {dmg}")


def detach(target: str | pathlib.Path) -> None:
    result = subprocess.run(["hdiutil", "detach", str(target)], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        result = subprocess.run(
            ["hdiutil", "detach", "-force", str(target)], text=True, capture_output=True, check=False
        )
        if result.returncode != 0:
            print(f"warning: failed to detach {target}: {result.stderr.strip()}", file=sys.stderr)


def verify_dmg(dmg: pathlib.Path, expected_app_name: str) -> None:
    mount_point, device = attach_dmg(dmg)
    try:
        validate_mount_root(mount_point, expected_app_name)
    finally:
        detach(device or mount_point)


def main() -> int:
    args = parse_args()
    if args.dmg:
        verify_dmg(args.dmg, args.expected_app_name)
    else:
        validate_mount_root(args.mounted_root, args.expected_app_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
