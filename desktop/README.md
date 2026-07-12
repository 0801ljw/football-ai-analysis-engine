# 足球赛事 AI 推演引擎 desktop foundation

This directory contains the Tauri 2 desktop host and Python sidecar build/development scaffolding for the PitchMind desktop app.

## What is included

- `src-tauri/`: Tauri 2 Rust host configuration and sidecar supervisor.
- `dist/index.html`: minimal packaged loading page used before the local sidecar is ready.
- `sidecar_main.py`: PyInstaller entrypoint that runs `uvicorn` against `app.main:app` on localhost.
- `scripts/dev-sidecar.py`: optional manual FastAPI runner for debugging with `WC_DESKTOP_MODE=1`, `WC_APP_DATA_DIR`, `WC_HOST`, and `PORT` set.
- `scripts/build_sidecar.py`: constructs deterministic PyInstaller commands for supported release target triples and emits target-suffixed binaries into `src-tauri/binaries/`.
- `scripts/verify_desktop_config.py`: stdlib-only contract verifier for desktop metadata and sidecar packaging configuration.
- `scripts/verify_dmg_layout.py`: mounts a DMG read-only and rejects invalid roots that expose bare `Contents/` instead of the `足球赛事 AI 推演引擎.app` bundle.

## Developer boundaries

Dependencies must be installed separately for developer builds. This foundation intentionally does not run `npm install`, Cargo dependency resolution, PyInstaller, or any network install step.

No release/update publishing happens here. The unsigned beta does not register the updater Rust plugin and does not include active updater plugin configuration or placeholder keys. `createUpdaterArtifacts` remains `false`; later signed updater integration should add the updater dependency, plugin registration, real public key, release feed endpoints, and artifact generation in a signed release pipeline.

## Development sketch

1. Prepare Python, Node, Rust, Tauri CLI, and PyInstaller in your own environment.
2. Run `python3 scripts/verify_desktop_config.py` from this directory or `python3 desktop/scripts/verify_desktop_config.py` from the repository root.
3. Run the Tauri dev host with the dependencies you installed separately. The Rust supervisor is the sole sidecar owner; Tauri loads `dist/index.html`, starts the Python sidecar, then navigates to the ready localhost URL or a diagnostic error page.
4. For sidecar-only debugging, run `python3 scripts/dev-sidecar.py --app-data-dir .desktop-data --port 8765` manually outside Tauri.
5. For any local/manual macOS DMG rebuild, pass a source directory that contains `足球赛事 AI 推演引擎.app`, not the `.app` path itself, then run `python3 scripts/verify_dmg_layout.py --dmg <path-to.dmg>`. The mounted DMG root must contain the `.app` bundle (and optionally `Applications`), never bare `Contents/`; `hdiutil convert` success alone is not sufficient.

The existing web UI references `app/static/style.css`; documentation and packaging helpers should use that exact singular stylesheet path.

## Supported sidecar targets

- `x86_64-pc-windows-msvc` -> `pitchmind-sidecar-x86_64-pc-windows-msvc.exe`
- `aarch64-apple-darwin` -> `pitchmind-sidecar-aarch64-apple-darwin`
- `x86_64-apple-darwin` -> `pitchmind-sidecar-x86_64-apple-darwin`
