# 足球赛事 AI 推演引擎 Desktop Beta Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 将现有 FastAPI 工作台封装为 Windows/macOS 双端可安装的“足球赛事 AI 推演引擎”桌面 Beta，并提供内置运行时、数据源降级、用户自带 API Key 设置、GitHub Release 构建与更新基础。

**Architecture:** 使用 Tauri 2 作为原生桌面宿主；当前 FastAPI 作为 Python sidecar。本地运行时通过显式 `WC_DESKTOP_MODE=1` 和系统应用数据目录隔离 SQLite、run、日志与配置。Tauri 启动 sidecar，轮询健康接口后加载 localhost 工作台；桌面前端仅做宿主生命周期与设置桥接，业务继续由 FastAPI 承担。

**Tech Stack:** Python 3.11+/FastAPI/pytest、Tauri 2/Rust、vanilla JS、PyInstaller、GitHub Actions、NSIS、DMG。

---

## Task 1: Desktop runtime configuration and product branding

**Objective:** 为桌面运行态提供安全、可测试的配置与用户数据目录，同时不破坏现有源码运行模式。

**Files:**
- Create: `app/desktop_runtime.py`
- Modify: `app/config.py`
- Modify: `app/runtime_doctor.py`
- Modify: `.env.example`
- Modify: `tests/test_config.py`
- Create: `tests/test_desktop_runtime.py`

**Step 1: Write failing tests**

测试 desktop mode：
- 应用名默认是“足球赛事 AI 推演引擎”；
- `WC_DESKTOP_MODE=1` 和 `WC_APP_DATA_DIR=<tmp>` 时，DB/runs/config/logs 都落在 app data；
- app data 目录创建不依赖 Hermes skill；
- desktop doctor 不把不存在的 `WC_SKILL_PATH` 当 fatal。

**Step 2: Run RED tests**

Run: `.venv/bin/python -m pytest tests/test_config.py tests/test_desktop_runtime.py -q`
Expected: FAIL because desktop runtime is absent.

**Step 3: Implement minimally**

- 添加 `DEFAULT_APP_NAME = "足球赛事 AI 推演引擎"`；
- `desktop_runtime.py` 只负责平台数据目录、目录初始化、redacted settings；
- Settings 增加 `desktop_mode`、`app_data_dir`、`config_path`、`logs_path`、`api_key_storage_mode`；
- desktop mode 默认将 db/runs 放到 app data，除非明确 env override；
- doctor 增加 desktop runtime check，且 desktop mode 下 skill 缺失为 warn。

**Step 4: Run GREEN tests**

Run: `.venv/bin/python -m pytest tests/test_config.py tests/test_desktop_runtime.py -q`
Expected: PASS.

**Step 5: Regression**

Run: `.venv/bin/python -m pytest -q && .venv/bin/python -m pip check`

---

## Task 2: Local desktop settings API and secure-ish key boundary

**Objective:** 给桌面 UI 一个不回显 secret 的设置 API；当前 Beta 将 Key 写入仅限用户权限的本地 JSON 配置（`api_key_storage_mode=local_json`，状态显示为 `local user configuration`），并尽力设置文件权限为 0600。此版本不使用、也不声称使用 OS keychain。

**Files:**
- Create: `app/desktop_settings.py`
- Modify: `app/schemas.py`
- Modify: `app/main.py`
- Create: `tests/test_desktop_settings.py`
- Modify: `tests/test_app_smoke.py`

**Step 1: Write failing tests**

覆盖：
- desktop mode 才开放 `/api/desktop/settings`；
- GET 只返回 `configured: bool` 和 masked preview，不返回原始 API Key；
- PUT 能设置/清除 named provider key；
- 非法 provider/超长 key 返回 422；
- key 内容不出现在 JSON 响应和日志字段。

**Step 2: Run RED tests**

Run: `.venv/bin/python -m pytest tests/test_desktop_settings.py -q`
Expected: FAIL.

**Step 3: Implement minimally**

- 用 stdlib JSON 文件保存 provider keys，文件权限尽可能限制为 user-only；
- `DesktopSettingsStore` 接口独立，当前实现为本地 JSON；后续如实现 OS keychain 需同步更新 `api_key_storage_mode` 与用户可见文档；
- API 将密钥输入与配置状态解耦；
- 在普通 server mode 返回 404，避免意外扩大接口。

**Step 4: Run GREEN and regression**

Run: `.venv/bin/python -m pytest tests/test_desktop_settings.py tests/test_app_smoke.py -q && .venv/bin/python -m pytest -q`

---

## Task 3: Data-source availability and honest fallback surface

**Objective:** 在桌面模式下提供统一的“本地/公开源/用户 Key/降级”状态，确保实时源失败时永不伪装为实时结果。

**Files:**
- Create: `app/data_source_status.py`
- Modify: `app/main.py`
- Create: `tests/test_data_source_status.py`
- Modify: `app/templates/index.html`
- Modify: `app/static/app.js`
- Modify: `app/static/styles.css` (if existing styling requires it)

**Step 1: Write failing tests**

测试 `/api/desktop/data-status`：
- 返回 local fallback 可用、公开实时源状态、用户 key 配置状态、更新时间、降级 reason；
- public probe 失败时为 degraded 而非 live；
- 不泄露 key；
- 页面包含“数据来源”“更新时间”“降级说明”和固定合规声明。

**Step 2: RED**

Run: `.venv/bin/python -m pytest tests/test_data_source_status.py -q`

**Step 3: Implement minimally**

- 不新增任何不可靠的隐藏抓取；复用当前 `SportteryService`/skill bridge 的可用性检查；
- 声明 public source 仅在显式 discover/fetch 成功后为 live-ish；
- 前端显示可信度与降级状态；
- 保持现有三步 workflow 与 dry-run 默认逻辑不变。

**Step 4: GREEN and regression**

Run: `.venv/bin/python -m pytest tests/test_data_source_status.py tests/test_app_smoke.py -q && .venv/bin/python -m pytest -q`

---

## Task 4: Tauri desktop host and Python sidecar lifecycle

**Objective:** 新建 Tauri 2 宿主，在开发态和生产态启动 Python sidecar、选择本地端口、等候 doctor、加载主 UI，并能干净终止 sidecar。

**Files:**
- Create: `desktop/package.json`
- Create: `desktop/src-tauri/Cargo.toml`
- Create: `desktop/src-tauri/tauri.conf.json`
- Create: `desktop/src-tauri/build.rs`
- Create: `desktop/src-tauri/src/main.rs`
- Create: `desktop/src-tauri/capabilities/default.json`
- Create: `desktop/README.md`
- Create: `desktop/scripts/dev-sidecar.py`
- Create: `desktop/scripts/build_sidecar.py`
- Create: `desktop/scripts/verify_desktop_config.py`
- Create: `tests/test_desktop_packaging.py`

**Step 1: Write failing tests**

Python tests validate packaging contract rather than requiring a GUI:
- Tauri config uses internal brand id `com.pitchmind.desktop` and display name `足球赛事 AI 推演引擎`;
- config declares NSIS/Dmg target metadata and updater endpoint placeholder from GitHub Releases;
- sidecar builder has deterministic target mapping and rejects unsupported platform;
- dev sidecar injects desktop env, app data tmp dir, and localhost bind;
- Tauri files do not contain product-forbidden tournament trademarks.

**Step 2: RED**

Run: `.venv/bin/python -m pytest tests/test_desktop_packaging.py -q`

**Step 3: Implement minimally**

- Tauri Rust sidecar supervisor chooses a free localhost port, starts sidecar with `WC_DESKTOP_MODE=1`, `WC_APP_DATA_DIR`, `WC_HOST=127.0.0.1`, `PORT`; waits bounded time on `/api/system/doctor`; opens local URL only after healthy; kills child on exit.
- Use dev sidecar command for local development and `externalBin` packaged sidecar for production.
- Do not implement actual updater signing yet; add config/doc scaffolding gated by release public key placeholder.
- Do not modify existing core frontend server routing.

**Step 4: GREEN**

Run: `.venv/bin/python -m pytest tests/test_desktop_packaging.py -q`

**Step 5: Build checks**

Run: `cd desktop && npm install && npm run check && npm run tauri -- --help`

Then run full Python suite.

---

## Task 5: Cross-platform build scripts and GitHub Actions draft release pipeline

**Objective:** 提供可复现的 sidecar + Tauri 构建脚本以及三平台 GitHub Actions 发布工作流；只创建 Draft Release，不自动公开。

**Files:**
- Create: `.github/workflows/desktop-release.yml`
- Create: `desktop/scripts/package_desktop_release.py`
- Create: `desktop/scripts/generate_checksums.py`
- Create: `desktop/INSTALL_BETA.md`
- Modify: `README.md`
- Modify: `RELEASE_CHECKLIST.md`
- Modify: `.gitignore`
- Modify: `tests/test_desktop_packaging.py`

**Step 1: Write failing tests**

覆盖：
- workflow matrix 包含 Windows x64、macOS arm64、macOS x64；
- release 仅在 `workflow_dispatch` + `draft: true` 路径发布；
- package script 产物使用产品展示名、包含 SHA-256；
- `.gitignore` 排除 sidecar 二进制、Tauri target、桌面用户配置和私钥；
- 安装文档包含未签名 Beta 的 SmartScreen/Gatekeeper 放行说明以及不泄露 Key 的提示。

**Step 2: RED**

Run: `.venv/bin/python -m pytest tests/test_desktop_packaging.py -q`

**Step 3: Implement minimally**

- 采用 GitHub Actions runner 原生编译；不在当前 Mac 伪造 Windows 包；
- workflow 上传 artifact，汇总 checksum，手动触发时创建 draft release；
- macOS 设置架构原生 runner，Windows 生成 NSIS；
- 仅保留自动更新 metadata / endpoint scaffold，明确未签名 Beta 不自动开启更新安装。

**Step 4: GREEN and full verification**

Run:
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
bash -n scripts/start.sh scripts/smoke.sh scripts/doctor.sh scripts/setup.sh
node --check app/static/app.js
python3 desktop/scripts/verify_desktop_config.py
```

---

## Task 6: Local build and smoke acceptance

**Objective:** 在当前 macOS arm64 开发机实际构建 sidecar 和 Tauri bundle（若本地依赖可用），验证 desktop runtime 端到端；不能构建的跨平台产物交给 CI。

**Files:**
- Modify only if defects found in Task 1–5
- Create: `docs/desktop-beta-acceptance.md`

**Step 1: Capture baseline**

Run existing full Python suite and save results.

**Step 2: Local desktop smoke**

- Build Python sidecar for macOS arm64;
- build/run Tauri in dev mode or bundle mode;
- inspect `/api/system/doctor` under desktop env;
- create a dry-run and export ZIP through API;
- verify app data is outside repo and no API secret appears in logs.

**Step 3: Document evidence**

Document exact commands, result, unresolved signing limitation, and CI-only Windows/Intel verification.

**Step 4: Final verification**

Run all Python tests, package contract tests, syntax checks and product forbidden-language scan.

---

## Git and release policy

The project currently has no Git repository. Do **not** initialize, commit, push, create a GitHub repo, publish a release, or upload artifacts without a separate explicit user approval. The implementation can prepare all source files and CI workflow locally; publishing remains a gated external side effect.
