#!/usr/bin/env python3
"""Write deterministic SHA-256 manifests for release assets.

The script intentionally refuses obvious runtime secret/data paths so a release
helper cannot accidentally checksum and upload local configuration or databases.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys

FORBIDDEN_PARTS = {
    ".env",
    "app.db",
    "runs",
    "target",
    "binaries",
    "__pycache__",
}
FORBIDDEN_SUBSTRINGS = ("API_KEY", "SECRET", "TOKEN")


def is_forbidden(path: pathlib.Path) -> bool:
    parts = set(path.parts)
    if parts & FORBIDDEN_PARTS:
        return True
    name = path.name.lower()
    return name.endswith((".env", ".db", ".sqlite", ".sqlite3"))


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("SHA256SUMS.txt"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = sorted(path.resolve() for path in args.files)
    if not files:
        print("No files provided", file=sys.stderr)
        return 2
    lines: list[str] = []
    for path in files:
        if not path.is_file():
            print(f"Refusing non-file path: {path}", file=sys.stderr)
            return 2
        if is_forbidden(path):
            print(f"Refusing to checksum runtime secret/artifact path: {path}", file=sys.stderr)
            return 2
        digest = sha256_file(path)
        lines.append(f"{digest}  {path.name}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(lines), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
