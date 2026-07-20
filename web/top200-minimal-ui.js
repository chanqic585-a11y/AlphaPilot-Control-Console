(function () {
  "use strict";

  const POLL_MS = 3000;
  let strategyLoading = false;
  let demoLoading = false;

  const byId = (id) => document.getElementById(id);

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  async function fetchJson(path) {
    const response = await fetch(path, { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.error || `HTTP ${response.status}`);
    }
    return payload;
  }

  function formatValue(value, suffix = "") {
    if (value === null || value === undefined || value === "") return "--";
    return `${value}${suffix}`;
  }

  function formatTimestamp(value) {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
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

  function setIssue(element, issues, isError = false) {
    if (!element) return;
    const visible = Array.isArray(issues) && issues.length > 0;
    element.hidden = !visible;
    element.classList.toggle("is-error", Boolean(isError));
    element.textContent = visible
      ? issues.map((item) => item.message || item.code || String(item)).join("；")
      : "";
  }

  function renderStrategyCard(release) {
    return `
      <article class="top200-strategy-card">
        <div>
          <strong>${escapeHtml(release.name || release.releaseId)}</strong>
          <small>${escapeHtml(release.type || "portfolio")} · ${escapeHtml(release.releaseId)}</small>
        </div>
        <span class="top200-state-badge">${escapeHtml(release.statusLabel || release.status)}</span>
        <span>Universe ${escapeHtml(release.actualInstrumentCount || 0)} / ${escapeHtml(release.maximumInstrumentCount || 200)}</span>
        <span>${release.approved ? "已批准" : "等待精确批准"}</span>
      </article>`;
  }

  async function refreshStrategy() {
    if (strategyLoading || !byId("top200MinimalStrategy")) return;
    strategyLoading = true;
    try {
      const [factory, summary, releases] = await Promise.all([
        fetchJson("/api/research-factory/summary"),
        fetchJson("/api/strategy/summary"),
        fetchJson("/api/strategy/releases"),
      ]);
      const current = (releases.releases || []).find((item) => item.status === "can_enter_demo");
      const progress = Math.max(0, Math.min(100, Number(factory.progressPercent || 0)));
      const track = byId("top200ResearchProgressBar")?.parentElement;
      byId("top200ResearchStage").textContent = factory.stage === "release_ready" ? "Release 已冻结" : factory.stage;
      byId("top200ResearchProgressLabel").textContent = `${factory.completedCount} / ${factory.totalCount}`;
      byId("top200ResearchProgressBar").style.width = `${progress}%`;
      if (track) track.setAttribute("aria-valuenow", String(progress));
      byId("top200ResearchCurrent").textContent = `当前：${factory.currentCandidate || "--"}`;
      byId("top200CanEnterDemo").textContent = summary.resultCounts.canEnterDemo;
      byId("top200NeedsForward").textContent = summary.resultCounts.needsForwardValidation;
      byId("top200Failed").textContent = summary.resultCounts.failed;
      byId("top200DataInsufficient").textContent = summary.resultCounts.dataInsufficient;
      byId("top200SystemIssue").textContent = summary.resultCounts.systemIssue;
      byId("top200ResultRoute").textContent = summary.approved ? "已批准" : "等待批准";
      byId("top200StrategyResults").innerHTML = current
        ? renderStrategyCard(current)
        : '<div class="top200-empty-state">当前没有可进入 Demo 的 Release。</div>';
      byId("top200ForwardCount").textContent = summary.resultCounts.needsForwardValidation;
      byId("top200ForwardList").textContent = summary.resultCounts.needsForwardValidation
        ? "存在需要新闭合交易的策略。"
        : "当前没有正在收集的闭合策略交易。";
      byId("top200StrategyAudit").textContent = JSON.stringify({
        researchRunId: factory.researchRunId,
        releaseId: current?.releaseId || null,
        releaseHash: current?.releaseHash || null,
        universePolicyHash: current?.universePolicyHash || null,
        universeSnapshotHash: current?.universeSnapshotHash || null,
        riskOverlayHash: current?.riskOverlayHash || null,
        formalPass: current?.formalPass || false,
        approved: summary.approved,
        demoArm: summary.demoArm,
        strategyOrderCount: summary.strategyOrderCount,
        route: summary.route,
      }, null, 2);
      byId("top200StrategyUpdatedAt").textContent = `最后更新 ${formatTimestamp(summary.updatedAt)}`;
      setIssue(
        byId("top200StrategyIssue"),
        summary.approved ? [] : [{ message: "Release 已冻结，当前未批准、未 ARM、未产生策略订单。" }],
      );
    } catch (error) {
      setIssue(byId("top200StrategyIssue"), [{ message: `状态读取失败：${error.message}` }], true);
      byId("top200SystemIssue").textContent = "1";
    } finally {
      strategyLoading = false;
    }
  }

  function renderDemoStrategyCard(strategy) {
    return `
      <article class="top200-strategy-card">
        <div>
          <strong>${escapeHtml(strategy.name)}</strong>
          <small>${escapeHtml((strategy.timeframes || []).join(" / "))} · ${escapeHtml(strategy.releaseId)}</small>
        </div>
        <span class="top200-state-badge">${strategy.status === "waiting_approval" ? "等待批准" : escapeHtml(strategy.status)}</span>
        <span>扫描 ${escapeHtml(strategy.scanInstrumentCount)} 个合约</span>
        <span>持仓 ${escapeHtml(strategy.openPositionCount)} · 今日 ${formatValue(strategy.todayPnl)}</span>
      </article>`;
  }

  function renderPositions(positions) {
    if (!positions.length) return '<div class="top200-empty-state">当前没有策略持仓。</div>';
    const rows = positions.map((item) => `
      <tr>
        <td>${escapeHtml(item.instrumentId)}</td><td>${escapeHtml(item.side)}</td>
        <td>${escapeHtml(item.quantity)}</td><td>${escapeHtml(item.leverage)}</td>
        <td>${escapeHtml(item.entryPrice)}</td><td>${escapeHtml(item.markPrice)}</td>
        <td>${escapeHtml(item.unrealizedPnl)}</td><td>${escapeHtml(item.stopLoss)}</td>
        <td>${escapeHtml(item.exitPolicy)}</td><td>${escapeHtml(item.status)}</td>
      </tr>`).join("");
    return `<table class="top200-table"><thead><tr><th>币种</th><th>方向</th><th>数量</th><th>杠杆</th><th>入场价</th><th>当前价</th><th>浮动盈亏</th><th>止损</th><th>退出</th><th>状态</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function renderOrders(orders) {
    if (!orders.length) return '<div class="top200-empty-state">当前没有异常策略订单。</div>';
    const rows = orders.map((item) => `
      <tr><td>${escapeHtml(item.instrumentId)}</td><td>${escapeHtml(item.status)}</td><td>${escapeHtml(item.reason)}</td><td>${escapeHtml(item.updatedAt)}</td></tr>`).join("");
    return `<table class="top200-table"><thead><tr><th>币种</th><th>状态</th><th>原因</th><th>更新时间</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  async function refreshDemo() {
    if (demoLoading || !byId("top200MinimalDemo")) return;
    demoLoading = true;
    try {
      const [summary, strategies, positions, orders, universe, reconciliation] = await Promise.all([
        fetchJson("/api/demo/summary"),
        fetchJson("/api/demo/strategies"),
        fetchJson("/api/demo/positions"),
        fetchJson("/api/demo/orders"),
        fetchJson("/api/demo/universe"),
        fetchJson("/api/demo/reconciliation"),
      ]);
      byId("top200DemoConnection").textContent = summary.connectionStatus === "engineering_smoke_passed" ? "工程链路通过" : "异常";
      byId("top200DemoEquity").textContent = formatValue(summary.equity);
      byId("top200DemoTodayPnl").textContent = formatValue(summary.todayPnl);
      byId("top200DemoFloatingPnl").textContent = formatValue(summary.floatingPnl);
      byId("top200DemoRunningCount").textContent = summary.runningStrategyCount;
      byId("top200DemoPositionCount").textContent = summary.openPositionCount;
      byId("top200DemoUniverseCount").textContent = `${universe.actualInstrumentCount} / ${universe.maximumInstrumentCount}`;
      byId("top200RunApprovedButton").disabled = !summary.canRunApprovedStrategies;
      byId("top200RunApprovedButton").title = summary.canRunApprovedStrategies
        ? "使用现有受控命令运行已批准策略"
        : "当前没有已批准且可 ARM 的策略";
      byId("top200DemoStrategyList").innerHTML = (strategies.strategies || []).length
        ? strategies.strategies.map(renderDemoStrategyCard).join("")
        : '<div class="top200-empty-state">当前没有 Demo 策略。</div>';
      const positionRows = positions.positions || [];
      byId("top200DemoPositionsCount").textContent = positionRows.length;
      byId("top200DemoPositions").innerHTML = renderPositions(positionRows);
      const orderRows = orders.orders || [];
      byId("top200DemoOrderCount").textContent = orderRows.length;
      byId("top200DemoOrders").innerHTML = renderOrders(orderRows);
      byId("top200DemoOrdersDetails").open = orderRows.length > 0;
      byId("top200DemoAudit").textContent = JSON.stringify({
        policyId: universe.policyId,
        policyHash: universe.policyHash,
        snapshotHash: universe.snapshotHash,
        utcDate: universe.utcDate,
        actualInstrumentCount: universe.actualInstrumentCount,
        maximumInstrumentCount: universe.maximumInstrumentCount,
        funnel: universe.funnel,
        reconciliation,
        engineeringSmoke: summary.engineeringSmoke,
      }, null, 2);
      byId("top200DemoUpdatedAt").textContent = `最后更新 ${formatTimestamp(summary.updatedAt)}`;
      setIssue(byId("top200DemoIssue"), summary.issues || []);
    } catch (error) {
      setIssue(byId("top200DemoIssue"), [{ message: `状态读取失败：${error.message}` }], true);
      byId("top200DemoConnection").textContent = "异常";
    } finally {
      demoLoading = false;
    }
  }

  function start() {
    refreshStrategy();
    refreshDemo();
    window.setInterval(refreshStrategy, POLL_MS);
    window.setInterval(refreshDemo, POLL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
