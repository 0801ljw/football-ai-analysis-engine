# 足球赛事 AI 推演引擎

Public product name: **足球赛事 AI 推演引擎**. Internal desktop/release owner name: **PitchMind**.

本项目是一个本地 MVP Web App，用 FastAPI + Jinja2 封装足球赛事赛前推演内容生产流程。当前版本保留确定性 `source=demo` fallback，并在 Phase 9 增强结构化 `prediction.json`、数据质量评级和预测 artifact API。

## 启动

首次使用可以先生成本机配置并运行体检：

```bash
scripts/setup.sh
```

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
```

也可以使用脚本启动：

```bash
scripts/setup.sh
scripts/start.sh
PORT=8788 scripts/start.sh
```

打开 `http://127.0.0.1:8787/`。

## 测试

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
scripts/doctor.sh
scripts/smoke.sh
```

接口验收：

```bash
curl http://127.0.0.1:8787/api/matches
curl http://127.0.0.1:8787/api/skill/status
curl http://127.0.0.1:8787/api/system/doctor
curl http://127.0.0.1:8787/api/system/setup-guide
curl -X POST http://127.0.0.1:8787/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"match_id":"demo-001","theme":"dark"}'
curl -X POST http://127.0.0.1:8787/api/odds/fetch \
  -H 'Content-Type: application/json' \
  -d '{"nums":"086 087,088","dry_run":true,"out_path":"/tmp/wc_odds.json"}'
curl -X POST http://127.0.0.1:8787/api/odds/inspect \
  -H 'Content-Type: application/json' \
  -d '{"odds_path":"/tmp/wc_odds.json"}'
curl -X POST http://127.0.0.1:8787/api/odds/discover \
  -H 'Content-Type: application/json' \
  -d '{"nums":"086 087,088","timeout":60}'
curl -X POST http://127.0.0.1:8787/api/reports/build \
  -H 'Content-Type: application/json' \
  -d '{"odds_path":"/tmp/wc_odds.json","out_path":"/tmp/wc_report.html","title":"世界杯数据推演报告","theme":"dark","dry_run":true}'
curl -X POST http://127.0.0.1:8787/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"nums":"086 087,088","title":"世界杯数据推演报告","theme":"dark","dry_run":true,"timeout":60}'
curl -X POST http://127.0.0.1:8787/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"nums":"086 087,088","title":"世界杯数据推演报告","theme":"dark","dry_run":false,"background":true,"timeout":60}'
curl http://127.0.0.1:8787/api/runs
curl http://127.0.0.1:8787/api/runs/queue
curl http://127.0.0.1:8787/api/runs/failures
curl -X POST http://127.0.0.1:8787/api/runs/recover
curl -X POST http://127.0.0.1:8787/api/runs/<run_id>/retry
curl -X POST http://127.0.0.1:8787/api/runs/<run_id>/cancel
curl http://127.0.0.1:8787/api/runs/<run_id>/prediction
curl -OJ http://127.0.0.1:8787/api/runs/<run_id>/export.zip
```

## 外部用户安装与体检

首次使用建议按下面顺序安装、启动、检查：

```bash
scripts/setup.sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
scripts/doctor.sh
scripts/start.sh
```

`.env.example` 记录可配置项；`scripts/setup.sh` 会在 `.env` 缺失时复制它。复制为 `.env` 后，`scripts/start.sh` 和 `scripts/doctor.sh` 会自动加载：

- `WC_APP_NAME`
- `WC_DATA_PATH`
- `WC_RUNS_PATH`
- `WC_SKILL_PATH`
- `WC_MAX_RUN_MATCHES`
- `WC_MAX_CONCURRENT_RUNS`
- `WC_DEFAULT_COMMAND_TIMEOUT`

`scripts/doctor.sh` 会优先使用 `.venv/bin/python`，不存在时使用 `python3`，然后执行 `python -m app.runtime_doctor`。输出为格式化 JSON；`ok=true` 时退出码为 0，`ok=false` 时退出码为 1。

缺少 `WC_SKILL_PATH` 对应 skill 不影响 demo fallback，但真实抓取/报告模式需要 skill scripts。

运行中的服务也提供同一份诊断和首次启动指南：

```bash
curl http://127.0.0.1:8787/api/system/doctor
curl http://127.0.0.1:8787/api/system/setup-guide
```

体检覆盖 Python 版本、项目关键文件、`runs/` 目标路径、配置值、Hermes skill 路径、skill 脚本、启动/冒烟脚本可执行权限，以及 runs 父目录写权限。任一 `fail` 为 `not_ready`；只有 `warn` 且无 `fail` 为 `degraded`；全部通过为 `ready`。Hermes skill 路径缺失只会返回 `warn` 并进入 `degraded`，因为 demo fallback 仍可运行；项目文件或启动脚本缺失才是 `not_ready`。

`GET /api/system/setup-guide` 返回 `status`、`steps`、`config`、`missing` 和 `commands`，用于首次启动面板和外部用户排查。`WC_SKILL_PATH` 缺失不是致命错误；demo fallback 仍可运行，真实模式才需要 skill 下的脚本。

## 多用户账号系统

当前版本支持 SQLite-backed 多用户 API token 账号，并在 Web 页面提供 Token 输入框：

- 用户表、角色、plan、run_quota 存在 `WC_DB_PATH` 指向的 SQLite DB。
- Admin 创建用户：`POST /api/admin/users`，返回一次性明文 token（请立即保存）。
- Admin 管理用户：`PATCH /api/admin/users/{user_id}` 可更新 role/plan/run_quota/active，`POST /api/admin/users/{user_id}/reset-token` 会重置 token 并只返回一次明文。
- 当前用户：`GET /api/me`。
- 用户请求带 HTTP Header `X-API-Token`；浏览器可在首页“账号 Token”面板保存到本机 localStorage。
- 用户存在后，真实 run 按用户 quota 限制；dry-run 仍会记录用量。
- 普通用户只能列出、查看、重试、取消、导出自己的 run；admin 可查看全量 run。
- Admin 接口需要 `role=admin`。
- 若数据库还没有用户，则兼容旧的单机 bootstrap 模式；设置 `WC_API_TOKEN` 可继续用系统 token。

示例：

```bash
# 首个用户可在空库 bootstrap 模式下创建为 admin；后续 admin 接口都要带 admin token。
curl -X POST http://127.0.0.1:8787/api/admin/users \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","role":"admin","plan":"internal","run_quota":1000}'

curl http://127.0.0.1:8787/api/me -H 'X-API-Token: REPLACE_WITH_TOKEN'

curl -X POST http://127.0.0.1:8787/api/runs \
  -H 'X-API-Token: REPLACE_WITH_TOKEN' \\
  -H 'Content-Type: application/json' \
  -d '{"nums":"086","title":"世界杯数据研究报告","theme":"dark","dry_run":true}'
```

## 商业化与部署配置

Phase 13-17 增加了普通用户/商业化前置能力，不包含小红书或社媒内容生成：

- 数据可信度：生成结果会暴露 `data_trust`，说明来源、评级、缺失盘口和限制。
- SQLite run index：默认 `WC_DB_PATH=./data/app.db`，可重建，文件 artifact 仍是内容源。
- 历史筛选：`GET /api/runs?status=&num=&quality=&q=`。
- Admin：`/api/admin/users`、`/api/admin/usage`、`/api/admin/run-index`、`/api/admin/run-index/rebuild`。
- 安全：默认只绑定 `127.0.0.1`；有用户账号后，写操作和 admin 接口要求用户 `X-API-Token`；无用户账号时可设置 `WC_API_TOKEN` 作为兼容系统 token。
- 配额：用户级 `plan/run_quota` 控制真实 run 数量；无用户账号时由 `WC_PLAN`、`WC_RUN_QUOTA` 控制系统配额。暂不接支付。

Docker 本地试跑：

```bash
docker build -t worldcup-ai-content-engine .
docker run --rm -p 8787:8787 --env-file .env worldcup-ai-content-engine
```

发布前检查见 `RELEASE_CHECKLIST.md`。

## 合规边界

这是体育数据推演与内容生产工具，不是交易导向平台。输出必须强调：

- 概率推演
- 数据观察
- 娱乐研究
- 风险提示

`app/compliance.py` 会执行合规扫描并返回 `failed` 状态；调用方不应抛未处理异常。

## Phase 2 skill bridge

`app/skill_bridge.py` 只读检查 Hermes skill 路径和稳定脚本，不导入 skill 内部模块，不修改 `~/.hermes` 源码：

默认路径为 `~/.hermes/skills/leisure/worldcup2026-betting-analyst`，可通过 `WC_SKILL_PATH` 覆盖。

`app/sporttery_service.py` 和 `app/report_service.py` 只负责构造安全命令与受控执行：

- 赔率 dry-run：`python3 <skill>/scripts/fetch_sporttery.py odds --nums ...`
- 报告 dry-run：`python3 <skill>/scripts/gen_multi_market_report.py --odds ... --out ... --title ... --theme ...`
- Web API 默认 `dry_run=true`，只返回将执行的命令；只有显式传 `dry_run=false` 才会 `subprocess.run`
- 执行时不使用 `shell=True`，启用 `capture_output=True` 和 timeout；skill/script 不存在时返回 graceful failed dict

接入顺序：

1. 只读加载 skill 的稳定脚本或数据文件，不修改 `~/.hermes` 源码。
2. 将真实引擎输出映射到当前报告结构：`match`、`probabilities`、`score_candidates`、`market_notes`、`risk_flags`。
3. 保留 demo fallback；skill 路径不存在或真实调用失败时仍可展示 MVP。
4. 所有内容进入页面或 API 前都走合规扫描。

## Phase 4 run workflow

`app/run_manager.py` 在项目内 `runs/` 目录创建一次性 run 记录。每个 run 使用 `YYYYMMDDTHHMMSSZ-xxxxxx` 形式的 ID，并写入：

- `request.json`：`nums`、`title`、`theme`、`dry_run`、`timeout`、`created_at`
- `log.json`：每步命令或执行结果、safety 信息、耗时，以及 `dry_run`、`failed`、`partial`、`succeeded` 状态
- `odds.json`：仅在显式 `dry_run=false` 且抓取步骤成功时生成
- `report.html`：仅在显式 `dry_run=false` 且报告步骤成功时生成

安全护栏：

- 单次最多 8 场，编号必须是 3 位数字。
- 主题限制为 `dark`、`purple`、`blue`。
- 命令 timeout 默认 60 秒，可在 `POST /api/runs` 中传入 `timeout` 覆盖。
- `odds.json`、`odds.valid.json` 和 `report.html` 只写入对应 run 目录，不接受外部输出路径。
- 抓取返回成功但 `odds.json` 缺失时，run 标记为 `partial` 并在 log 记录 warning。
- 报告存在时，API 返回 `report_url`，首页历史列表可直接打开报告。

## Phase 5 odds health gate

`app/odds_health.py` 会检查 `odds.json` 的 `matches` 数据，并返回：

- `ok`：是否至少有一个有效场次
- `valid_count` / `invalid_count`：有效与不可用场次数
- `valid_nums` / `invalid`：可用于报告的编号与不可用原因
- `markets`：每个有效场次的市场字段可用情况
- `summary`：中文健康摘要

有效场次定义为：match 是 object、没有 `error`，且包含 `主队` 与 `客队`。

真实 run 在抓取成功后先执行 health gate：

- 全部不可用：状态为 `partial_no_valid_matches`，不调用报告脚本，避免报告生成阶段崩溃。
- 部分有效：保留原始 `odds.json`，另写 `odds.valid.json`，只把有效场次交给报告脚本。
- 全部有效：同样写 `odds.valid.json`，日志记录 `source_odds_path` 与 `report_odds_path`。

首页历史 run 列表会显示有效/不可用数量；创建 run 后会显示 health summary。报告存在时可打开新页面，也可在当前页面内预览。

新增 API：

- `POST /api/odds/inspect`：读取项目目录或临时目录内的 odds 文件并返回 health
- `POST /api/runs`：创建本地 run，默认 `dry_run=true`
- `GET /api/runs`：按创建时间倒序返回历史 run
- `GET /api/runs/{run_id}`：查看 request、log 和 artifact 状态
- `GET /api/runs/{run_id}/odds-health`：查看 run 的 odds health
- `GET /runs/{run_id}/report.html`：报告文件存在时返回 HTML，否则 404

启动后可在首页“创建本地 Run”表单选择“生成 Dry Run”或“执行真实流程”，也可使用上面的 `curl /api/runs` 命令。真实执行仍默认关闭，只有请求体显式传入 `"dry_run": false` 才会调用底层脚本。

## Phase 6 background queue and discovery

`POST /api/runs` 继续默认同步兼容旧行为。请求体传入 `"background": true` 且 `"dry_run": false` 时，会先创建 run 目录、写入 `request.json` 与 `log.json`，并立即返回 `queued` 状态；后台线程随后更新同一份 `log.json`：

- `queued`
- `running_fetch`
- `running_report`
- `succeeded`
- `partial_no_valid_matches`
- `partial`
- `failed`
- `dry_run`

`GET /api/runs/{run_id}` 会读取当前 `log.json`，可用于轮询后台执行状态。后台队列是进程内标准库 queue/thread 实现，不依赖 Celery、Redis 或新包。

新增 `POST /api/odds/discover` 用于真实检查场次可用性。它把 odds 抓取到临时文件，使用同一套 health gate 返回 `valid_nums`、`invalid`、`markets` 和 `summary`，不会创建 run。抓取失败时返回 `ok=false` 与结构化 `error`。

脚本：

- `scripts/start.sh`：创建或复用 `.venv`，按需安装项目，然后启动 `uvicorn app.main:app`。
- `scripts/smoke.sh`：检查 `/api/matches`、`/api/skill/status` 和 dry-run `POST /api/runs`，失败时非零退出。

## Phase 7 retry, cancel and polling UI

新增 run 控制接口：

- `POST /api/runs/{run_id}/retry`：仅允许 `failed`、`partial`、`partial_no_valid_matches`、`cancelled` 状态重试。重试会创建新的 run 目录，并在新 `request.json` 与 `log.json` 中记录 `retry_of`，不会覆盖旧 run artifact。
- `POST /api/runs/{run_id}/cancel`：`queued` 状态会直接写入 `cancelled`、`cancelled_at` 和取消原因；`running_fetch` / `running_report` 会写入 `cancel_requested=true` 与 `cancel_requested_at`。当前设计不安全终止子进程，worker 会在下一阶段开始前观察取消请求并停止。

首页真实执行按钮现在传入 `"background": true`，创建后每秒轮询 `GET /api/runs/{run_id}`，并显示 `queued`、`running_fetch`、`running_report`、终态进度。可重试的终态显示重试按钮，可取消的运行态显示取消按钮。

首页新增“可用场次检查”面板，调用 `POST /api/odds/discover`，把可用编号和不可用编号分开展示。可用编号带复选框，选中后可写入创建 run 表单。

## Phase 8 queue recovery, failure dashboard and export

应用使用模块级 `RunManager` 复用进程内队列状态，并在启动时执行一次恢复扫描。也可以手动调用：

- `POST /api/runs/recover`：扫描 `runs/*/log.json`。`queued` 会重新入队；旧进程遗留的 `running_fetch` / `running_report` 会标记为 `failed`，并写入 `error.code="interrupted"`。已终止状态不会被修改。
- `GET /api/runs/queue`：返回 `queued_count`、`active_count`、`max_concurrent_runs`、`queued_run_ids`、`active_run_ids`。默认并发上限为 1，后台真实 run 顺序执行。
- `GET /api/runs/failures`：按分类聚合失败、部分完成、取消和中断 run，并返回最近记录。分类包括 `script_unavailable`、`fetch_failed`、`odds_missing`、`no_valid_matches`、`report_missing`、`cancelled`、`interrupted`、`unknown`。
- `GET /api/runs/{run_id}/export.zip`：导出当前可用 artifact，包含 `manifest.json`，以及存在的 `request.json`、`log.json`、`odds.json`、`odds.valid.json`、`report.html`。即使没有报告也可以导出已有文件。

首页 run 区域会显示队列状态、失败分类概览、最近失败摘要，并为每个 run 提供 ZIP 导出链接。

## Phase 9 structured prediction artifact

成功生成报告的真实 run 会额外写入 `prediction.json`。它是面向产品层消费的结构化预测 artifact，不从 HTML 反解析模型概率，本阶段只沉淀 odds health、有效场次、市场信号、数据质量与合规定位：

- `schema_version`、`run_id`、`generated_at`
- `source`：`odds.json`、`odds.valid.json`、`report.html` 路径与 `source_type`
- `data_quality`：`grade=A/B/C/D`、`status=publishable/internal_reference/insufficient`、`score`、`missing`、`signals`
- `matches`：每场编号、主客队、市场可用性、单场质量缺口
- `compliance`：固定定位为体育数据推演与娱乐研究，不构成下注建议

新增 API：

- `GET /api/runs/{run_id}/prediction`：返回 parsed `prediction.json`；artifact 不存在时 404。
- `GET /api/runs/{run_id}` 和 `GET /api/runs` 会暴露 `data_quality` 与 `prediction_exists`，前端历史列表显示质量等级，并提供 `prediction.json` 链接。
- `GET /api/runs/{run_id}/export.zip` 在存在时自动包含 `prediction.json`。

## Phase 19 deployment package and first external trial

Phase 19 增加部署打包与首个真实外部用户试用流程：

- `scripts/package_release.sh`：生成 `dist/worldcup-ai-content-engine-v<version>-<timestamp>.tar.gz` 与 `.sha256`，只包含源码、demo 数据、脚本、测试和文档。
- `scripts/external_trial_smoke.py`：对已启动服务执行首个外部用户试用冒烟，覆盖 doctor、admin/user token、非 admin 禁访、dry-run、export.zip。
- `EXTERNAL_TRIAL.md`：外部试用安装、安全边界、首测步骤和反馈记录模板。
- 安全边界：默认 `WC_HOST=127.0.0.1`；非 localhost 暴露必须设置 `WC_API_TOKEN`，`scripts/start.sh` 与 runtime doctor 都会检查。

```bash
scripts/package_release.sh
shasum -a 256 -c dist/worldcup-ai-content-engine-v*.tar.gz.sha256
BASE_URL=http://127.0.0.1:8787 scripts/external_trial_smoke.py
```

## Desktop unsigned Beta release pipeline

Task 5 adds local source for a secure Desktop unsigned Beta pipeline. It is source-only in this workspace: no GitHub repo is created, no workflow is run, and no artifact is published locally.

- `.github/workflows/desktop-release.yml` is manual `workflow_dispatch` only and creates a **Draft GitHub Release** with CI-built Windows NSIS and macOS DMG artifacts.
- Native CI matrix: Windows x86_64, macOS Apple Silicon, and macOS Intel. The Python PyInstaller sidecar is built before Tauri/Cargo so Tauri can find the required target-suffixed external binary.
- `scripts/package_desktop_source.py` creates deterministic `worldcup-ai-content-engine-source.tar.gz` for release aggregation, and can still create versioned local review archives. It excludes `.env`, `data/app.db`, `runs/`, build directories, Tauri targets, sidecar binaries, and release outputs.
- `desktop/scripts/package_desktop_release.py` normalizes CI installer names to `足球赛事AI推演引擎-Setup-x64.exe`, `足球赛事AI推演引擎-macOS-AppleSilicon.dmg`, and `足球赛事AI推演引擎-macOS-Intel.dmg` and includes `INSTALL_BETA.md` beside each installer.
- `scripts/write_checksums.py` writes deterministic SHA-256 manifests for collected release files and refuses obvious runtime secret/data paths.
- `scripts/create_release_notes.py` creates deterministic Draft GitHub Release notes from the combined `release-assets/` directory.
- `desktop/INSTALL_BETA.md` documents manual unsigned Beta installation. Updates are **manual GitHub Release update** only; **automatic signed updater is later** and is not claimed to work in this stage.

Desktop package metadata avoids official tournament affiliation language; PitchMind is the internal publisher/project owner name.

## Phase 10 external user setup and runtime doctor

Phase 10 增加外部用户可安装、可诊断、可运行的最小 operability 能力：

- `app/runtime_doctor.py`：无副作用检查运行环境，并返回 `ok`、`status`、`checks`、`summary`。
- `GET /api/system/doctor`：返回 runtime doctor JSON，供 UI 或外部健康检查调用。
- `scripts/doctor.sh`：命令行体检入口，按 doctor `ok` 决定退出码。
- 首页新增“系统体检 / Runtime doctor”面板，直接渲染 doctor JSON。

状态规则：

- 任一 `fail` => `not_ready`，`ok=false`
- 无 `fail` 但有 `warn` => `degraded`，`ok=true`
- 全部 `pass` => `ready`，`ok=true`

缺少 Hermes skill 或 skill 脚本是 `warn`，不会阻止 demo fallback。合规边界不变：只输出概率推演、数据观察、娱乐研究和风险提示。
