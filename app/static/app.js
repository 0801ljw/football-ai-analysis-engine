const WORKBENCH_THEME_STORAGE_KEY = "wc-theme";
const WORKBENCH_THEMES = new Set(["claude", "host", "deep-blue-tech"]);
const themeButtons = Array.from(document.querySelectorAll("[data-theme-option]"));

function applyWorkbenchTheme(theme) {
  const selectedTheme = WORKBENCH_THEMES.has(theme) ? theme : "claude";
  document.body.dataset.theme = selectedTheme;
  themeButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.themeOption === selectedTheme));
  });
}

function storedWorkbenchTheme() {
  try {
    return window.localStorage.getItem(WORKBENCH_THEME_STORAGE_KEY) || "claude";
  } catch (_error) {
    return "claude";
  }
}

applyWorkbenchTheme(storedWorkbenchTheme());

themeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const theme = button.dataset.themeOption || "claude";
    applyWorkbenchTheme(theme);
    try {
      window.localStorage.setItem(WORKBENCH_THEME_STORAGE_KEY, theme);
    } catch (_error) {
      // Theme switching still works for the current page when storage is unavailable.
    }
  });
});

const form = document.querySelector("#generate-form");
const output = document.querySelector("#api-output");
const skillStatusButton = document.querySelector("#skill-status-button");
const skillStatusOutput = document.querySelector("#skill-status-output");
const doctorButton = document.querySelector("#doctor-button");
const doctorOutput = document.querySelector("#doctor-output");
const setupGuideButton = document.querySelector("#setup-guide-button");
const setupGuideOutput = document.querySelector("#setup-guide-output");
const oddsForm = document.querySelector("#odds-form");
const oddsOutput = document.querySelector("#odds-output");
const reportForm = document.querySelector("#report-form");
const reportOutput = document.querySelector("#report-output");
const runForm = document.querySelector("#run-form");
const runResult = document.querySelector("#run-result");
const runsList = document.querySelector("#runs-list");
const queueStats = document.querySelector("#queue-stats");
const failureDashboard = document.querySelector("#failure-dashboard");
const refreshRunsButton = document.querySelector("#refresh-runs-button");
const discoverForm = document.querySelector("#discover-form");
const discoverResult = document.querySelector("#discover-result");
const useSelectedNumsButton = document.querySelector("#use-selected-nums-button");
const runsFilterForm = document.querySelector("#runs-filter-form");
const adminUsageButton = document.querySelector("#admin-usage-button");
const adminUsageOutput = document.querySelector("#admin-usage-output");
const adminUsersButton = document.querySelector("#admin-users-button");
const adminUserCreateForm = document.querySelector("#admin-user-create-form");
const adminUsersOutput = document.querySelector("#admin-users-output");
const consumerDiscoverForm = document.querySelector("#consumer-discover-form");
const consumerDiscoverResult = document.querySelector("#consumer-discover-result");
const consumerRunForm = document.querySelector("#consumer-run-form");
const consumerRunResult = document.querySelector("#consumer-run-result");
const consumerNumsInput = document.querySelector("#consumer-nums");
const consumerSelectedNums = document.querySelector("#consumer-selected-nums");
const demoRunButton = document.querySelector("#demo-run-button");
const summaryDataSource = document.querySelector("#summary-data-source");
const summaryRecentReports = document.querySelector("#summary-recent-reports");
const summaryCurrentTask = document.querySelector("#summary-current-task");
const summaryCurrentTaskNote = document.querySelector("#summary-current-task-note");
const stepperSteps = Array.from(document.querySelectorAll(".stepper-step"));
const authTokenInput = document.querySelector("#auth-token");
const authSaveButton = document.querySelector("#auth-save-button");
const authClearButton = document.querySelector("#auth-clear-button");
const authStatus = document.querySelector("#auth-status");
const desktopDataPanel = document.querySelector("#desktop-data-source-panel");
const desktopDataRefreshButton = document.querySelector("#desktop-data-refresh-button");
const desktopDataStatusOutput = document.querySelector("#desktop-data-status-output");
const desktopApiKeyForm = document.querySelector("#desktop-api-key-form");
const desktopApiKeyInput = document.querySelector("#desktop-api-key-input");
const desktopApiKeyDeleteButton = document.querySelector("#desktop-api-key-delete-button");
const desktopApiKeyStatus = document.querySelector("#desktop-api-key-status");
const isDesktopMode = document.body?.dataset?.desktopMode === "true";
const AUTH_TOKEN_STORAGE_KEY = "worldcup-api-token";

function currentAuthToken() {
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || "";
}

function authHeaders(extra = {}) {
  const token = currentAuthToken();
  return token ? { ...extra, "X-API-Token": token } : extra;
}

function updateAuthStatus(message = "") {
  if (!authStatus) {
    return;
  }
  const token = currentAuthToken();
  authStatus.textContent = message || (token ? "已保存 Token，本页请求会按用户隔离 run。" : "未保存 Token；无用户账号时将使用本机兼容模式。");
}

const TERMINAL_STATUSES = new Set(["succeeded", "partial", "partial_no_valid_matches", "failed", "cancelled", "dry_run"]);
const RETRYABLE_STATUSES = new Set(["failed", "partial", "partial_no_valid_matches", "cancelled"]);
const CANCELLABLE_STATUSES = new Set(["queued", "running_fetch", "running_report"]);
const STATUS_STEPS = ["queued", "running_fetch", "running_report", "succeeded"];
const STATUS_LABELS = {
  queued: "排队",
  running_fetch: "获取数据",
  running_report: "生成报告",
  succeeded: "完成",
  partial: "部分完成",
  partial_no_valid_matches: "无有效场次",
  failed: "失败",
  cancelled: "已取消",
  dry_run: "体验完成",
};

function setOnboardingStep(step) {
  const order = ["choose", "generate", "review"];
  const activeIndex = Math.max(0, order.indexOf(step));
  stepperSteps.forEach((item) => {
    const index = order.indexOf(item.dataset.step || "choose");
    item.classList.toggle("is-active", index === activeIndex);
    item.classList.toggle("is-complete", index >= 0 && index < activeIndex);
    if (index === activeIndex) {
      item.setAttribute("aria-current", "step");
    } else {
      item.removeAttribute("aria-current");
    }
  });
}

function updateCurrentTaskSummary(status = "idle", note = "准备好开始新的推演") {
  if (!summaryCurrentTask) {
    return;
  }
  summaryCurrentTask.textContent = status === "idle" ? "无任务" : (STATUS_LABELS[status] || status);
  if (summaryCurrentTaskNote) {
    summaryCurrentTaskNote.textContent = note;
  }
}

function summarizeRunsForWorkbench(runs) {
  if (summaryRecentReports) {
    const completed = runs.filter((run) => ["succeeded", "partial", "dry_run"].includes(run.status)).length;
    summaryRecentReports.textContent = completed ? `已完成 ${completed} 份` : "还没有报告";
  }
  const active = runs.find((run) => !TERMINAL_STATUSES.has(run.status));
  if (active) {
    updateCurrentTaskSummary(active.status, `${(active.nums || []).join(" ") || active.title || "报告"} 正在处理`);
    setOnboardingStep(active.status === "queued" || active.status === "running_fetch" ? "generate" : "review");
    return;
  }
  if (runs.some((run) => ["succeeded", "partial", "dry_run"].includes(run.status))) {
    updateCurrentTaskSummary("idle", "最近报告可查看或导出");
    setOnboardingStep("review");
  } else {
    updateCurrentTaskSummary("idle", "准备好开始新的推演");
    setOnboardingStep("choose");
  }
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    payload.http_error = true;
    payload.status_code = response.status;
  }
  return payload;
}

async function getJson(url) {
  const response = await fetch(url, { headers: authHeaders() });
  const payload = await response.json();
  if (!response.ok) {
    payload.http_error = true;
    payload.status_code = response.status;
  }
  return payload;
}

function writeJson(node, payload) {
  if (node) {
    node.textContent = JSON.stringify(payload, null, 2);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderHealth(health) {
  if (!health) {
    return '<span class="muted">health: 未记录</span>';
  }
  const validCount = Number(health.valid_count ?? 0);
  const invalidCount = Number(health.invalid_count ?? 0);
  const summary = escapeHtml(health.summary || `有效 ${validCount} / 不可用 ${invalidCount}`);
  return `<span class="health-pill" title="${summary}">有效 ${validCount} · 不可用 ${invalidCount}</span>`;
}

function previewButton(reportUrl, runId) {
  if (!reportUrl) {
    return "";
  }
  return `<button type="button" class="secondary-button preview-report-button" data-report-url="${reportUrl}" data-run-id="${runId}">预览报告</button>`;
}

function exportLink(runId) {
  const href = `/api/runs/${encodeURIComponent(runId)}/export.zip`;
  return `<a class="secondary-link" href="${href}">导出 ZIP</a>`;
}

function predictionLink(run) {
  if (!run?.artifacts?.prediction_exists && !run?.prediction_exists) {
    return "";
  }
  const runId = encodeURIComponent(run.run_id);
  return `<a class="secondary-link" href="/api/runs/${runId}/prediction" target="_blank" rel="noreferrer">prediction.json</a>`;
}

function renderDataQuality(dataQuality) {
  if (!dataQuality) {
    return '<span class="muted">质量: 未生成</span>';
  }
  const grade = escapeHtml(dataQuality.grade || "?");
  const status = escapeHtml(dataQuality.status || "unknown");
  const score = dataQuality.score === undefined ? "" : ` · ${Number(dataQuality.score)}`;
  const summary = escapeHtml(dataQuality.summary || `${grade} ${status}`);
  return `<span class="quality-pill quality-${grade.toLowerCase()}" title="${summary}">质量 ${grade} · ${status}${score}</span>`;
}

function formatFriendlyDate(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderBeginnerRunTitle(run) {
  return escapeHtml(run.title || "赛前数据研究报告");
}

function renderBeginnerRunMeta(run) {
  const nums = (run.nums || []).join(" ");
  const statusLabel = STATUS_LABELS[run.status] || "状态待确认";
  const updatedAt = formatFriendlyDate(run.updated_at);
  const createdAt = formatFriendlyDate(run.created_at);
  const timestamp = updatedAt || createdAt;
  const timestampLabel = timestamp ? ` · ${updatedAt ? "更新" : "创建"} ${timestamp}` : "";
  return escapeHtml(`比赛编号 ${nums || "未记录"} · ${statusLabel}${timestampLabel}`);
}


function renderDataTrust(trust) {
  if (!trust) {
    return '<div class="trust-panel muted">数据可信度：生成报告后显示。</div>';
  }
  const missing = (trust.missing_markets || []).length
    ? `<p>缺失盘口：${escapeHtml((trust.missing_markets || []).join("、"))}</p>`
    : "";
  const limitations = (trust.limitations || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  return `
    <div class="trust-panel">
      <strong>数据可信度 ${escapeHtml(trust.grade || "?")} · ${escapeHtml(trust.trust_level || "未知")}</strong>
      <p>${escapeHtml(trust.plain_language || trust.summary || "")}</p>
      <p>来源：${escapeHtml(trust.source_label || "未知")}</p>
      ${missing}
      ${limitations ? `<ul>${limitations}</ul>` : ""}
    </div>
  `;
}

function runActionButtons(run) {
  const runId = escapeHtml(run.run_id);
  const retry = RETRYABLE_STATUSES.has(run.status)
    ? `<button type="button" class="secondary-button retry-run-button" data-run-id="${runId}">重试</button>`
    : "";
  const cancel = CANCELLABLE_STATUSES.has(run.status)
    ? `<button type="button" class="danger-button cancel-run-button" data-run-id="${runId}">取消</button>`
    : "";
  return retry || cancel ? `<div class="run-controls">${retry}${cancel}</div>` : "";
}

function progressPercent(status) {
  if (status === "queued") {
    return 12;
  }
  if (status === "running_fetch") {
    return 42;
  }
  if (status === "running_report") {
    return 72;
  }
  if (status === "succeeded") {
    return 100;
  }
  if (status === "partial" || status === "partial_no_valid_matches" || status === "failed" || status === "cancelled") {
    return 100;
  }
  return 0;
}

function renderProgress(run) {
  const status = run.status;
  const currentIndex = STATUS_STEPS.indexOf(status);
  const terminal = TERMINAL_STATUSES.has(status);
  const steps = STATUS_STEPS.map((step, index) => {
    const complete = status === "succeeded" || (currentIndex >= 0 && index <= currentIndex);
    const active = step === status;
    return `<span class="${complete ? "complete" : ""} ${active ? "active" : ""}">${STATUS_LABELS[step]}</span>`;
  }).join("");
  const terminalLabel = terminal && !STATUS_STEPS.includes(status)
    ? `<span class="terminal ${status}">${STATUS_LABELS[status] || status}</span>`
    : "";
  return `
    <div class="run-progress" aria-label="run progress">
      <div class="progress-track"><div class="progress-fill" style="width: ${progressPercent(status)}%"></div></div>
      <div class="progress-steps">${steps}${terminalLabel}</div>
    </div>
  `;
}

function renderRunResult(run) {
  if (!runResult) {
    return;
  }
  if (run.http_error || !run.run_id) {
    runResult.innerHTML = `<span class="muted">请求未完成：${escapeHtml(run.detail || "unknown error")}</span>`;
    return;
  }
  const runId = escapeHtml(run.run_id);
  const reportUrl = escapeHtml(run.report_url || run.artifacts?.report_url || "");
  const health = run.odds_health;
  const healthSummary = escapeHtml(health?.summary || "");
  const reportLink = reportUrl
    ? `<a href="${reportUrl}" target="_blank" rel="noreferrer">打开报告</a>`
    : "<span>暂无报告</span>";
  runResult.innerHTML = `
    <strong>${renderBeginnerRunTitle(run)}</strong>
    <span>${renderBeginnerRunMeta(run)}</span>
    ${renderHealth(health)}
    ${renderDataQuality(run.data_quality)}
    ${renderDataTrust(run.data_trust)}
    ${healthSummary ? `<span class="health-summary">${healthSummary}</span>` : ""}
    ${renderProgress(run)}
    ${reportLink}
    ${exportLink(run.run_id)}
    ${predictionLink(run)}
    ${previewButton(reportUrl, runId)}
    ${runActionButtons(run)}
    <div class="report-preview" id="report-preview-${runId}" hidden></div>
  `;
}

function renderRuns(runs) {
  if (!runsList) {
    return;
  }
  if (!runs.length) {
    runsList.innerHTML = '<p class="muted empty-reports">从左侧生成第一份报告。</p>';
    return;
  }
  runsList.innerHTML = runs
    .map((run) => {
      const runId = escapeHtml(run.run_id);
      const reportUrl = escapeHtml(run.report_url || "");
      const report = reportUrl
        ? `<a href="${reportUrl}" target="_blank" rel="noreferrer">打开报告</a>${previewButton(reportUrl, runId)}`
        : '<span class="muted">无报告</span>';
      return `
        <article class="run-row">
          <div>
            <strong>${renderBeginnerRunTitle(run)}</strong>
            <p>${renderBeginnerRunMeta(run)}</p>
            <p>${renderHealth(run.odds_health)} ${renderDataQuality(run.data_quality)}</p>
          </div>
          <div class="run-links">${report}${exportLink(run.run_id)}${predictionLink(run)}</div>
          ${runActionButtons(run)}
          <div class="report-preview" id="report-preview-${runId}" hidden></div>
        </article>
      `;
    })
    .join("");
}

function renderQueueStats(stats) {
  if (!queueStats) {
    return;
  }
  if (stats.http_error) {
    queueStats.innerHTML = `<span class="muted">队列状态读取失败：${escapeHtml(stats.detail || "unknown error")}</span>`;
    return;
  }
  queueStats.innerHTML = `
    <span>排队 ${Number(stats.queued_count || 0)}</span>
    <span>运行 ${Number(stats.active_count || 0)}</span>
    <span>并发上限 ${Number(stats.max_concurrent_runs || 1)}</span>
  `;
}

function renderFailureDashboard(payload) {
  if (!failureDashboard) {
    return;
  }
  if (payload.http_error) {
    failureDashboard.innerHTML = `<span class="muted">失败概览读取失败：${escapeHtml(payload.detail || "unknown error")}</span>`;
    return;
  }
  const counts = Object.entries(payload.counts || {});
  const countPills = counts.length
    ? counts.map(([category, count]) => `<span>${escapeHtml(category)} ${Number(count || 0)}</span>`).join("")
    : '<span class="muted">暂无失败记录</span>';
  const recent = (payload.recent || []).slice(0, 5);
  const recentRows = recent.length
    ? recent.map((item) => `
        <li>
          <strong>${escapeHtml(item.category)}</strong>
          <span>${escapeHtml(item.title || item.run_id)} · ${escapeHtml(item.status)} · ${escapeHtml((item.nums || []).join(" "))}</span>
          ${item.summary ? `<small>${escapeHtml(item.summary)}</small>` : ""}
        </li>
      `).join("")
    : "";
  failureDashboard.innerHTML = `
    <div class="failure-counts">${countPills}</div>
    ${recentRows ? `<ul>${recentRows}</ul>` : ""}
  `;
}

function renderAdminUsers(payload, oneTimeToken = "") {
  if (!adminUsersOutput) {
    return;
  }
  if (payload.http_error) {
    adminUsersOutput.innerHTML = `<p class="muted">用户管理读取失败：${escapeHtml(payload.detail || "unknown error")}</p>`;
    return;
  }
  const users = payload.users || (payload.user ? [payload.user] : []);
  const tokenNotice = oneTimeToken
    ? `<p class="token-once"><strong>一次性 Token：</strong><code>${escapeHtml(oneTimeToken)}</code></p>`
    : "";
  const rows = users.length
    ? users.map((user) => {
        const quota = user.quota || {};
        const active = Number(user.active) === 1 || user.active === true;
        return `
          <tr>
            <td>${escapeHtml(user.username)}</td>
            <td>${escapeHtml(user.role)}</td>
            <td>${escapeHtml(user.plan)}</td>
            <td>${Number(quota.run_quota ?? user.run_quota ?? 0)}</td>
            <td>${Number(quota.real_runs_used ?? 0)}</td>
            <td>${Number(quota.remaining_real_runs ?? 0)}</td>
            <td>${active ? "active" : "disabled"}</td>
            <td><code>${escapeHtml(user.token_preview || "")}</code></td>
          </tr>
        `;
      }).join("")
    : '<tr><td colspan="8">暂无用户</td></tr>';
  adminUsersOutput.innerHTML = `
    ${tokenNotice}
    <table class="admin-users-table">
      <thead><tr><th>用户</th><th>角色</th><th>Plan</th><th>Quota</th><th>Used</th><th>Remaining</th><th>Status</th><th>Token</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

async function refreshAdminUsers() {
  if (!adminUsersOutput) {
    return;
  }
  adminUsersOutput.textContent = "读取中...";
  renderAdminUsers(await getJson("/api/admin/users"));
}

function renderSetupGuide(payload) {
  if (!setupGuideOutput) {
    return;
  }
  if (payload.http_error) {
    setupGuideOutput.innerHTML = `<p class="muted">启动指南读取失败：${escapeHtml(payload.detail || "unknown error")}</p>`;
    return;
  }
  const steps = (payload.steps || []).map((step) => `<li>${escapeHtml(step)}</li>`).join("");
  const commands = (payload.commands || []).map((command) => `<code>${escapeHtml(command)}</code>`).join("");
  setupGuideOutput.innerHTML = `
    <div class="setup-guide-summary">
      <strong>${escapeHtml(payload.status || "unknown")}</strong>
      <span>${escapeHtml((payload.missing || []).length)} missing item(s)</span>
    </div>
    ${steps ? `<ol>${steps}</ol>` : ""}
    ${commands ? `<div class="setup-guide-commands">${commands}</div>` : ""}
    <pre>${escapeHtml(JSON.stringify(payload.config || {}, null, 2))}</pre>
  `;
}

function renderDesktopKeyStatus(keyState) {
  if (!desktopApiKeyStatus) {
    return;
  }
  if (!keyState) {
    desktopApiKeyStatus.textContent = "Key 状态未知。";
    return;
  }
  desktopApiKeyStatus.textContent = keyState.configured
    ? `已配置 ${keyState.provider}：${keyState.masked || "已遮罩"}（${keyState.storage || "local"}）`
    : `未配置 ${keyState.provider || "the_odds_api"} API Key。`;
}

function renderDesktopDataStatus(payload) {
  if (!desktopDataStatusOutput) {
    return;
  }
  if (payload.http_error) {
    if (payload.status_code === 404 && desktopDataPanel) {
      desktopDataPanel.hidden = true;
      return;
    }
    desktopDataStatusOutput.innerHTML = `<p class="muted">桌面数据来源状态不可用：${escapeHtml(payload.detail || "unknown error")}</p>`;
    return;
  }
  if (desktopDataPanel) {
    desktopDataPanel.hidden = false;
  }
  const sources = payload.sources || {};
  const local = sources.local_fallback || {};
  const publicSource = sources.public_source || {};
  const keyState = sources.user_key || {};
  renderDesktopKeyStatus(keyState);
  desktopDataStatusOutput.innerHTML = `
    <div class="desktop-source-grid">
      <article>
        <strong>本地 fallback</strong>
        <p>${local.available ? "可用" : "不可用"} · ${escapeHtml(local.source || "local/demo/offline")} · ${local.realtime ? "实时" : "非实时"}</p>
        <small>${escapeHtml(local.reason || "")}</small>
      </article>
      <article>
        <strong>公开数据源</strong>
        <p>${escapeHtml(publicSource.status || "not_checked")} · ${publicSource.available ? "可用" : "不可用"} · ${publicSource.realtime ? "实时" : "非实时"}</p>
        <small>${escapeHtml(publicSource.reason || "仅在显式检查/抓取成功后更新；不会隐式联网。")}</small>
      </article>
      <article>
        <strong>用户 Key</strong>
        <p>${keyState.configured ? "已配置" : "未配置"} ${keyState.masked ? `· ${escapeHtml(keyState.masked)}` : ""}</p>
        <small>${escapeHtml(keyState.storage || "local user configuration")}</small>
      </article>
    </div>
    <p class="desktop-updated">更新时间：${escapeHtml(payload.updated_at || "未知")}</p>
    ${payload.degraded ? `<p class="desktop-degraded">降级原因：${escapeHtml(payload.reason || "unknown")}</p>` : ""}
    <p class="desktop-compliance">${escapeHtml(payload.compliance_notice || "")}</p>
  `;
}

async function refreshDesktopDataStatus() {
  if (!desktopDataStatusOutput) {
    return;
  }
  desktopDataStatusOutput.textContent = "读取中...";
  renderDesktopDataStatus(await getJson("/api/desktop/data-status"));
}

async function saveDesktopApiKey(apiKey) {
  const response = await fetch("/api/desktop/settings/api-keys/the_odds_api", {
    method: "PUT",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ api_key: apiKey }),
  });
  const payload = await response.json();
  if (!response.ok) {
    payload.http_error = true;
    payload.status_code = response.status;
  }
  return payload;
}

async function deleteDesktopApiKey() {
  const response = await fetch("/api/desktop/settings/api-keys/the_odds_api", {
    method: "DELETE",
    headers: authHeaders(),
  });
  const payload = await response.json();
  if (!response.ok) {
    payload.http_error = true;
    payload.status_code = response.status;
  }
  return payload;
}

if (desktopDataRefreshButton) {
  desktopDataRefreshButton.addEventListener("click", refreshDesktopDataStatus);
}

if (desktopApiKeyForm && desktopApiKeyInput) {
  desktopApiKeyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const apiKey = desktopApiKeyInput.value;
    if (!apiKey.trim()) {
      if (desktopApiKeyStatus) desktopApiKeyStatus.textContent = "请输入非空 API Key。";
      return;
    }
    if (desktopApiKeyStatus) desktopApiKeyStatus.textContent = "保存中...";
    const payload = await saveDesktopApiKey(apiKey);
    desktopApiKeyInput.value = "";
    if (payload.http_error) {
      if (desktopApiKeyStatus) desktopApiKeyStatus.textContent = `保存失败：${payload.detail || "unknown error"}`;
      return;
    }
    renderDesktopKeyStatus(payload);
    await refreshDesktopDataStatus();
  });
}

if (desktopApiKeyDeleteButton) {
  desktopApiKeyDeleteButton.addEventListener("click", async () => {
    if (desktopApiKeyStatus) desktopApiKeyStatus.textContent = "删除中...";
    const payload = await deleteDesktopApiKey();
    if (payload.http_error) {
      if (desktopApiKeyStatus) desktopApiKeyStatus.textContent = `删除失败：${payload.detail || "unknown error"}`;
      return;
    }
    renderDesktopKeyStatus(payload);
    await refreshDesktopDataStatus();
  });
}

if (authTokenInput) {
  authTokenInput.value = currentAuthToken();
  updateAuthStatus();
}

if (authSaveButton && authTokenInput) {
  authSaveButton.addEventListener("click", async () => {
    const token = authTokenInput.value.trim();
    if (token) {
      window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    }
    const me = await getJson("/api/me");
    updateAuthStatus(me.http_error ? `Token 已保存，但验证失败：${me.detail || "unknown error"}` : `已登录：${me.user?.username || "system"}（${me.user?.role || "unknown"}）`);
    await refreshRuns();
  });
}

if (authClearButton && authTokenInput) {
  authClearButton.addEventListener("click", async () => {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    authTokenInput.value = "";
    updateAuthStatus("已清除本机保存的 Token。");
    await refreshRuns();
  });
}

document.addEventListener("click", (event) => {
  const button = event.target.closest(".preview-report-button");
  if (!button) {
    return;
  }
  const reportUrl = button.dataset.reportUrl;
  const runId = button.dataset.runId;
  const preview = document.querySelector(`#report-preview-${CSS.escape(runId)}`);
  if (!preview || !reportUrl) {
    return;
  }
  const isHidden = preview.hasAttribute("hidden");
  if (isHidden) {
    preview.innerHTML = `<iframe title="报告预览 ${escapeHtml(runId)}" src="${escapeHtml(reportUrl)}"></iframe>`;
    preview.removeAttribute("hidden");
    button.textContent = "收起预览";
  } else {
    preview.setAttribute("hidden", "");
    button.textContent = "预览报告";
  }
});

document.addEventListener("click", async (event) => {
  const retryButton = event.target.closest(".retry-run-button");
  const cancelButton = event.target.closest(".cancel-run-button");
  if (!retryButton && !cancelButton) {
    return;
  }
  const button = retryButton || cancelButton;
  const runId = button.dataset.runId;
  if (!runId) {
    return;
  }
  button.disabled = true;
  const action = retryButton ? "retry" : "cancel";
  const payload = await postJson(`/api/runs/${encodeURIComponent(runId)}/${action}`, {});
  renderRunResult(payload);
  await refreshRuns();
  if (action === "retry" && payload.run_id && !TERMINAL_STATUSES.has(payload.status)) {
    pollRun(payload.run_id);
  }
});

async function refreshRuns() {
  if (!runsList) {
    return;
  }
  runsList.textContent = "读取中...";
  const params = new URLSearchParams();
  if (runsFilterForm) {
    const data = new FormData(runsFilterForm);
    for (const key of ["status", "num", "quality", "q"]) {
      const value = String(data.get(key) || "").trim();
      if (value) params.set(key, value);
    }
  }
  const runsUrl = `/api/runs${params.toString() ? `?${params.toString()}` : ""}`;
  const [payload, stats, failures] = await Promise.all([
    getJson(runsUrl),
    getJson("/api/runs/queue"),
    getJson("/api/runs/failures"),
  ]);
  renderRuns(payload.runs || []);
  summarizeRunsForWorkbench(payload.runs || []);
  renderQueueStats(stats);
  renderFailureDashboard(failures);
}

async function pollRun(runId) {
  const detail = await getJson(`/api/runs/${encodeURIComponent(runId)}`);
  renderRunResult(detail);
  if (detail.http_error) {
    return;
  }
  await refreshRuns();
  if (!TERMINAL_STATUSES.has(detail.status)) {
    window.setTimeout(() => pollRun(runId), 1000);
  }
}


function selectedConsumerNums() {
  if (consumerDiscoverResult) {
    const checkboxes = Array.from(consumerDiscoverResult.querySelectorAll('input[type="checkbox"]'));
    if (checkboxes.length) {
      return checkboxes.filter((item) => item.checked).map((item) => item.value).join(" ");
    }
  }
  return consumerNumsInput ? consumerNumsInput.value : "";
}

function updateConsumerSelectedNums() {
  if (!consumerSelectedNums) {
    return;
  }
  const nums = selectedConsumerNums();
  consumerSelectedNums.textContent = nums ? `将生成：${nums}` : "暂无可生成编号。";
}

function renderConsumerDiscover(payload) {
  if (!consumerDiscoverResult) {
    return;
  }
  if (payload.http_error) {
    consumerDiscoverResult.innerHTML = `<p class="muted">检查失败：${escapeHtml(payload.detail || "unknown error")}</p>`;
    updateCurrentTaskSummary("idle", "检查未完成，请稍后重试");
    return;
  }
  const validNums = payload.valid_nums || [];
  const invalidEntries = Object.entries(payload.invalid || {});
  const validList = validNums.length
    ? validNums.map((num) => `
        <label class="check-row">
          <input type="checkbox" value="${escapeHtml(num)}" checked>
          <span>${escapeHtml(num)}</span>
        </label>
      `).join("")
    : '<p class="muted">暂未发现可用场次，请检查编号或稍后重试。</p>';
  const invalidList = invalidEntries.length
    ? `<ul>${invalidEntries.map(([num, reason]) => `<li><strong>${escapeHtml(num)}</strong>：${escapeHtml(reason)}</li>`).join("")}</ul>`
    : '<p class="muted">没有不可用编号。</p>';
  consumerDiscoverResult.innerHTML = `
    <p>${escapeHtml(payload.summary || "检查完成")}</p>
    <div class="consumer-num-grid">
      <div><h4>可用于生成</h4>${validList}</div>
      <div><h4>暂不可用</h4>${invalidList}</div>
    </div>
  `;
  updateConsumerSelectedNums();
  updateCurrentTaskSummary("idle", validNums.length ? "可用场次已选好" : "没有发现可用场次");
  if (validNums.length) {
    setOnboardingStep("generate");
  }
}

function renderConsumerRun(run) {
  if (!consumerRunResult) {
    return;
  }
  if (run.http_error || !run.run_id) {
    consumerRunResult.innerHTML = `<p class="muted">生成失败：${escapeHtml(run.detail || "unknown error")}</p>`;
    updateCurrentTaskSummary("failed", "请检查编号或稍后重试");
    return;
  }
  const runId = escapeHtml(run.run_id);
  const reportUrl = escapeHtml(run.report_url || run.artifacts?.report_url || "");
  const reportLink = reportUrl
    ? `<a class="secondary-link" href="${reportUrl}" target="_blank" rel="noreferrer">打开报告</a>`
    : '<span class="muted">报告生成中或暂无报告</span>';
  consumerRunResult.innerHTML = `
    <div class="consumer-status-card">
      <strong>${renderBeginnerRunTitle(run)}</strong>
      <span>${renderBeginnerRunMeta(run)}</span>
      ${renderHealth(run.odds_health)}
      ${renderDataQuality(run.data_quality)}
      ${renderDataTrust(run.data_trust)}
      ${renderProgress(run)}
      <div class="run-links">${reportLink}${exportLink(run.run_id)}${predictionLink(run)}${previewButton(reportUrl, `consumer-${runId}`)}</div>
      <div class="report-preview" id="report-preview-consumer-${runId}" hidden></div>
    </div>
  `;
  updateCurrentTaskSummary(run.status, TERMINAL_STATUSES.has(run.status) ? "报告已可查看或导出" : "任务正在处理");
  setOnboardingStep(TERMINAL_STATUSES.has(run.status) ? "review" : "generate");
}

async function pollConsumerRun(runId) {
  const detail = await getJson(`/api/runs/${encodeURIComponent(runId)}`);
  renderConsumerRun(detail);
  await refreshRuns();
  if (!detail.http_error && !TERMINAL_STATUSES.has(detail.status)) {
    window.setTimeout(() => pollConsumerRun(runId), 1000);
  }
}

if (consumerDiscoverForm && consumerDiscoverResult) {
  consumerDiscoverForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(consumerDiscoverForm);
    const timeoutValue = Number(data.get("timeout") || 60);
    consumerDiscoverResult.textContent = "正在检查公开数据可用性...";
    updateCurrentTaskSummary("running_fetch", "正在检查可用场次");
    setOnboardingStep("choose");
    const payload = await postJson("/api/odds/discover", {
      nums: data.get("nums"),
      timeout: Number.isFinite(timeoutValue) ? timeoutValue : 60,
    });
    renderConsumerDiscover(payload);
  });

  consumerDiscoverResult.addEventListener("change", (event) => {
    if (event.target.matches('input[type="checkbox"]')) {
      updateConsumerSelectedNums();
    }
  });
}

if (demoRunButton && consumerNumsInput && consumerRunForm) {
  demoRunButton.addEventListener("click", () => {
    consumerNumsInput.value = "086 087 088";
    const trialMode = consumerRunForm.querySelector('input[name="trial_mode"]');
    if (trialMode) {
      trialMode.checked = true;
    }
    const titleInput = consumerRunForm.querySelector('input[name="title"]');
    if (titleInput) {
      titleInput.value = "PitchMind Demo 赛前数据研究报告";
    }
    if (summaryDataSource) {
      summaryDataSource.textContent = "体验模式已就绪";
    }
    updateConsumerSelectedNums();
    updateCurrentTaskSummary("dry_run", "正在启动一键体验 Demo");
    setOnboardingStep("generate");
    consumerRunForm.requestSubmit();
  });
}

if (consumerRunForm && consumerRunResult) {
  consumerRunForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(consumerRunForm);
    const timeoutValue = Number(data.get("timeout") || 60);
    const nums = selectedConsumerNums();
    const trialMode = data.get("trial_mode") === "on";
    consumerRunResult.textContent = trialMode ? "正在创建体验任务..." : "已提交任务，正在排队生成...";
    updateCurrentTaskSummary(trialMode ? "dry_run" : "queued", trialMode ? "正在准备示例报告" : "任务已提交");
    setOnboardingStep("generate");
    const payload = await postJson("/api/runs", {
      nums,
      title: data.get("title"),
      theme: data.get("theme"),
      timeout: Number.isFinite(timeoutValue) ? timeoutValue : 60,
      dry_run: trialMode,
      background: !trialMode,
    });
    renderConsumerRun(payload);
    await refreshRuns();
    if (payload.run_id && !TERMINAL_STATUSES.has(payload.status)) {
      pollConsumerRun(payload.run_id);
    }
  });
}

if (form && output) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    output.textContent = "生成中...";

    const payload = await postJson("/api/generate", {
      match_id: data.get("match_id"),
      theme: data.get("theme"),
    });

    writeJson(output, payload);
  });
}

if (skillStatusButton && skillStatusOutput) {
  skillStatusButton.addEventListener("click", async () => {
    skillStatusOutput.textContent = "读取中...";
    const response = await fetch("/api/skill/status");
    writeJson(skillStatusOutput, await response.json());
  });
}

if (doctorButton && doctorOutput) {
  doctorButton.addEventListener("click", async () => {
    doctorOutput.textContent = "体检中...";
    writeJson(doctorOutput, await getJson("/api/system/doctor"));
  });
}

if (setupGuideButton && setupGuideOutput) {
  setupGuideButton.addEventListener("click", async () => {
    setupGuideOutput.textContent = "读取中...";
    renderSetupGuide(await getJson("/api/system/setup-guide"));
  });
}

if (oddsForm && oddsOutput) {
  oddsForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(oddsForm);
    oddsOutput.textContent = "生成中...";

    const payload = await postJson("/api/odds/fetch", {
      nums: data.get("nums"),
      out_path: data.get("out_path"),
      dry_run: true,
    });

    writeJson(oddsOutput, payload);
  });
}

if (reportForm && reportOutput) {
  reportForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(reportForm);
    reportOutput.textContent = "生成中...";

    const payload = await postJson("/api/reports/build", {
      odds_path: data.get("odds_path"),
      out_path: data.get("out_path"),
      title: data.get("title"),
      theme: data.get("theme"),
      dry_run: true,
    });

    writeJson(reportOutput, payload);
  });
}

if (runForm && runResult) {
  let selectedDryRun = true;
  runForm.querySelectorAll("button[data-dry-run]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedDryRun = button.dataset.dryRun === "true";
    });
  });

  runForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(runForm);
    runResult.textContent = "创建中...";
    const timeoutValue = Number(data.get("timeout") || 60);

    const payload = await postJson("/api/runs", {
      nums: data.get("nums"),
      title: data.get("title"),
      theme: data.get("theme"),
      timeout: Number.isFinite(timeoutValue) ? timeoutValue : 60,
      dry_run: selectedDryRun,
      background: !selectedDryRun,
    });

    renderRunResult(payload);
    await refreshRuns();
    if (!selectedDryRun && payload.run_id && !TERMINAL_STATUSES.has(payload.status)) {
      pollRun(payload.run_id);
    }
  });
}

function renderDiscoverResult(payload) {
  if (!discoverResult) {
    return;
  }
  const validNums = payload.valid_nums || [];
  const invalid = payload.invalid || {};
  const validList = validNums.length
    ? validNums.map((num) => `
        <label class="check-row">
          <input type="checkbox" value="${escapeHtml(num)}" checked>
          <span>${escapeHtml(num)}</span>
        </label>
      `).join("")
    : '<p class="muted">没有可用编号</p>';
  const invalidEntries = Object.entries(invalid);
  const invalidList = invalidEntries.length
    ? `<ul>${invalidEntries.map(([num, reason]) => `<li><strong>${escapeHtml(num)}</strong> · ${escapeHtml(reason)}</li>`).join("")}</ul>`
    : '<p class="muted">没有不可用编号</p>';
  discoverResult.innerHTML = `
    <p>${escapeHtml(payload.summary || "检查完成")}</p>
    <div class="discover-grid">
      <div>
        <h3>可用编号</h3>
        ${validList}
      </div>
      <div>
        <h3>不可用编号</h3>
        ${invalidList}
      </div>
    </div>
  `;
  if (useSelectedNumsButton) {
    useSelectedNumsButton.disabled = validNums.length === 0;
  }
}

if (discoverForm && discoverResult) {
  discoverForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(discoverForm);
    const timeoutValue = Number(data.get("timeout") || 60);
    discoverResult.textContent = "检查中...";
    if (useSelectedNumsButton) {
      useSelectedNumsButton.disabled = true;
    }
    const payload = await postJson("/api/odds/discover", {
      nums: data.get("nums"),
      timeout: Number.isFinite(timeoutValue) ? timeoutValue : 60,
    });
    renderDiscoverResult(payload);
  });
}

if (useSelectedNumsButton && runForm) {
  useSelectedNumsButton.addEventListener("click", () => {
    const selected = Array.from(discoverResult.querySelectorAll('input[type="checkbox"]:checked')).map((item) => item.value);
    const numsInput = runForm.querySelector('input[name="nums"]');
    if (numsInput && selected.length) {
      numsInput.value = selected.join(" ");
      numsInput.focus();
    }
  });
}

if (runsFilterForm) {
  runsFilterForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await refreshRuns();
  });
}

if (adminUsageButton && adminUsageOutput) {
  adminUsageButton.addEventListener("click", async () => {
    adminUsageOutput.textContent = "读取中...";
    writeJson(adminUsageOutput, await getJson("/api/admin/usage"));
  });
}

if (adminUsersButton && adminUsersOutput) {
  adminUsersButton.addEventListener("click", refreshAdminUsers);
}

if (adminUserCreateForm && adminUsersOutput) {
  adminUserCreateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(adminUserCreateForm);
    const payload = await postJson("/api/admin/users", {
      username: data.get("username"),
      role: data.get("role"),
      plan: data.get("plan"),
      run_quota: Number(data.get("run_quota") || 0),
    });
    if (payload.http_error) {
      renderAdminUsers(payload);
      return;
    }
    const summary = await getJson("/api/admin/users");
    renderAdminUsers(summary, payload.token || "");
  });
}

if (refreshRunsButton) {
  refreshRunsButton.addEventListener("click", refreshRuns);
}

if (isDesktopMode) {
  refreshDesktopDataStatus();
} else if (desktopDataPanel) {
  desktopDataPanel.hidden = true;
}
refreshRuns();
