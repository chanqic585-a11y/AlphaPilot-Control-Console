"use strict";

const STALE_AFTER_MS = 3000;
const PAGE_SIZE = 50;
const CONFLICT_MESSAGE = "底层状态已变更，请基于最新状态操作";

const documentRoot = document.body;
const app = document.getElementById("app");
const pageTitle = document.getElementById("page-title");
const staleBanner = document.getElementById("stale-banner");
const conflictBanner = document.getElementById("conflict-banner");
const errorBanner = document.getElementById("error-banner");
const connectionLabel = document.getElementById("connection-label");
const heartbeatTime = document.getElementById("heartbeat-time");

class ProjectionConflictError extends Error {}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function valueOf(object, keys, fallback = "--") {
  for (const key of keys) {
    const value = object?.[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return fallback;
}

function displayNumber(value, fallback = "--") {
  if (value === null || value === undefined || value === "") return fallback;
  const number = Number(value);
  if (!Number.isFinite(number)) return escapeHtml(value);
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(number);
}

function displayMoney(value) {
  if (value === null || value === undefined || value === "") return "--";
  const number = Number(value);
  if (!Number.isFinite(number)) return escapeHtml(value);
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(number);
}

function pilotIdentity(pilot) {
  if (!pilot) return "暂无";
  if (typeof pilot !== "object") return String(pilot);
  const campaignId = valueOf(pilot, ["campaignId", "pilotId", "id"], "");
  const status = valueOf(pilot, ["status", "state"], "");
  if (!campaignId) return "未命名 Pilot";
  return status ? `${campaignId} · ${status}` : campaignId;
}

function strategyCandidateLinks(pilot) {
  const ids = [
    ...(Array.isArray(pilot?.formalReadyCandidateIds) ? pilot.formalReadyCandidateIds : []),
    ...(Array.isArray(pilot?.formalBlockedCandidateIds) ? pilot.formalBlockedCandidateIds : []),
  ];
  if (!ids.length) return '<div class="empty-state">当前 Pilot 没有正式候选</div>';
  return `<div class="candidate-links">${ids.map((id) => (
    `<a class="button-link" href="/v63a/strategy/${encodeURIComponent(id)}">${escapeHtml(id)}</a>`
  )).join("")}</div>`;
}

function formatBeijing(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return escapeHtml(value);
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function setError(message = "") {
  errorBanner.textContent = message;
  errorBanner.hidden = !message;
}

function showConflict(message = CONFLICT_MESSAGE) {
  conflictBanner.textContent = message || CONFLICT_MESSAGE;
  conflictBanner.hidden = false;
}

async function fetchProjection(url, { refreshProjection } = {}) {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (response.status === 409) {
    const conflict = await response.json().catch(() => ({}));
    showConflict(conflict.message || CONFLICT_MESSAGE);
    if (refreshProjection) {
      await refreshProjection();
    }
    throw new ProjectionConflictError(CONFLICT_MESSAGE);
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || error.error || `HTTP ${response.status}`);
  }
  return response.json();
}

async function projectionCommand(url, body, { refreshProjection }) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (response.status === 409) {
    showConflict(CONFLICT_MESSAGE);
    await refreshProjection();
    throw new ProjectionConflictError(CONFLICT_MESSAGE);
  }
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

class CursorPager {
  constructor(baseUrl, render, pageSize = PAGE_SIZE) {
    this.baseUrl = baseUrl;
    this.render = render;
    this.pageSize = pageSize;
    this.cursor = null;
    this.history = [];
    this.items = [];
    this.nextCursor = null;
    this.hasMore = false;
    this.stateVersion = null;
  }

  async load(cursor = null, { keepHistory = false } = {}) {
    const params = new URLSearchParams({ limit: String(this.pageSize) });
    if (cursor) params.set("cursor", cursor);
    const url = `${this.baseUrl}?${params.toString()}`;
    const payload = await fetchProjection(url, {
      refreshProjection: () => this.load(null),
    });
    const collection = payload.collection || {};
    if (!Array.isArray(collection.items)) {
      throw new Error("Projection collection.items 缺失");
    }
    if (!keepHistory) this.history = [];
    this.cursor = cursor;
    this.items = collection.items;
    this.nextCursor = collection.nextCursor || null;
    this.hasMore = Boolean(collection.hasMore);
    this.stateVersion = collection.stateVersion || payload.stateVersion || null;
    this.render(this, payload);
    return payload;
  }

  async next() {
    if (!this.hasMore || !this.nextCursor) return;
    this.history.push(this.cursor);
    await this.load(this.nextCursor, { keepHistory: true });
  }

  async previous() {
    if (!this.history.length) return;
    const previousCursor = this.history.pop() ?? null;
    await this.load(previousCursor, { keepHistory: true });
  }
}

class ConnectionHealthManager {
  constructor() {
    this.eventSource = null;
    this.lastHeartbeatAt = 0;
    this.disconnectedAt = null;
    this.timer = null;
  }

  start() {
    this.open();
    this.timer = window.setInterval(() => this.evaluate(), 250);
    window.addEventListener("online", () => this.open());
    window.addEventListener("offline", () => this.noteDisconnected());
  }

  open() {
    if (this.eventSource) this.eventSource.close();
    documentRoot.dataset.connection = "connecting";
    connectionLabel.textContent = "正在连接";
    const source = new EventSource("/api/v63/events");
    this.eventSource = source;
    source.addEventListener("heartbeat", (event) => {
      this.lastHeartbeatAt = Date.now();
      this.disconnectedAt = null;
      const payload = JSON.parse(event.data);
      heartbeatTime.textContent = `心跳 ${formatBeijing(payload.generatedAt)}`;
      this.markConnected();
    });
    source.onopen = () => {
      this.disconnectedAt = null;
      if (!this.lastHeartbeatAt) this.lastHeartbeatAt = Date.now();
    };
    source.onerror = () => this.noteDisconnected();
  }

  noteDisconnected() {
    if (!this.disconnectedAt) this.disconnectedAt = Date.now();
  }

  evaluate() {
    const now = Date.now();
    const reference = Math.max(this.lastHeartbeatAt, this.disconnectedAt || 0);
    if (!reference || now - reference > STALE_AFTER_MS) this.markStale();
  }

  markConnected() {
    documentRoot.dataset.connection = "connected";
    connectionLabel.textContent = "实时连接正常";
    staleBanner.hidden = true;
  }

  markStale() {
    documentRoot.dataset.connection = "stale";
    connectionLabel.textContent = "连接中断 / 数据陈旧";
    staleBanner.hidden = false;
  }
}

function statusTone(status) {
  const value = String(status || "").toLowerCase();
  if (["healthy", "passed", "running", "connected", "ready", "active"].includes(value)) {
    return "success";
  }
  if (["blocked", "failed", "disconnected", "stale", "error"].includes(value)) {
    return "danger";
  }
  return "warning";
}

function statusBadge(status, label = null) {
  return `<span class="status-badge ${statusTone(status)}">${escapeHtml(label || status || "未知")}</span>`;
}

function metric(label, value, note = "", realtime = false) {
  return `<div class="metric">
    <label>${escapeHtml(label)}</label>
    <strong${realtime ? " data-realtime" : ""}>${value}</strong>
    ${note ? `<small>${escapeHtml(note)}</small>` : ""}
  </div>`;
}

function pageHeader(title, description, status = null) {
  pageTitle.textContent = title;
  return `<div class="page-heading">
    <div><h2>${escapeHtml(title)}</h2><p>${escapeHtml(description)}</p></div>
    ${status ? statusBadge(status.code || status, status.labelZh || status) : ""}
  </div>`;
}

function rawDetails(payload) {
  return `<details>
    <summary>高级审计字段</summary>
    <pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
  </details>`;
}

function pagerControls(pager, label) {
  return `<div class="pager">
    <button data-page-action="previous" title="上一页" aria-label="上一页" ${pager.history.length ? "" : "disabled"}>←</button>
    <span>${escapeHtml(label)}</span>
    <button data-page-action="next" title="下一页" aria-label="下一页" ${pager.hasMore ? "" : "disabled"}>→</button>
  </div>`;
}

function wirePager(pager) {
  app.querySelector('[data-page-action="previous"]')?.addEventListener("click", () => pager.previous());
  app.querySelector('[data-page-action="next"]')?.addEventListener("click", () => pager.next());
}

function issuesList(issues) {
  const rows = Array.isArray(issues) ? issues : [];
  if (!rows.length) return '<div class="empty-state">没有活动问题</div>';
  return `<ul class="issue-list">${rows.map((issue) => {
    const text = typeof issue === "string"
      ? issue
      : valueOf(issue, ["messageZh", "message", "code", "reason"], "未知问题");
    return `<li>${escapeHtml(text)}</li>`;
  }).join("")}</ul>`;
}

async function renderControl() {
  const [projection, health, lease] = await Promise.all([
    fetchProjection("/api/v63/projections/control-console"),
    fetchProjection("/api/v63/runtime/health"),
    fetchProjection("/api/v63/runtime/lease"),
  ]);
  const strategy = projection.strategy || {};
  const research = projection.research || {};
  const resultCounts = strategy.resultCounts || {};
  const currentPilot = strategy.currentPilot || null;
  const progress = Math.max(0, Math.min(100, Number(research.progressPercent || 0)));
  app.innerHTML = `
    ${pageHeader("总览控制台", "先看结论，再展开研究、运行与证据状态。", projection.statusPresentation)}
    <div class="metric-grid">
      ${metric("当前 Pilot", escapeHtml(pilotIdentity(currentPilot)))}
      ${metric("候选待复核", displayNumber(valueOf(strategy, ["pendingCandidateReviewCount"], 0)))}
      ${metric("可进入 Demo", displayNumber(valueOf(strategy, ["releaseReadyCount"], 0)))}
      ${metric("Runtime", escapeHtml(valueOf(health, ["status", "runtimeStatus"], "未知")), "", true)}
    </div>
    <section class="section split-grid">
      <div class="panel">
        <div class="panel-body">
          <div class="section-header"><div><h3>当前研究</h3><p>${escapeHtml(valueOf(research, ["researchRunId"], "没有活动研究"))}</p></div>${statusBadge(research.status)}</div>
          <p>${escapeHtml(valueOf(research, ["stage", "mode"], "等待任务"))}</p>
          <div class="progress-track" aria-label="研究进度"><span style="width:${progress}%"></span></div>
          <p class="muted">${progress}% · ${escapeHtml(valueOf(research, ["nextAction"], "暂无下一步"))}</p>
        </div>
      </div>
      <div class="panel">
        <div class="panel-body">
          <div class="section-header"><div><h3>执行安全边界</h3><p>只读投影，不授予执行权限</p></div></div>
          <dl class="key-value">
            <div><dt>Demo ARM</dt><dd data-realtime>${escapeHtml(valueOf(strategy, ["demoArm"], false))}</dd></div>
            <div><dt>Execution Lease</dt><dd data-realtime>${escapeHtml(valueOf(lease, ["leaseCount", "count", "status"], 0))}</dd></div>
            <div><dt>活动订单</dt><dd data-realtime>${displayNumber(valueOf(strategy, ["strategyOrderCount"], 0))}</dd></div>
            <div><dt>执行授权</dt><dd>${projection.executionAuthorized ? "已授权" : "未授权"}</dd></div>
          </dl>
        </div>
      </div>
    </section>
    <section class="section">
      <div class="section-header"><div><h3>正式候选</h3><p>从当前 Pilot 的只读身份投影进入策略证据页。</p></div></div>
      ${strategyCandidateLinks(currentPilot)}
    </section>
    <section class="section">
      <div class="section-header"><div><h3>历史结果概览</h3><p>只显示汇总，具体证据保留在审计字段。</p></div></div>
      <div class="metric-grid">
        ${metric("已通过", displayNumber(valueOf(resultCounts, ["passed", "formalPassed"], strategy.formalPassCount || 0)))}
        ${metric("未通过", displayNumber(valueOf(resultCounts, ["failed", "notPassed"], 0)))}
        ${metric("数据不足", displayNumber(valueOf(resultCounts, ["insufficientData", "dataInsufficient"], 0)))}
        ${metric("已归档", displayNumber(valueOf(resultCounts, ["archived"], strategy.archivedFailureCount || 0)))}
      </div>
    </section>
    ${rawDetails({ projection, health, lease })}
  `;
}

async function renderStrategy(strategyId) {
  const projection = await fetchProjection(`/api/v63/projections/strategies/${encodeURIComponent(strategyId)}`);
  const strategy = projection.strategy || projection.candidate || projection;
  const metrics = strategy.metrics || strategy.formalMetrics || {};
  const blockers = strategy.blockers || strategy.issues || [];
  const metricsAvailable = valueOf(strategy, ["metricsAvailable"], Object.keys(metrics).length > 0);
  const evidenceStatus = valueOf(strategy, ["evidenceStatus"], metricsAvailable ? "metrics_available" : "unknown");
  const evidenceExplanation = evidenceStatus === "identity_only"
    ? "仅有候选身份与 Formal 角色；当前权威投影未提供可展示的指标，页面不会补造数值。"
    : "指标和证据以当前权威 Projection 为准。";
  app.innerHTML = `
    ${pageHeader("单个策略工作台", `策略 ${strategyId} 的证据与状态投影。`, projection.statusPresentation)}
    <div class="metric-grid">
      ${metric("策略名称", escapeHtml(valueOf(strategy, ["displayNameZh", "displayName", "name", "strategyId"], strategyId)))}
      ${metric("Campaign", escapeHtml(valueOf(strategy, ["campaignId"], "--")))}
      ${metric("Formal 角色", escapeHtml(valueOf(strategy, ["formalRole"], "--")))}
      ${metric("证据状态", escapeHtml(evidenceStatus))}
      ${metric("PF", displayNumber(valueOf(metrics, ["profitFactor", "pf"])))}
      ${metric("平均净 R", displayNumber(valueOf(metrics, ["averageNetR", "avgNetR"])))}
      ${metric("最大回撤", displayNumber(valueOf(metrics, ["maximumDrawdown", "maxDrawdown"])))}
    </div>
    <div class="notice notice-info">${escapeHtml(evidenceExplanation)}</div>
    <section class="section split-grid">
      <div class="panel"><div class="panel-body">
        <h3>策略定义</h3>
        <dl class="key-value">
          <div><dt>方向</dt><dd>${escapeHtml(valueOf(strategy, ["direction"], "--"))}</dd></div>
          <div><dt>周期</dt><dd>${escapeHtml(valueOf(strategy, ["timeframe"], "--"))}</dd></div>
          <div><dt>Definition Hash</dt><dd>${escapeHtml(valueOf(strategy, ["definitionHash", "releaseHash"], "--"))}</dd></div>
          <div><dt>状态版本</dt><dd>${escapeHtml(projection.stateVersion)}</dd></div>
        </dl>
      </div></div>
      <div>
        <div class="section-header"><div><h3>阻塞与问题</h3><p>问题消失前不推断为可执行。</p></div></div>
        ${issuesList(blockers)}
      </div>
    </section>
    ${rawDetails(projection)}
  `;
}

function genericRows(items, columns) {
  return items.map((item) => `<tr>${columns.map((column) => {
    const value = valueOf(item, column.keys, "--");
    return `<td${column.realtime ? " data-realtime" : ""}>${column.format ? column.format(value, item) : escapeHtml(value)}</td>`;
  }).join("")}</tr>`).join("");
}

function renderEvolutionPage(pager, payload) {
  const columns = [
    { label: "候选 / 变体", keys: ["displayNameZh", "displayName", "variantName", "candidateId", "strategyId", "id"] },
    { label: "世代", keys: ["generation", "generationId", "iteration"] },
    { label: "状态", keys: ["statusZh", "status", "incubationStatus"] },
    { label: "成本稳健性", keys: ["costRobustness", "costRobustScore"] },
    { label: "因子稳定性", keys: ["factorStability", "factorStabilityScore"] },
    { label: "最近运行", keys: ["updatedAt", "lastRunAt"], format: (value) => formatBeijing(value) },
  ];
  app.innerHTML = `
    ${pageHeader("ML 隔离孵化舱", "候选变体按游标分页读取，每页替换，不将全池加载进浏览器。", payload.statusPresentation)}
    <section class="section">
      <div class="section-header"><div><h3>进化池</h3><p>当前页 ${pager.items.length} 条，单页上限 ${pager.pageSize}。</p></div></div>
      ${pager.items.length ? `<div class="table-wrap"><table><thead><tr>${columns.map((c) => `<th>${c.label}</th>`).join("")}</tr></thead><tbody>${genericRows(pager.items, columns)}</tbody></table></div>` : '<div class="empty-state">当前没有候选变体</div>'}
      ${pagerControls(pager, pager.hasMore ? "还有下一页" : "已到当前末页")}
    </section>
    ${rawDetails({ stateVersion: payload.stateVersion, collection: { pageSize: pager.pageSize, hasMore: pager.hasMore } })}
  `;
  wirePager(pager);
}

function renderDemoPage(pager, payload) {
  const columns = [
    { label: "策略", keys: ["displayNameZh", "displayName", "strategyName", "strategyId", "releaseId", "id"] },
    { label: "状态", keys: ["statusZh", "status", "runtimeStatus"] },
    { label: "信号", keys: ["signalCount", "matchedSignalCount", "signals"] },
    { label: "订单", keys: ["orderCount", "strategyOrderCount", "orders"], realtime: true },
    { label: "持仓", keys: ["positionCount", "openPositionCount", "positions"], realtime: true },
    { label: "浮动盈亏", keys: ["floatingPnl", "unrealizedPnl"], realtime: true, format: displayMoney },
  ];
  const scan = payload.scanFunnel || {};
  app.innerHTML = `
    ${pageHeader("Demo 舰队总览", "真实 Runtime、扫描漏斗、订单与持仓只读投影。", payload.runtimeStatus || payload.status)}
    <div class="metric-grid">
      ${metric("账户权益", displayMoney(payload.equity), "OKX Demo", true)}
      ${metric("今日盈亏", displayMoney(payload.todayPnl), "", true)}
      ${metric("浮动盈亏", displayMoney(payload.floatingPnl), "", true)}
      ${metric("运行策略", displayNumber(payload.runningStrategyCount), `ARM ${payload.armed ? "已开启" : "关闭"}`, true)}
    </div>
    <section class="section split-grid">
      <div>
        <div class="section-header"><div><h3>策略舰队</h3><p>当前页 ${pager.items.length} 条。</p></div></div>
        ${pager.items.length ? `<div class="table-wrap"><table><thead><tr>${columns.map((c) => `<th>${c.label}</th>`).join("")}</tr></thead><tbody>${genericRows(pager.items, columns)}</tbody></table></div>` : '<div class="empty-state">没有 Demo 策略记录</div>'}
        ${pagerControls(pager, pager.hasMore ? "还有下一页" : "已到当前末页")}
      </div>
      <div>
        <div class="section-header"><div><h3>扫描漏斗</h3><p>最近一轮全市场筛选。</p></div></div>
        <dl class="key-value">
          <div><dt>市场合约</dt><dd data-realtime>${displayNumber(valueOf(scan, ["marketContractCount", "marketContracts"], 0))}</dd></div>
          <div><dt>流动性合格</dt><dd data-realtime>${displayNumber(valueOf(scan, ["liquidityEligibleCount", "liquidityEligible"], 0))}</dd></div>
          <div><dt>深度扫描</dt><dd data-realtime>${displayNumber(valueOf(scan, ["depthEvaluatedCount", "depthEvaluated"], 0))}</dd></div>
          <div><dt>策略匹配</dt><dd data-realtime>${displayNumber(valueOf(scan, ["matchedSignalCount", "matched"], 0))}</dd></div>
        </dl>
        <div class="section-header section"><div><h3>活动问题</h3></div></div>
        ${issuesList(payload.issues)}
      </div>
    </section>
    ${rawDetails({ ...payload, collection: { pageSize: pager.pageSize, hasMore: pager.hasMore } })}
  `;
  wirePager(pager);
}

function renderLiveCollections(collections) {
  const { strategies, positions, orders, events } = collections;
  app.innerHTML = `
    ${pageHeader("实盘交易终端", "当前仅提供只读投影。Live ARM、订单和 Withdraw 均未由 V63.1 授权。", "not_run")}
    <div class="metric-grid">
      ${metric("运行策略", displayNumber(strategies.items.length), "当前页")}
      ${metric("持仓", displayNumber(positions.items.length), "当前页", true)}
      ${metric("订单", displayNumber(orders.items.length), "当前页", true)}
      ${metric("执行授权", "关闭", "executionAuthorized=false")}
    </div>
    ${simpleCollectionSection("策略列表", strategies, ["displayNameZh", "displayName", "strategyId", "releaseId", "id"])}
    ${simpleCollectionSection("当前持仓", positions, ["instrumentId", "symbol", "instId", "id"], true)}
    ${simpleCollectionSection("订单", orders, ["instrumentId", "symbol", "orderId", "id"], true)}
    ${simpleCollectionSection("事件", events, ["messageZh", "message", "eventType", "id"], true)}
  `;
}

function simpleCollectionSection(title, pager, labelKeys, realtime = false) {
  const rows = pager.items.map((item) => `<tr>
    <td${realtime ? " data-realtime" : ""}>${escapeHtml(valueOf(item, labelKeys, "--"))}</td>
    <td>${escapeHtml(valueOf(item, ["statusZh", "status", "state"], "--"))}</td>
    <td${realtime ? " data-realtime" : ""}>${escapeHtml(valueOf(item, ["updatedAt", "createdAt", "timestamp"], "--"))}</td>
  </tr>`).join("");
  return `<section class="section">
    <div class="section-header"><div><h3>${escapeHtml(title)}</h3><p>当前页 ${pager.items.length} 条。</p></div></div>
    ${rows ? `<div class="table-wrap"><table><thead><tr><th>对象</th><th>状态</th><th>更新时间</th></tr></thead><tbody>${rows}</tbody></table></div>` : `<div class="empty-state">没有${escapeHtml(title)}记录</div>`}
  </section>`;
}

async function renderRoute() {
  setError("");
  const path = window.location.pathname;
  document.querySelectorAll("[data-route]").forEach((link) => link.classList.remove("active"));
  try {
    if (path === "/v63a" || path === "/v63a/" || path === "/v63a/control") {
      document.querySelector('[data-route="control"]')?.classList.add("active");
      await renderControl();
      return;
    }
    if (path.startsWith("/v63a/strategy/")) {
      document.querySelector('[data-route="control"]')?.classList.add("active");
      await renderStrategy(decodeURIComponent(path.slice("/v63a/strategy/".length)));
      return;
    }
    if (path === "/v63a/evolution") {
      document.querySelector('[data-route="evolution"]')?.classList.add("active");
      const pager = new CursorPager("/api/v63/projections/evolution-pool", renderEvolutionPage);
      await pager.load();
      return;
    }
    if (path === "/v63a/demo") {
      document.querySelector('[data-route="demo"]')?.classList.add("active");
      const pager = new CursorPager("/api/v63/projections/demo-fleet", renderDemoPage);
      await pager.load();
      return;
    }
    if (path === "/v63a/live") {
      document.querySelector('[data-route="live"]')?.classList.add("active");
      const result = {};
      const names = ["strategies", "positions", "orders", "events"];
      await Promise.all(names.map(async (name) => {
        const pager = new CursorPager(`/api/v63/projections/live-terminal/${name}`, () => {});
        await pager.load();
        result[name] = pager;
      }));
      renderLiveCollections(result);
      return;
    }
    app.innerHTML = '<div class="empty-state">页面不存在</div>';
  } catch (error) {
    if (error instanceof ProjectionConflictError) return;
    setError(`Projection 读取失败：${error.message}`);
    app.innerHTML = '<div class="empty-state">无法读取当前页面的真实状态</div>';
  }
}

function updateClock() {
  document.getElementById("beijing-clock").textContent =
    `${formatBeijing(new Date())}（北京时间）`;
}

updateClock();
window.setInterval(updateClock, 1000);
new ConnectionHealthManager().start();
renderRoute();
