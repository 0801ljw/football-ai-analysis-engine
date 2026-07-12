#!/usr/bin/env python3
"""Verify desktop host configuration without network access or dependency installs."""

from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "desktop"
SRC_TAURI = DESKTOP / "src-tauri"
DISPLAY_NAME = "足球赛事 AI 推演引擎"
IDENTIFIER = "com.pitchmind.desktop"
PROHIBITED = ("FIFA", "World Cup", "世界杯")


def fail(message: str) -> None:
    raise SystemExit(f"desktop configuration verification failed: {message}")


def assert_no_prohibited_terms(paths: list[pathlib.Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for term in PROHIBITED:
            if term in text:
                fail(f"prohibited tournament trademark {term!r} found in {path.relative_to(ROOT)}")


def main() -> int:
    config_path = SRC_TAURI / "tauri.conf.json"
    cargo_path = SRC_TAURI / "Cargo.toml"
    package_path = DESKTOP / "package.json"
    capability_path = SRC_TAURI / "capabilities" / "default.json"
    frontend_path = DESKTOP / "dist" / "index.html"
    sidecar_entrypoint = DESKTOP / "sidecar_main.py"
    for path in (config_path, cargo_path, package_path, capability_path, frontend_path, sidecar_entrypoint):
        if not path.exists():
            fail(f"missing {path.relative_to(ROOT)}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("productName") != DISPLAY_NAME:
        fail("invalid desktop productName")
    if config.get("identifier") != IDENTIFIER:
        fail("invalid desktop identifier")
    build = config.get("build", {})
    if "beforeDevCommand" in build or "devUrl" in build:
        fail("Rust supervisor must be the single sidecar owner; remove beforeDevCommand/devUrl")
    if build.get("frontendDist") != "../dist":
        fail("frontendDist must point at the packaged loading UI")
    if config.get("bundle", {}).get("externalBin") != ["binaries/pitchmind-sidecar"]:
        fail("externalBin must map src-tauri/binaries sidecar base name")
    if config.get("bundle", {}).get("icon") != ["icons/icon.png"]:
        fail("bundle icon must explicitly use the validated src-tauri/icons/icon.png")
    if config.get("bundle", {}).get("createUpdaterArtifacts") is not False:
        fail("unsigned beta builds must not create updater artifacts")
    install_mode = config.get("bundle", {}).get("windows", {}).get("nsis", {}).get("installMode")
    if install_mode != "currentUser":
        fail("NSIS installMode must be currentUser for unsigned beta installs")
    if config.get("app", {}).get("windows", [{}])[0].get("url") != "index.html":
        fail("initial window must load the packaged loading page")
    if "updater" in config.get("plugins", {}):
        fail("updater plugin config must be absent until signed updater integration")
    if "tauri-plugin-updater" in cargo_path.read_text(encoding="utf-8"):
        fail("updater Rust plugin must not be registered for unsigned beta")

    assert_no_prohibited_terms([config_path, cargo_path, package_path, capability_path])
    print("desktop configuration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
