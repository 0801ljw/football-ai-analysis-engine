# 世界杯 AI 推演内容引擎｜首个外部用户试用包（Phase 20）

> 面向：第一个真实外部试用用户 + 试用主持人  
> 目标：验证“安装启动 → 账号 Token → 三步 dry-run → 报告导出”的最小闭环。  
> 当前 release：`dist/worldcup-ai-content-engine-v0.1.0-20260705T114745Z.tar.gz`  
> 校验文件：`dist/worldcup-ai-content-engine-v0.1.0-20260705T114745Z.tar.gz.sha256`

---

## 一、核心数据速览

| 项目 | 当前状态 |
|---|---|
| 产品定位 | 体育数据推演与内容研究工具，不是下注建议 |
| 试用范围 | 只跑 dry-run，不要求真实赔率抓取 |
| 交付包 | `worldcup-ai-content-engine-v0.1.0-20260705T114745Z.tar.gz` |
| 安全默认 | 仅监听 `127.0.0.1` |
| 非本机暴露 | 必须设置 `WC_API_TOKEN` |
| 首测脚本 | `scripts/external_trial_smoke.py` |
| 成功标准 | doctor ready、Token 可用、dry-run 成功、export.zip 可下载 |

---

## 二、给试用用户看的简短说明

你好，这是一个“世界杯赛前数据推演报告”本地试用版。它会在你的电脑上启动一个本地网页，你可以用三步完成一次报告生成流程：

1. 输入比赛编号；
2. 生成 dry-run 测试报告；
3. 导出 zip 文件。

这不是下注推荐，也不承诺命中率或收益；它只是把数据、概率和风险提示整理成可读报告，便于研究和内容生产。

### 你需要准备

- 一台能运行 Python 3.11+ 的电脑；
- 一个由管理员提供的 API Token；
- release 包：`worldcup-ai-content-engine-v0.1.0-20260705T114745Z.tar.gz`。

### 试用命令

```bash
tar -xzf worldcup-ai-content-engine-v0.1.0-20260705T114745Z.tar.gz
cd worldcup-ai-content-engine-v0.1.0-20260705T114745Z
scripts/setup.sh
scripts/start.sh
```

打开：

```text
http://127.0.0.1:8787/
```

如果管理员要求你跑自动试用检查：

```bash
BASE_URL=http://127.0.0.1:8787 ADMIN_TOKEN='管理员给你的token' scripts/external_trial_smoke.py
```

---

## 三、主持人试用流程 Checklist

### A. 试用前准备

- [ ] 确认发给用户的是已验证 release 包，不是工作目录。
- [ ] 附带 `.sha256`，让用户可校验完整性。
- [ ] 告知：第一轮只跑 dry-run，不测真实赔率抓取。
- [ ] 准备一个临时 admin token 或提前创建 trial user token。
- [ ] 说明 Token 只显示一次，丢失要 reset。

### B. 安装启动

让用户按顺序执行：

```bash
scripts/setup.sh
scripts/doctor.sh
scripts/start.sh
```

验收口径：

- [ ] `doctor` 是 `ready` 或可解释的 `degraded`；
- [ ] 页面能打开；
- [ ] 首页能看到“账号 Token”和“三步生成赛前报告”。

### C. 账号与权限

- [ ] 用户能把 Token 粘贴进首页并保存；
- [ ] `/api/me` 能返回当前用户；
- [ ] 普通用户不能访问 Admin 用户管理；
- [ ] 用户只能看到自己的 run。

### D. 核心 dry-run 链路

建议测试编号：`086`。

- [ ] 点击/提交 dry-run；
- [ ] run 状态返回 `dry_run`；
- [ ] 历史列表能看到该 run；
- [ ] export.zip 可下载；
- [ ] 用户能找到 zip 文件。

### E. 观察用户反应

重点观察这 6 件事：

1. 是否理解“这是本地网页，不是线上 SaaS”；
2. 是否理解 Token；
3. 是否知道下一步点哪里；
4. 是否能区分 dry-run 和真实抓取；
5. 是否误解成“下注推荐”；
6. 是否觉得导出的 zip 有用。

---

## 四、主持人标准话术

### 开场

> 这是一个早期试用版，我想验证的是“普通用户能不能装起来、跑通一次报告生成、导出结果”。今天先不测真实数据抓取，只测产品主流程。

### 合规说明

> 这个工具做的是概率推演和数据研究，不构成下注建议，也不承诺命中率或收益。你看到的内容请按研究/娱乐理解。

### 遇到卡住时

> 先不要自己反复重装，把终端最后 30 行和页面截图发我。我会判断是安装、端口、Token 还是产品 UX 问题。

### 结束提问

> 如果只保留一个改进点，你最希望我们先改什么？安装、页面理解、Token、生成速度、导出文件，还是报告内容？

---

## 五、试用成功标准

本轮 Phase 20 只要求达成以下最小闭环：

- [ ] 至少 1 位真实外部用户参与；
- [ ] 用户在非开发者引导下完成安装或访问；
- [ ] 至少 1 次 dry-run 成功；
- [ ] 至少 1 次 export.zip 成功；
- [ ] 收集到 5 条以上有效反馈；
- [ ] 明确下一轮优先级：安装问题、UX 问题、账号问题、真实数据链路，四选一。

---

## 六、试用反馈表

详见 `PHASE20_FEEDBACK_FORM.md`。建议每次试用后立刻填写，不要凭记忆复盘。
