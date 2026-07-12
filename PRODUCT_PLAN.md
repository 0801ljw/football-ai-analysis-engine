# 产品规划

## MVP

目标：本地可运行，完成产品壳、合规边界、demo 推演报告和 adapter 结构。

模块：

- FastAPI 路由：首页、报告页、`/api/matches`、`/api/generate`
- demo 数据：至少 3 场，全部标注 `source=demo`
- adapter：确定性 demo report，保留 Hermes skill path，支持 graceful fallback
- content renderer：生成中文标题、正文、话题
- compliance：合规扫描，失败返回状态，不抛未处理异常

验收标准：

- 本地 venv 可安装
- `pytest -q` 通过
- 两个 curl 验收接口返回 JSON
- 页面不出现产品禁用文案

## V1

目标：接入真实 Hermes worldcup2026 skill 的只读能力，保持 MVP API 不变。

Phase 2 已完成的基础能力：

- `SkillBridge` 只读描述 skill path、scripts path、data path 和关键脚本可用性。
- `SportteryService` 构造公开赔率抓取命令，支持编号解析、3 位数字校验和受控 subprocess 执行。
- `ReportService` 构造多市场报告生成命令，限制主题为 `dark/purple/blue`。
- Web API 提供 `/api/skill/status`、`/api/odds/fetch`、`/api/reports/build`。
- 真实执行接口默认关闭：请求模型默认 `dry_run=true`，前端当前只触发 dry-run。
- skill 不存在或脚本缺失时 graceful failed，不影响 demo fallback。

Phase 3 已完成的本地 run 闭环：

- `RunManager` 在项目内 `runs/` 创建独立 run 目录。
- 每个 run 保存 `request.json` 和 `log.json`，并预留 `odds.json`、`report.html` artifact 路径。
- dry-run run 只记录将执行的抓取与报告命令，不启动子进程。
- 显式关闭 dry-run 后，按顺序执行 odds 抓取和报告生成，并把每步结果写入 log。
- Web API 提供 `POST /api/runs`、`GET /api/runs`、`GET /api/runs/{run_id}`、`GET /runs/{run_id}/report.html`。
- 前端提供“创建本地 Run”表单和历史 run 列表，同时保留 Phase 2 命令构造表单。

Phase 4 已完成的真实执行与预览护栏：

- `RunManager` 继续同步执行，不引入后台队列。
- `POST /api/runs` 支持 `timeout`，默认 60 秒。
- 单次最多 8 场，编号沿用 3 位数字校验。
- 主题限制为 `dark/purple/blue`。
- run 输出路径固定为 `runs/<run_id>/odds.json` 和 `runs/<run_id>/report.html`。
- dry-run log 记录 safety 信息与预期 artifact 路径。
- 真实执行 log 记录 started_at、finished_at、duration_seconds。
- 抓取返回成功但 odds artifact 缺失时标记 `partial` 并写入 warning。
- 报告存在时 API 和首页历史列表返回可打开的 `report_url`。

Phase 5 已完成的数据健康闸门：

- 新增 `app/odds_health.py`，统一检查 `odds.json` 的 `matches` 数据。
- 有效场次定义为 match 是 object、没有 `error`，且包含 `主队` 与 `客队`。
- 抓取成功后先记录 `odds_health`，再决定是否进入报告生成。
- 全部不可用时状态为 `partial_no_valid_matches`，不调用报告脚本，避免不可用编号触发报告生成崩溃。
- 部分有效时保留原始 `odds.json`，另写 `odds.valid.json`，报告脚本只读取有效场次。
- 全部有效时也统一写入 `odds.valid.json`，日志记录 `source_odds_path` 与 `report_odds_path`。
- Web API 新增 `POST /api/odds/inspect` 与 `GET /api/runs/{run_id}/odds-health`。
- `GET /api/runs` 与 `GET /api/runs/{run_id}` 暴露 health 摘要，前端历史列表显示有效/不可用数量。
- 报告存在时前端支持打开报告和页面内预览。

Phase 6 已完成的后台队列、场次发现与脚本化启动：

- `POST /api/runs` 保持默认同步兼容；传入 `"background": true` 且 `"dry_run": false` 时立即创建 run 目录、写入 request/log，并返回 `queued`。
- 后台执行使用进程内标准库 queue/thread，不引入 Celery、Redis 或新依赖。
- run 状态扩展为 `queued`、`running_fetch`、`running_report`、`succeeded`、`partial_no_valid_matches`、`partial`、`failed`、`dry_run`。
- `GET /api/runs/{run_id}` 始终读取当前 `log.json`，可用于轮询后台 run 状态。
- 新增 `POST /api/odds/discover`，真实抓取 odds 到临时文件并复用 health gate 返回 `valid_nums`、`invalid`、`markets` 和 `summary`，不创建 run。
- discover 抓取失败时返回 `ok=false` 与结构化 `error`，不抛未处理异常。
- 新增 `scripts/start.sh`，自动创建或复用 `.venv`，按需安装项目，并启动 `127.0.0.1:${PORT:-8787}`。
- 新增 `scripts/smoke.sh`，检查 `/api/matches`、`/api/skill/status` 和 dry-run `POST /api/runs`，失败时非零退出。

Phase 7 已完成的失败重试、取消与前端轮询：

- 新增 `POST /api/runs/{run_id}/retry`，只允许 `failed`、`partial`、`partial_no_valid_matches`、`cancelled` 创建新 run。
- 重试复用原始 `nums`、`title`、`theme`、`dry_run`、`background`、`timeout`；真实非 dry-run 重试默认使用后台执行，并记录 `retry_of`。
- 新增 `POST /api/runs/{run_id}/cancel`，支持 queued run 直接取消并写入 `cancelled_at` 与原因。
- 运行中的 run 写入 `cancel_requested=true` 与 `cancel_requested_at`；worker 在 fetch 前和 report 前检查该标记，观察到后写入 `cancelled` 并停止后续阶段。
- 前端真实执行按钮默认创建后台 run，随后轮询 `GET /api/runs/{run_id}` 并显示 `queued`、`running_fetch`、`running_report`、终态进度。
- 前端按状态显示重试和取消按钮，重试会创建新的 run，不覆盖历史 artifact。
- 前端新增可用场次检查面板，调用 `POST /api/odds/discover`，展示可用/不可用编号，并可把选中的可用编号写入 run 表单。

Phase 8 已完成的队列恢复、并发限制、失败看板与导出：

- `RunManager` 支持模块级单例复用，应用启动时会扫描 `runs/*/log.json` 做一次恢复。
- `recover_pending_runs()` 会把 `queued` run 重新入队；旧进程遗留的 `running_fetch` / `running_report` 不自动重跑，而是标记为 `failed`，并写入 `error.code="interrupted"`，提示进程在完成前停止。终态 run 保持不变。
- 后台真实 run 默认 `max_concurrent_runs=1`，使用标准库 worker pool 控制并发；默认行为是顺序执行队列。
- 新增 `GET /api/runs/queue`，返回排队、运行中和并发上限统计。
- 新增 `GET /api/runs/failures`，按 `script_unavailable`、`fetch_failed`、`odds_missing`、`no_valid_matches`、`report_missing`、`cancelled`、`interrupted`、`unknown` 聚合失败或部分完成 run，并返回最近记录。
- 新增 `GET /api/runs/{run_id}/export.zip`，把已有的 `request.json`、`log.json`、`odds.json`、`odds.valid.json`、`report.html` 和 `manifest.json` 打包导出；没有报告时仍可导出已有 artifact。
- 前端 run 区域显示队列状态、失败分类概览、最近失败摘要，并给 run 历史和当前结果增加 ZIP 导出链接。

Phase 9 已完成的结构化预测 artifact 与数据质量评级：

- 成功生成报告的真实 run 会写入 `prediction.json`，作为产品层消费的结构化预测 artifact；本阶段不从 HTML 反解析模型概率，只沉淀 odds health、有效场次、市场信号、数据质量与合规定位。
- `prediction.json` schema 包含 `schema_version`、`run_id`、`generated_at`、`source`、`data_quality`、`matches`、`compliance`。
- `data_quality.grade` 使用 A/B/C/D，`status` 使用 `publishable`、`internal_reference`、`insufficient`；市场信号覆盖胜平负、让球、总进球、比分波胆、半全场。
- 新增 `GET /api/runs/{run_id}/prediction`，artifact 存在时返回 JSON，不存在时 404。
- `GET /api/runs` 与 `GET /api/runs/{run_id}` 暴露 `prediction_exists` 与 `data_quality`，前端显示质量等级并提供 `prediction.json` 链接。
- `GET /api/runs/{run_id}/export.zip` 在存在时自动包含 `prediction.json`。

Phase 10 已完成的外部用户安装、体检与运行诊断：

- 新增 `app/runtime_doctor.py`，无副作用检查 Python 版本、项目关键文件、runs 目标路径、配置值、Hermes skill 路径、skill 脚本、shell 脚本可执行权限和 runs 父目录写权限。
- 新增 `GET /api/system/doctor`，返回 `ok`、`status=ready/degraded/not_ready`、`checks` 和 `summary`，方便 UI、脚本和外部健康检查复用同一诊断结果。
- 新增 `scripts/doctor.sh`，优先复用 `.venv/bin/python`，不存在时使用 `python3` 执行 `python -m app.runtime_doctor`；`ok=true` 退出 0，`ok=false` 退出 1。
- 首页新增“系统体检 / Runtime doctor”面板，按钮调用 `/api/system/doctor` 并直接展示 JSON。
- 缺少 Hermes skill 路径只标记 `warn`，产品进入 `degraded` 但 demo fallback 仍可运行；项目关键文件、启动脚本、已存在 skill 下的必需脚本或 runs 父目录不可写会 `not_ready`。
- README 记录外部用户安装、启动、体检、API 诊断命令与 demo fallback 行为。

Phase 11 已完成的最小配置外置与首次启动指南：

- `app/config.py` 改为读取 `WC_APP_NAME`、`WC_DATA_PATH`、`WC_RUNS_PATH`、`WC_SKILL_PATH`、`WC_MAX_RUN_MATCHES`、`WC_MAX_CONCURRENT_RUNS`、`WC_DEFAULT_COMMAND_TIMEOUT`，不引入新依赖。
- 默认 skill 路径改为 `~/.hermes/skills/leisure/worldcup2026-betting-analyst`，仍可通过 `WC_SKILL_PATH` 覆盖；整数配置无效时回退默认值。
- 新增 `.env.example`、`scripts/setup.sh` 和 `GET /api/system/setup-guide`，首次启动可复制 `.env`、运行 doctor、启动服务并查看配置缺口。
- `scripts/start.sh` 和 `scripts/doctor.sh` 会自动加载 `.env`。
- 首页新增“首次启动指南”面板，调用 setup-guide endpoint 展示步骤、命令和当前配置。
- 缺少 skill path 不是 fatal；demo fallback 可用，真实模式才需要 skill scripts。

run 目录结构：

```text
runs/
  20260705T123456Z-a1b2c3/
    request.json
    log.json
    odds.json
    odds.valid.json
    report.html
    prediction.json
```

启动后创建默认 dry-run run：

```bash
curl -X POST http://127.0.0.1:8787/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"nums":"086 087,088","title":"世界杯数据推演报告","theme":"dark","dry_run":true,"timeout":60}'
```

后台真实执行 run：

```bash
curl -X POST http://127.0.0.1:8787/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"nums":"086 087,088","title":"世界杯数据推演报告","theme":"dark","dry_run":false,"background":true,"timeout":60}'
```

可用场次发现：

```bash
curl -X POST http://127.0.0.1:8787/api/odds/discover \
  -H 'Content-Type: application/json' \
  -d '{"nums":"086 087,088","timeout":60}'
```

重试或取消 run：

```bash
curl -X POST http://127.0.0.1:8787/api/runs/<run_id>/retry
curl -X POST http://127.0.0.1:8787/api/runs/<run_id>/cancel
```

队列恢复、失败概览和导出：

```bash
scripts/doctor.sh
curl -X POST http://127.0.0.1:8787/api/runs/recover
curl http://127.0.0.1:8787/api/system/doctor
curl http://127.0.0.1:8787/api/system/setup-guide
curl http://127.0.0.1:8787/api/runs/queue
curl http://127.0.0.1:8787/api/runs/failures
curl http://127.0.0.1:8787/api/runs/<run_id>/prediction
curl -OJ http://127.0.0.1:8787/api/runs/<run_id>/export.zip
```

模块边界：

- Engine Adapter：负责调用真实脚本、读取只读数据、异常降级
- Report Mapper：把真实概率、比分网格、风险层结果映射成产品 schema
- Compliance Gate：所有模型输出和内容文案统一扫描
- Source Metadata：记录数据来源、更新时间、是否 demo/fallback

数据源：

- Hermes skill 只读脚本与 JSON
- 官方公开赔率或用户提供数据
- 赛程、赛果、伤停、首发等外部数据的带时间戳快照

验收标准：

- skill 不存在时 demo 正常
- skill 存在时能返回真实引擎元信息
- 所有输出带来源和更新时间
- 真实输出仍通过合规扫描

## V2

目标：形成面向普通用户与商业化的赛前报告工作台（按 Boss 要求，当前商业化路线不包含小红书/社媒内容生成）。

商业化补全路线见 `COMMERCIALIZATION_PLAN.md`，按 Phase 12–17 逐一完成：

- Phase 12：普通用户三步式工作流 UI（选比赛 → 生成 → 预览/导出），高级 JSON/API 面板降级为高级工具。
- Phase 13：数据可信度与来源展示，明确 demo/fallback/真实脚本、数据时间、缺失盘口和限制。
- Phase 14：SQLite run index，保留文件 artifact 作为内容源，同时支持历史搜索/筛选/重建索引。
- Phase 15：部署/分发与安全边界，Docker 或等价安装流、非 localhost 暴露需显式 auth/config。
- Phase 16：商业化基础但暂不接支付，增加 plan/quota、usage tracking、admin/status 和 audit log。
- Phase 17：产品 polish/release checklist，错误态、空状态、首启引导、合规文案和最终回归。
- Phase 18：Admin 用户管理，支持 token preview、重置 token、禁用/启用用户和用户级配额状态。
- Phase 19：部署打包与首个真实外部用户试用流程，支持 release tarball、sha256、外部试用 smoke、安全暴露检查和试用反馈模板。

模块：

- 普通用户工作流
- 报告预览与导出
- 数据可信度分级与缺口提示
- 后台任务队列与缓存
- 历史记录搜索/筛选
- 安装部署与安全配置
- 用量/配额/审计基础

验收标准：

- 可批量生成多场报告
- 可区分 demo、快照、实时数据
- 失败任务可追踪、可重试
- 合规失败内容不会进入发布导出链路
- 普通用户无需理解 run/artifact/API 即可完成核心流程
- 商业化前置能力（配额、用量、审计、安全边界）可本地验证
