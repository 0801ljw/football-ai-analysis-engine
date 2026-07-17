[English](../../README.md) / [简体中文](README.zh-CN.md) / [日本語](README.ja.md) / [한국어](README.ko.md)

# PitchMind — 足球 AI 分析引擎

![PitchMind 品牌封面](../assets/pitchmind-hero.png)

**PitchMind 把足球赛事研究整理成一个本地优先的桌面流程：收集比赛上下文、生成 AI 辅助分析、核对证据并导出报告，同时不把你的私有 token 或本地 run 数据发送到托管产品。**

[下载公开 Beta 4](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4) · [产品导览](#产品导览) · [开发者文档](../DEVELOPMENT.md)

> 合规边界：PitchMind 仅用于研究、学习与娱乐，不构成投注建议、金融建议，也不承诺任何比赛结果。

## 可用桌面 Beta

**最新公开预发布版：** [`desktop-beta-4`](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)

**最新自动 CI Draft：** `desktop-beta-8` 用于证明草稿发布自动化链路，不作为普通用户的直接下载入口。

| 平台 | 状态 | 公开 Beta 4 资产文件 |
| --- | --- | --- |
| Windows x64 | 可用 | `PitchMind-Setup-x64.exe` |
| macOS Apple Silicon | 可用 | `PitchMind-macOS-AppleSilicon.dmg` |
| macOS Intel | 可用 | `PitchMind-macOS-Intel.dmg` |

当前 Beta 未签名。安装时操作系统可能显示安全警告。请只从上方官方 GitHub Release 下载；如发布页附带校验文件，请核对资产名与校验和；不要安装镜像站或他人重新上传的文件。

## 产品导览

![PitchMind 产品导览](../assets/pitchmind-product-tour.png)
## 3 步开始使用

1. 打开 [`desktop-beta-4` 发布页](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)，下载与你的平台匹配的安装包。
2. 安装并启动 PitchMind。由于这是未签名 Beta，只有在确认文件来自官方发布页时，才继续通过系统安全提示。
3. 创建一个本地 run，查看数据质量说明与报告内容；如需分享研究结果，可导出可用 artifact。

## 核心能力

| 方向 | PitchMind 能帮助你完成的事 |
| --- | --- |
| 赛事研究 | 在一个本地工作区整理足球场次编号、数据源状态和分析 run。 |
| AI 辅助报告 | 生成结构化足球分析报告，并附带证据说明、可用时的 prediction JSON 与合规提醒。 |
| 历史记录与导出 | 查看历史 run、状态、报告 artifact 和可导出的结果。 |
| 本地优先隐私 | 配置、token、本地数据库和生成的 run 文件保留在你自己的电脑上。 |
| 安全边界 | 在产品流程中明确未签名 Beta 状态，并提醒输出仅用于研究与娱乐。 |

## 已验证历史表现

以下数据由 102 条 raw ledger 记录筛选为 86 场 clean 赛前样本后重建。胜平负准确率使用 clean 样本；精确比分 Top 3 覆盖率按历史 `lh`/`la` 与当前 `score_matrix` 评分方法重新计算。这些数据用于呈现模型评估证据，不代表未来比赛结果承诺。

![PitchMind 已验证历史表现数据图](../assets/pitchmind-performance.svg)

| 评估口径 | 结果 |
| --- | ---: |
| Raw ledger 记录 | 102 场 |
| 有真实赛前快照的 clean 样本 | 86 场 |
| 胜平负方向准确率 | **64/86（74.4%）** |
| 精确比分 Top 3 覆盖率 | **33/86（38.4%）** |

以下为开赛前已归档的精确比分命中案例：

| 比赛 | 赛前模型比分 | 实际比分 | 命中 |
| --- | --- | ---: | --- |
| 阿根廷 vs 奥地利 | **2:0** / 1:0 / 3:0 | **2:0** | Top 1 |
| 法国 vs 伊拉克 | **3:0** / 2:0 / 4:0 | **3:0** | Top 1 |
| 巴西 vs 海地 | **3:0** / 4:0 / 5:0 | **3:0** | Top 1 |
| 法国 vs 瑞典 | **3:0** / 4:0 / 2:0 | **3:0** | Top 1 |
| 美国 vs 波黑 | **2:0** / 3:0 / 2:1 | **2:0** | Top 1 |
| 葡萄牙 vs 克罗地亚 | **2:1** / 1:1 / 3:1 | **2:1** | Top 1 |
| 西班牙 vs 奥地利 | 2:0 / **3:0** / 1:0 | **3:0** | Top 3 |
| 瑞士 vs 阿尔及利亚 | 1:1 / 2:1 / **2:0** | **2:0** | Top 3 |

上表是精选成功案例。评估引擎应以包含命中和失误的整体准确率为准，而不是只看个别漂亮赛果。

## 发布质量证据

| 证据 | 状态 |
| --- | --- |
| 自动化测试 | 发布质量门禁中 146 项测试通过。 |
| 原生桌面 CI | Windows x64、macOS Apple Silicon、macOS Intel 三条发布任务产出平台安装包。 |
| 发布资产 | 公开 Beta 4 提供安装包，并在发布页附带校验/发布材料（如 `SHA256SUMS.txt`）。 |
| 本地优先边界 | 当前未签名 Beta 阶段不声称云同步、远程遥测或自动签名更新。 |

## 隐私与未签名 Beta 安全

- PitchMind 设计为在你的电脑本地运行。
- 寻求支持时，不要发送 API token、账号 token、`.env` 文件、本地数据库或 run artifact。
- 浏览器或桌面端 token 输入仅用于你的本地流程。请把 token 当作密钥保管。
- 当前桌面 Beta 尚未代码签名，也不声称支持自动更新。如果你不接受未签名预览软件的风险，请等待后续签名版本。

## 反馈

请在 [GitHub Issues](https://github.com/0801ljw/football-ai-analysis-engine/issues) 反馈 bug、安装问题和易用性建议。请附上操作系统、下载的资产文件名以及问题描述。不要包含 token 或本地私有数据。

## 技术与开发者入口

| 层级 | 技术 |
| --- | --- |
| 桌面外壳 | Tauri |
| 本地 Web 应用 | FastAPI, Jinja2 |
| 前端资源 | HTML, CSS, JavaScript |
| 运行时与工具 | Python, SQLite, PyInstaller sidecar, 发布打包脚本 |
| 发布目标 | GitHub Releases，手动未签名 Beta 分发 |

开发者入口：

- [开发者文档](../DEVELOPMENT.md)
- [桌面 Beta 安装说明](../../desktop/INSTALL_BETA.md)
- [发布检查清单](../../RELEASE_CHECKLIST.md)
- [桌面源码 README](../../desktop/README.md)

## 法律与合规提醒

PitchMind 提供足球数据研究、概率式探索和内容生产辅助，用于娱乐和学习。它不提供投注建议、不保证预测结果，也不指导下注。请始终遵守你所在地法律和相关平台规则。
