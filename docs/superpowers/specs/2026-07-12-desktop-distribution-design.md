# 足球赛事 AI 推演引擎：双端桌面版与发布设计

**状态：待用户审阅**  
**产品展示名：** 足球赛事 AI 推演引擎  
**内部品牌 / 未来商标：** 绿茵智擎  
**英文内部标识：** `pitchmind`  
**版本目标：** Desktop Beta 0.1

## 1. 目标

将现有本地 FastAPI/Jinja2 产品从“技术用户解压源码并运行脚本”的交付模式，升级为 Windows 与 macOS 用户可双击安装、首次打开自动完成运行环境初始化、可直接使用实时足球数据推演功能的桌面 App。

普通用户不需要自行安装 Python、Node.js、Hermes、虚拟环境或运行终端命令。

## 2. 产品与合规边界

### 对外展示

- App 名称、安装包名称、GitHub Release 标题、窗口标题均使用：**足球赛事 AI 推演引擎**。
- 桌面 App 图标、内部 package ID、代码命名和后续商标注册候选使用：**绿茵智擎 / PitchMind**。

### 固定合规声明

> 独立数据研究工具，与任何赛事组织方无官方关联；不构成任何投注建议或收益承诺。

### 禁止项

- 不使用 FIFA、世界杯、World Cup、赛事官方 Logo、奖杯、吉祥物、官方口号或任何暗示赛事授权的视觉资产。
- 不使用荐号、跟单、稳赢、盈利承诺等文案。
- 不向 GitHub、日志、安装包或远端更新源上传用户 API Key、本地 token、数据库和报告内容。

## 3. 支持范围

### Desktop Beta 0.1

| 平台 | 架构 | 发布物 |
|---|---|---|
| Windows 10/11 | x64 | NSIS `.exe` 安装器 |
| macOS | Apple Silicon (arm64) | `.dmg` |
| macOS | Intel (x64) | `.dmg` |
| 技术用户 | 源码 | `.tar.gz` + SHA-256 |

首版不覆盖 Linux、Windows ARM、移动端。

## 4. 架构

### 4.1 外层桌面壳

使用 **Tauri 2**：

- 提供原生窗口、应用菜单、系统目录定位、桌面安装器、更新器与自动启动协调。
- WebView 内加载现有工作台界面；优先复用当前 HTML/CSS/JS 的产品逻辑，避免为桌面版重写核心业务。
- Tauri 仅负责宿主和生命周期，不复刻 FastAPI 的业务规则。

### 4.2 Python Engine Sidecar

现有 FastAPI 应用及推演逻辑使用 PyInstaller 按目标平台打包为 sidecar：

- 不要求用户系统预装 Python。
- sidecar 随桌面 App 一起安装，不放在用户可编辑的工作目录。
- App 启动时由 Tauri 分配一个 localhost 随机可用端口，并启动 sidecar。
- sidecar 仅监听 `127.0.0.1` / `::1`，不自动暴露到局域网或公网。
- Tauri 等待 `/api/system/doctor` 与健康检查成功后再显示主工作台；失败时显示可读诊断与“导出诊断”按钮。

### 4.3 本地数据与安全边界

所有可变数据进入系统用户数据目录：

| 内容 | Windows | macOS |
|---|---|---|
| 应用数据 | `%APPDATA%/PitchMind/` | `~/Library/Application Support/PitchMind/` |
| 配置 | `config.json` | `config.json` |
| SQLite / 历史 run / 报告 | `data/`、`runs/` | `data/`、`runs/` |
| 运行日志 | `logs/` | `logs/` |

原则：

- 升级安装不得删除或覆盖用户数据。
- `WC_SKILL_PATH` 不再作为普通用户必须项；将运行所需的静态引擎代码与合法可分发数据内置。
- 用户自有 API Key 属于高级设置；当前 Beta 仅保存在本机用户配置 JSON（`api_key_storage_mode=local_json` / `local user configuration`，尽力设置 0600 权限），UI 永不回显完整 Key。此 Beta 不使用 OS keychain；如后续接入 Tauri Stronghold / OS keychain，必须同步更新实现、状态字段与用户文档。
- 默认不遥测；若后续增加崩溃报告，必须单独获得用户明确同意。

## 5. 数据策略：完整实时版

### 默认体验：免配置

安装后即可：

1. 使用内置赛程、球队基础数据和本地模型运行演示/离线推演；
2. 请求公开可用的实时数据源（如公开赛程、公开赔率接口）；
3. 显示数据来源、更新时间、可用市场、缺失项和可信度等级；
4. 当实时源不可用、过期或数据不完整时，明确降级为本地/快照数据，禁止伪称实时。

### 高级设置：用户自带 Key

- 用户可选填国际赔率或其他数据服务 API Key。
- 首版不强制任何 Key；没有 Key 时仍可使用公开源和离线推演。
- 设置页解释每一种 Key 的用途、来源、频率限制和数据是否会离开设备。
- Key 变更需立即做最小连通性校验，不把完整 Key 写入日志。

### 数据质量呈现

每次报告固定包含：

- `数据来源`：本地 / 快照 / 公开实时源 / 用户 API；
- `更新时间`；
- `数据完整度`；
- `可信度等级`；
- `缺失与降级说明`。

## 6. 安装与首次使用

### Windows

用户下载 `足球赛事AI推演引擎-Setup-x64.exe`：

1. 双击安装器；
2. 选择安装目录（默认用户目录，避免管理员权限）；
3. 安装器创建开始菜单与桌面快捷方式；
4. 可勾选“安装完成后启动”；
5. 首次启动初始化用户数据目录、SQLite 与默认配置；
6. 打开原生窗口，展示三步工作流与试用模式。

### macOS

用户下载对应架构 DMG：

1. 双击 `.dmg`；
2. 将 App 拖入 Applications；
3. 首次打开时初始化数据目录与配置；
4. 打开原生窗口。

### 未签名 Beta 说明

首轮未签名：

- Windows 可能显示 SmartScreen；
- macOS 可能被 Gatekeeper 阻止；
- Release 页面提供明确放行指引，且提示用户仅从官方 GitHub Release 下载。

正式公开分发前需单独接入 Windows Code Signing 与 Apple Developer notarization。

## 7. 更新机制

采用 GitHub Release 自动更新：

- App 启动后延迟检查，也可在“设置 → 检查更新”手动检查；
- 检查版本元数据、目标平台与安装包 hash；
- 下载完成后提示用户重启安装更新；
- 更新失败不影响当前可用版本；
- 在未签名 Beta 阶段，更新页必须明确风险提示；
- 自动更新 feed 仅指向指定 GitHub repo 的正式 Release，不接受任意 URL；
- 支持关闭自动下载，仅保留“发现新版本”提示。

## 8. GitHub 发布结构

### 代码仓库

建议私有 Beta repo：`0801ljw/pitchmind`。

对外 README 使用“足球赛事 AI 推演引擎”，并注明内部品牌“绿茵智擎”。源码、构建密钥、签名流程和用户数据必须分离。

### 每个 GitHub Release 附件

```text
足球赛事AI推演引擎-Setup-x64.exe
足球赛事AI推演引擎-macOS-AppleSilicon.dmg
足球赛事AI推演引擎-macOS-Intel.dmg
worldcup-ai-content-engine-source.tar.gz
SHA256SUMS.txt
RELEASE_NOTES.md
安装与Beta放行说明.pdf / INSTALL.md
```

### CI 构建矩阵

GitHub Actions：

- `windows-latest` 构建 PyInstaller Windows sidecar + Tauri NSIS `.exe`；
- `macos-14` 构建 arm64 Python sidecar + Tauri arm64 `.dmg`；
- `macos-13` 构建 x64 Python sidecar + Tauri x64 `.dmg`；
- 每个平台产物跑 smoke：启动 App/sidecar，检查 doctor、创建 dry-run、导出 ZIP；
- 汇总 SHA-256，创建 Draft Release；
- 由管理员审核后手动 Publish，Beta 阶段不自动公开。

## 9. 关键错误处理

| 情况 | 产品行为 |
|---|---|
| Python sidecar 启动失败 | 显示诊断页、日志路径、重启/导出诊断；不白屏 |
| 端口被占用 | 自动重新选择 localhost 端口 |
| 实时数据源失败 | 显示数据源不可用与降级信息；允许本地/快照模式 |
| 用户 API Key 无效 | 设置页提示失败原因，保留原 Key，不打印 Key |
| 更新下载失败 | 保持当前版本，提供重试与 Release 下载链接 |
| 升级后迁移失败 | 保留旧数据，备份并显示恢复建议 |
| 后端意外退出 | 前端提示服务异常，可安全重启 sidecar |

## 10. 验收标准

### 安装验收

- Windows x64 全新虚拟机：无 Python、无 Node、无 Hermes 环境，双击安装后能启动 App。
- macOS arm64 与 x64 干净环境：从 DMG 安装、打开、完成首次初始化。
- App 建立桌面快捷方式 / Applications 应用条目。
- 卸载程序删除应用本体但明确询问是否删除用户数据。

### 功能验收

- 首次启动可完成 dry-run；
- 正常联网时可执行真实数据请求并展示来源/时间；
- 数据源失败时会真实降级且不伪造实时数据；
- 高级设置可保存、校验和删除自有 API Key；
- 报告预览、历史记录、导出 ZIP 都可用；
- 全部产品输出继续通过合规扫描。

### 更新验收

- 安装 v0.1.0 后能发现 v0.1.1；
- 可下载并重启更新；
- 用户的数据库、配置、run 和报告升级后仍存在；
- 断网或更新失败时旧版仍可正常打开。

### 工程验收

- 保留现有 Python 测试；新增桌面配置、sidecar 生命周期、数据目录、数据源降级、API Key 脱敏、更新元数据的自动化测试；
- Windows/macOS CI 构建全部绿；
- 安装产物 SHA-256 已发布且复验一致；
- 真实干净环境端到端验收均有记录。

## 11. 明确不做（Desktop Beta 0.1）

- 不做移动 App；
- 不做支付、订阅扣费或“跟单”；
- 不做赛事组织方授权/官方合作暗示；
- 不做 Linux 与 Windows ARM；
- 不做远程云端账户同步；
- 不在未取得签名证书前宣称“无系统风险提示”。

## 12. 交付顺序

1. Desktop foundation：Tauri 宿主、用户数据目录、sidecar lifecycle、开发态联调；
2. Packaging：各平台 PyInstaller sidecar 与 Tauri 安装包；
3. Runtime：内置静态数据、默认实时源、降级与高级 API Key 设置；
4. CI/release：GitHub Actions 三平台构建、校验、Draft Release；
5. Updater：GitHub Release 更新 feed、下载、重启安装和失败回退；
6. Clean-machine QA：Windows/macOS 实机或云机安装验收；
7. Beta 发布：小范围 Private Release、反馈收集、签名路线决策。
