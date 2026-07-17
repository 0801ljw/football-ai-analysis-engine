# PitchMind GitHub Product Page Refresh Design

## Goal

把 GitHub 首页从开发项目说明升级为可信、可下载、可看懂的桌面产品入口，同时保留开发者文档与历史证据。

## Approved direction

采用「真实产品优先」的信息架构，不使用 AI 虚构界面：

1. 四语切换。
2. 品牌 Hero。
3. 一句话价值主张与 Download / Product Tour / Developer Docs 三个主入口。
4. Windows x64、macOS Apple Silicon、macOS Intel 三平台状态。
5. 三张真实界面产品图：主工作台、报告详情、历史与导出。
6. 三步使用流程。
7. 核心能力与本地优先隐私边界。
8. 可审计的历史表现：全量聚合指标优先，精选案例明确标注。
9. 发布验收证据、技术栈、开发者入口、合规说明。

## Visual system

- 延续现有深蓝科技品牌，不更换产品视觉语言。
- 产品图来自真实运行页面，只做统一窗口框、标题与留白包装。
- README 图像全部存放在 `docs/assets/`，无远程字体或图片依赖。
- Social Preview 使用 1280×640；历史表现 Dashboard 使用 1280×760。
- 四语 README 共享产品图和指标图，分别提供本地化 alt 文本与说明。

## Repository hygiene

- 把根目录的阶段任务、Codex 任务和外部试用材料移动到 `docs/archive/development-phases/`，不删除内容。
- 根目录保留面向使用与开发的核心文件。
- 新增 `CONTRIBUTING.md`、`SECURITY.md` 和 Issue templates。
- 不擅自选择开源许可证；未得到明确授权前不新增 LICENSE。

## Release truth

- 公开可直接下载版本仍以已发布的 `desktop-beta-4` 为准；它已包含三平台安装包。
- `desktop-beta-8` 是自动生成的 Draft，用于证明 CI 自动化闭环，不作为普通用户下载入口。
- README 必须区分「Latest public prerelease」与「Latest automated draft」。

## Verification

- 真实启动 App，浏览器捕获三个真实状态。
- 校验图片尺寸、SVG XML、README 相对链接和四语状态一致。
- 历史指标必须从权威 ledger/赛前归档重新对账；无法重算的指标不得沿用旧数字。
- 运行全量 pytest、pip check、desktop config verifier、Markdown 链接检查、合规/secret 扫描和 `git diff --check`。
- 本地预览完成后再 commit/push；GitHub About、Topics、Social Preview 属外部操作，发布前回读验证。