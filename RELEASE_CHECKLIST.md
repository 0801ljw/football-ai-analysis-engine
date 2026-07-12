# Release Checklist

## Product copy
- No guarantee language.
- No gambling-sales wording.
- Always say: 概率推演 / 数据研究 / 不构成下注建议。

## Verification
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
bash -n scripts/start.sh scripts/smoke.sh scripts/doctor.sh scripts/setup.sh
node --check app/static/app.js
scripts/doctor.sh
scripts/start.sh
BASE_URL=http://127.0.0.1:8787 scripts/smoke.sh
```

## Security
- Keep default `WC_HOST=127.0.0.1`.
- If exposing beyond localhost, set `WC_API_TOKEN`.
- Never commit `.env` with real tokens.

## Desktop Draft Release
- Release workflow is `.github/workflows/desktop-release.yml` and must be started manually with `workflow_dispatch` only.
- The workflow must create a draft/prerelease GitHub Release; 不要发布公开 Release until artifacts, checksums, and install notes are manually reviewed.
- Verify CI matrix includes Windows x86_64 NSIS, macOS Apple Silicon DMG, and macOS Intel DMG.
- Verify PyInstaller sidecar runs before Tauri build and produces target-suffixed sidecar binaries.
- Required local source checks before enabling a run:
  ```bash
  python -m pytest -q
  python -m pip check
  python desktop/scripts/verify_desktop_config.py
  python -m py_compile scripts/write_checksums.py scripts/package_desktop_source.py scripts/create_release_notes.py desktop/scripts/package_desktop_release.py desktop/scripts/build_sidecar.py desktop/scripts/verify_desktop_config.py desktop/scripts/verify_dmg_layout.py desktop/sidecar_main.py
  ```
- Confirm source packages/checksums exclude `.env`, `data/app.db`, `runs/`, Tauri `target/`, sidecar `binaries/`, and local build/release directories.
- Confirm every macOS DMG has been mounted and verified before normalization: the visible root must contain `足球赛事 AI 推演引擎.app` and may contain `Applications`; it must not contain bare `Contents/`. Use `python desktop/scripts/verify_dmg_layout.py --dmg <path-to.dmg>` for any local/manual DMG workaround and never accept `hdiutil convert` success alone.
- Confirm release aggregation contains normalized installers, `worldcup-ai-content-engine-source.tar.gz`, `INSTALL_BETA.md`, combined `SHA256SUMS.txt`, and `RELEASE_NOTES.md` before manually publishing anything.
- Unsigned Beta updates are manual GitHub Release downloads only; do not claim automatic updater support until signed updater work is implemented.

## Demo script
1. Run `scripts/setup.sh`.
2. Run `scripts/start.sh`.
3. Open `/`.
4. Use “三步生成赛前报告”.
5. Show 数据可信度, report preview, export zip, admin usage.

## Multi-user
- Create an admin user and store the returned token securely.
- Verify `/api/me` with `X-API-Token`.
- Verify non-admin cannot access admin endpoints.
- Verify per-user real run quota.
