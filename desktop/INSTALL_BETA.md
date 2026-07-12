# 足球赛事 AI 推演引擎 unsigned Beta 安装说明

本文面向 PitchMind 桌面端 unsigned Beta 试用者。当前 Windows/macOS 安装包由 CI 构建；维护者当前不会在本机生成这些安装包，也不会通过聊天窗口单独发送安装器。

## 下载来源

1. 只从项目的 GitHub Release 页面下载 Draft/Prerelease 经维护者确认后的附件。
2. 下载对应系统的安装包和 `SHA256SUMS.txt`，本地校验后再安装。
3. 不要通过聊天、私信或截图发送任何 API Token、管理员 Token、`.env`、数据库或密钥。需要诊断时只发错误文字、版本号、系统版本和不含密钥的截图。

## 当前更新策略

这是未签名 Beta。自动更新暂未启用，也没有内置签名 updater；本阶段更新方式是手动下载新的 GitHub Release 附件并覆盖安装。自动签名更新器会在后续正式签名发布流程中再接入。

## Windows 安装与 SmartScreen

1. 下载 `nsis` 安装器后先校验 SHA-256。
2. 双击安装器。如果 Windows SmartScreen 提示“Windows 已保护你的电脑”，这是未签名 Beta 的预期现象。
3. 确认来源是 GitHub Release 后，可选择“更多信息” -> “仍要运行”。如果来源不确定，请取消安装。
4. 安装范围为当前用户，不需要管理员权限。

## macOS 安装与 Gatekeeper

1. 下载与你芯片匹配的 DMG：Apple Silicon 使用 `aarch64-apple-darwin`，Intel 使用 `x86_64-apple-darwin`。
2. 校验 SHA-256 后打开 DMG，并拖入 Applications。
3. 若 macOS Gatekeeper 提示无法验证开发者，这是未签名 Beta 的预期现象。
4. 确认来源是 GitHub Release 后，可在 Finder 中右键应用 -> 打开，或到 系统设置 -> 隐私与安全性 中允许打开。若来源不确定，请删除该文件。

## 错误与诊断

- 启动失败时，记录系统版本、下载的文件名、校验结果、错误提示全文。
- 应用内部诊断页或错误页可用于判断本地 sidecar 是否启动、端口是否可用、配置目录是否可写。
- 不要发送 Token、`.env`、`data/app.db`、`runs/` 目录或任何 API key。
- 当前安装包是 CI 构建产物，不是本地生成产物；如果 GitHub Release 没有对应平台附件，请等待维护者重新运行 CI。
