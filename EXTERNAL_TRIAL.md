# 首个真实外部用户试用流程（Phase 19）

目标：把本地产品交给第一个外部试用用户前，用最小安全边界跑通“安装 → 启动 → 创建用户 → 生成 dry-run → 导出 zip”。

## 1. 打包

```bash
scripts/package_release.sh
shasum -a 256 -c dist/worldcup-ai-content-engine-v*.tar.gz.sha256
```

打包脚本只包含源码、demo 数据、脚本、测试和文档；明确排除：

- `.env` / 真实 token
- `data/app.db` / 用户 token hash 与用量
- `runs/` / 历史报告 artifact
- `dist/` / 旧发布包
- cache / `__pycache__`

## 2. 试用机器安装

```bash
tar -xzf worldcup-ai-content-engine-v*.tar.gz
cd worldcup-ai-content-engine-v*
scripts/setup.sh
scripts/doctor.sh
scripts/start.sh
```

默认只监听 `127.0.0.1`。优先建议通过 SSH/Tailscale tunnel 给外部用户试用，不直接公网暴露。

## 3. 非 localhost 暴露安全边界

如果必须监听 `0.0.0.0`：

```bash
export WC_HOST=0.0.0.0
export WC_API_TOKEN='replace-with-a-long-random-token'
scripts/start.sh
```

`runtime_doctor` 与 `scripts/start.sh` 都会阻止“非 localhost 且无 `WC_API_TOKEN`”的启动方式。

## 4. 创建试用用户并跑首测

启动服务后运行：

```bash
BASE_URL=http://127.0.0.1:8787 scripts/external_trial_smoke.py
```

如果服务器已经有用户，必须提供 admin token：

```bash
ADMIN_TOKEN='wc_...' BASE_URL=http://127.0.0.1:8787 scripts/external_trial_smoke.py
```

脚本会验证：

1. `/api/system/doctor` 可访问。
2. 创建或使用 admin。
3. 创建 trial user，并只显示一次明文 token。
4. trial user 可访问 `/api/me`。
5. trial user 不能访问 admin users。
6. trial user 可创建 dry-run。
7. trial user 可导出自己的 `export.zip`。

## 5. 交给外部用户的话术

- 这是“体育数据推演 / 内容研究工具”，不是下注建议。
- 首轮只跑 dry-run，确认安装、账号、导出链路没问题。
- 真实赔率抓取依赖 `WC_SKILL_PATH` 指向的 Hermes skill；缺失时 demo fallback 仍可体验产品流程。
- 用户 token 只显示一次；丢失后由 admin reset-token。

## 6. 试用反馈记录

建议记录：

- 安装是否卡住（Python、venv、依赖、端口）。
- 首屏是否能看懂三步流程。
- Token 输入是否理解。
- dry-run 生成与导出是否成功。
- 数据可信度与风险提示是否足够清楚。
- 是否有误解为“下注推荐”的风险。
