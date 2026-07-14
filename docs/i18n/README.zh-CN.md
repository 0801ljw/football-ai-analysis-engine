[English](../../README.md) / [简体中文](README.zh-CN.md) / [日本語](README.ja.md) / [한국어](README.ko.md)

# PitchMind — 足球 AI 分析引擎

![PitchMind 品牌封面](../assets/pitchmind-hero.png)

**PitchMind** 是一个 local-first（本地优先）的桌面 Beta，用于足球赛事研究、AI 辅助分析与结构化报告生成。它面向普通用户，提供专注的研究工作台，同时避免把私有 token 或本地 run 数据发送到托管服务。

> 合规边界：PitchMind 仅用于研究与娱乐，不构成投注建议、金融建议，也不承诺任何比赛结果。

## 下载桌面 Beta

**最新 Beta：** [`desktop-beta-4`](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)

| 平台 | 状态 | 资产文件 |
| --- | --- | --- |
| Windows x64 | 可用 | `PitchMind-Setup-x64.exe` |
| macOS Apple Silicon | 可用 | `PitchMind-macOS-AppleSilicon.dmg` |
| macOS Intel | 暂不可用 | 本次发布没有 Intel DMG |

当前 Beta 未签名。安装时操作系统可能显示安全警告。请只从上方官方 GitHub Release 下载，不要安装镜像站或他人重新上传的文件。

## 你可以用它做什么

| 方向 | PitchMind 能帮助你完成的事 |
| --- | --- |
| 赛事研究 | 在一个本地工作区整理足球场次编号、数据源状态和分析 run。 |
| AI 辅助报告 | 生成结构化足球分析报告，并附带数据质量说明与合规提醒。 |
| 历史记录 | 查看历史 run、状态、导出 artifact，以及可用时的 prediction JSON。 |
| 本地优先流程 | 配置、token 和生成的 run 文件保留在你自己的电脑上。 |
| 安全边界 | 明确展示未签名 Beta 提示，并提醒输出仅用于研究与娱乐。 |

## 3 步快速开始

1. 打开 [`desktop-beta-4` 发布页](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)，下载与你的平台匹配的安装包。
2. 安装并启动 PitchMind。由于这是未签名 Beta，只有在确认文件来自官方发布页时，才继续通过系统安全提示。
3. 创建一个本地 run，查看数据质量说明；如需分享研究结果，可导出可用 artifact。

## 隐私与本地优先使用

- PitchMind 设计为在你的电脑本地运行。
- 寻求支持时，不要发送 API token、账号 token、`.env` 文件、本地数据库或 run artifact。
- 浏览器或桌面端 token 输入仅用于你的本地流程。请把 token 当作密钥保管。
- 本 README 不声称存在远程遥测、云同步或自动更新能力。

## 未签名 Beta 安全提示

当前桌面 Beta 尚未代码签名，也不声称支持自动更新。Windows 或 macOS 对未签名预览软件弹出安全提示是预期行为。如果你不接受这类风险，请等待后续签名版本。

## 反馈与 Issue

请在 [GitHub Issues](https://github.com/0801ljw/football-ai-analysis-engine/issues) 反馈 bug、安装问题和易用性建议。请附上操作系统、下载的资产文件名以及问题描述。不要包含 token 或本地私有数据。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 桌面外壳 | Tauri |
| 本地 Web 应用 | FastAPI, Jinja2 |
| 前端资源 | HTML, CSS, JavaScript |
| 运行时与工具 | Python, SQLite, PyInstaller sidecar, 发布打包脚本 |
| 发布目标 | GitHub Releases，手动未签名 Beta 分发 |

## 开发者入口

本首页面向普通用户。旧版开发者 README 已按原样保留：

- [开发者文档](../DEVELOPMENT.md)
- [桌面 Beta 安装说明](../../desktop/INSTALL_BETA.md)
- [发布检查清单](../../RELEASE_CHECKLIST.md)
- [桌面源码 README](../../desktop/README.md)

## 法律与合规提醒

PitchMind 提供足球数据研究、概率式探索和内容生产辅助，用于娱乐和学习。它不提供投注建议、不保证预测结果，也不指导下注。请始终遵守你所在地法律和相关平台规则。
