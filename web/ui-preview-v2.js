(() => {
  "use strict";

  const page = document.documentElement.dataset.previewPage;
  const byId = (id) => document.getElementById(id);
  const value = (input, fallback = "--") => input === null || input === undefined || input === "" ? fallback : String(input);
  const rows = (payload, key) => Array.isArray(payload?.[key]) ? payload[key] : [];
  const escapeHtml = (input) => value(input).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  })[character]);
  const formatMoney = (input) => {
    const number = Number(input);
    return input !== null && input !== undefined && Number.isFinite(number)
      ? `${number >= 0 ? "+" : ""}${number.toFixed(2)} USDT`
      : "不可用";
  };
  const formatTime = (input) => {
    if (!input) return "--";
    const date = new Date(input);
    return Number.isNaN(date.getTime()) ? String(input) : new Intl.DateTimeFormat("zh-CN", {
      timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
    }).format(date);
  };

  async function getJson(path) {
    const response = await fetch(path, { headers: { Accept: "application/json" }, cache: "no-store" });
    if (!response.ok) throw new Error(`${response.status} ${path}`);
    return response.json();
  }

  function setPnl(element, input) {
    if (!element) return;
    const number = Number(input);
    element.textContent = formatMoney(input);
    element.classList.toggle("positive", Number.isFinite(number) && number > 0);
    element.classList.toggle("negative", Number.isFinite(number) && number < 0);
  }

  function showIssue(message) {
    const banner = byId("issueBanner");
    if (!banner) return;
    banner.hidden = !message;
    banner.textContent = message || "";
  }

  function emptyRow(columns, text) {
    return `<tr><td colspan="${columns}" class="empty">${escapeHtml(text)}</td></tr>`;
  }

  function renderDemoStrategy(item) {
    const name = value(item.displayName || item.strategyName || item.name || item.releaseId, "未命名策略");
    const status = value(item.status || item.runtimeStatus, "等待");
    const timeframe = Array.isArray(item.timeframes) ? item.timeframes.join(" / ") : value(item.timeframe);
    const scanCount = value(item.scanInstrumentCount, "不可用");
    return `<article class="strategy-item" tabindex="0" data-release-id="${escapeHtml(item.releaseId)}"><header><h3>${escapeHtml(name)}</h3><span class="strategy-state">${escapeHtml(status)}</span></header><p>${escapeHtml(timeframe)} · 扫描 ${escapeHtml(scanCount)} 个合约</p><p>持仓 ${escapeHtml(value(item.openPositionCount, "0"))} · 今日 ${escapeHtml(formatMoney(item.todayPnl))}</p></article>`;
  }

  function openStrategyDrawer(item) {
    const drawer = byId("strategyDrawer");
    const backdrop = byId("drawerBackdrop");
    if (!drawer || !backdrop) return;
    byId("drawerTitle").textContent = value(item.name || item.releaseId, "策略详情");
    const summary = [
      ["状态", value(item.status, "等待")],
      ["周期", Array.isArray(item.timeframes) ? item.timeframes.join(" / ") : value(item.timeframe)],
      ["扫描范围", `${value(item.scanInstrumentCount, "不可用")} 个合约`],
      ["最后扫描", formatTime(item.latestScanAt)],
      ["当前持仓", value(item.openPositionCount, "0")],
      ["今日盈亏", formatMoney(item.todayPnl)],
    ];
    byId("drawerSummary").innerHTML = summary.map(([key, itemValue]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(itemValue)}</dd></div>`).join("");
    drawer.hidden = false;
    backdrop.hidden = false;
    byId("closeDrawer")?.focus();
  }

  function closeStrategyDrawer() {
    byId("strategyDrawer")?.setAttribute("hidden", "");
    byId("drawerBackdrop")?.setAttribute("hidden", "");
  }

  async function refreshDemo() {
    const [summary, strategies, positions, orders, universe, reconciliation] = await Promise.all([
      getJson("/api/demo/summary"),
      getJson("/api/demo/strategies"),
      getJson("/api/demo/positions"),
      getJson("/api/demo/orders"),
      getJson("/api/demo/universe"),
      getJson("/api/demo/reconciliation"),
    ]);
    byId("connectionStatus").textContent = value(summary.connectionStatus, "异常");
    byId("accountEquity").textContent = formatMoney(summary.equity);
    byId("availableBalance").textContent = formatMoney(summary.availableBalance);
    byId("equityMeta").textContent = summary.equity === null || summary.equity === undefined
      ? "不可用 · 未提供账户快照"
      : `${formatTime(summary.updatedAt)} · ${value(summary.equitySource, "账户快照")}`;
    setPnl(byId("todayPnl"), summary.todayPnl);
    setPnl(byId("floatingPnl"), summary.floatingPnl);
    byId("runningStrategies").textContent = value(summary.runningStrategyCount, "0");
    byId("openPositions").textContent = value(summary.openPositionCount, "0");
    byId("universeStatus").textContent = `TOP200 ${value(universe.actualInstrumentCount, "--")}`;
    const funnel = universe.funnel || {};
    byId("marketCount").textContent = value(funnel.publicInstrumentCount);
    byId("demoUniverseCount").textContent = value(funnel.authenticatedDemoInstrumentCount);
    byId("liquidityCount").textContent = value(funnel.eligibleInstrumentCount);
    byId("deepScreenCount").textContent = value(funnel.selectedInstrumentCount);
    byId("signalCount").textContent = value(summary.matchability?.signalCount30d);
    byId("scanUpdatedAt").textContent = universe.utcDate ? `快照 ${value(universe.utcDate)}` : "等待快照";

    const strategyRows = rows(strategies, "strategies");
    byId("strategyList").innerHTML = strategyRows.length ? strategyRows.map(renderDemoStrategy).join("") : '<p class="empty">当前没有 Demo 策略。</p>';
    byId("strategyList").querySelectorAll(".strategy-item").forEach((element, index) => {
      const activate = () => openStrategyDrawer(strategyRows[index]);
      element.addEventListener("click", activate);
      element.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") activate();
      });
    });

    const positionItems = rows(positions, "positions");
    byId("positionCount").textContent = String(positionItems.length);
    byId("positionRows").innerHTML = positionItems.length ? positionItems.map((item) => `<tr><td>${escapeHtml(item.instrumentId || item.symbol)}</td><td>${escapeHtml(item.side || item.direction)}</td><td>${escapeHtml(item.quantity || item.size)}</td><td>${escapeHtml(item.entryPrice)}</td><td>${escapeHtml(formatMoney(item.unrealizedPnl))}</td></tr>`).join("") : emptyRow(5, "当前没有策略持仓。");

    const orderItems = rows(orders, "orders");
    byId("orderCount").textContent = String(orderItems.length);
    byId("orderRows").innerHTML = orderItems.length ? orderItems.map((item) => `<tr><td>${escapeHtml(formatTime(item.createdAt || item.updatedAt))}</td><td>${escapeHtml(item.instrumentId || item.symbol)}</td><td>${escapeHtml(item.status)}</td><td>${escapeHtml(item.reason || item.errorCode)}</td></tr>`).join("") : emptyRow(4, "当前没有异常策略订单。");

    const issues = Array.isArray(summary.issues) ? summary.issues : [];
    showIssue(issues.length ? value(issues[0].message || issues[0].code) : "");
    byId("auditSummary").textContent = JSON.stringify({
      releaseId: summary.releaseId || null,
      releaseHash: summary.releaseHash || null,
      riskOverlayHash: summary.riskOverlayHash || null,
      armed: Boolean(summary.armed),
      reconciliation,
    }, null, 2);
    byId("updatedAt").textContent = `更新 ${formatTime(summary.updatedAt || new Date().toISOString())}`;
  }

  function gate(element, passed, yes, no) {
    element.textContent = passed ? yes : no;
    element.classList.toggle("passed", passed);
  }

  async function refreshLive() {
    const readiness = await getJson("/api/live/canary-readiness");
    const technical = Boolean(readiness.adaptiveLearning?.passed);
    const approved = readiness.execution?.approvalStatus === "approved";
    const armed = readiness.execution?.armStatus === "armed";
    gate(byId("technicalGate"), technical, "已通过", "未通过");
    gate(byId("approvalGate"), approved, "已批准", "未批准");
    gate(byId("armGate"), armed, "已 ARM", "未 ARM");
    gate(byId("approvalGateAudit"), approved, "已批准", "未批准");
    gate(byId("armGateAudit"), armed, "已 ARM", "未 ARM");
    byId("connectionStatus").textContent = readiness.readOnly ? "只读" : "在线";
    byId("liveReleaseStatus").textContent = value(readiness.statusLabel || readiness.status, "草稿");
    byId("liveRelease").textContent = value(readiness.release?.releaseId, "草稿");
    byId("modelMode").textContent = value(readiness.adaptiveLearning?.modelMode, "未就绪");
    byId("accountEquity").textContent = formatMoney(readiness.equity);
    byId("availableBalance").textContent = formatMoney(readiness.availableBalance);
    setPnl(byId("todayPnl"), readiness.todayPnl);
    byId("strategyOrders").textContent = value(readiness.orders?.count, "0");
    byId("openPositions").textContent = value(readiness.positions?.count, "0");

    const blockers = Array.isArray(readiness.adaptiveLearning?.blockers) ? readiness.adaptiveLearning.blockers : [];
    byId("blockerCount").textContent = String(blockers.length);
    byId("blockerList").innerHTML = blockers.length ? blockers.map((item) => `<li>${escapeHtml(item.message || item.code || item)}</li>`).join("") : "<li>当前没有技术阻塞。</li>";
    const risk = readiness.risk || {};
    byId("riskSummary").innerHTML = [
      ["Live", armed ? "已 ARM" : "关闭"],
      ["Withdraw", readiness.execution?.withdrawAllowed ? "异常开启" : "关闭"],
      ["分配资金", formatMoney(risk.allocatedCapitalUSDT)],
      ["单笔风险", formatMoney(risk.riskPerTradeUSDT)],
      ["最大持仓", value(risk.maximumConcurrentPositions)],
      ["最大杠杆", risk.maximumLeverage ? `${value(risk.maximumLeverage)}x` : "不可用"],
    ].map(([key, item]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(item)}</dd></div>`).join("");
    const issues = Array.isArray(readiness.issues) ? readiness.issues : [];
    showIssue(armed || readiness.execution?.withdrawAllowed
      ? "安全状态异常：Live 或 Withdraw 不应在当前阶段开启。"
      : issues.length ? value(issues[0].message || issues[0].code) : "");
    byId("auditSummary").textContent = JSON.stringify({
      releaseId: readiness.release?.releaseId || null,
      releaseHash: readiness.audit?.releaseHash || null,
      modelPolicyHash: readiness.audit?.modelPolicyHash || null,
      riskOverlayHash: readiness.audit?.riskOverlayHash || null,
      technicalReadinessPassed: technical,
      exactApprovalPassed: approved,
      liveArmed: armed,
      withdrawEnabled: Boolean(readiness.execution?.withdrawAllowed),
    }, null, 2);
    byId("updatedAt").textContent = `更新 ${formatTime(readiness.release?.generatedAt || new Date().toISOString())}`;
  }

  async function refresh() {
    const button = byId("refreshButton");
    if (button) button.disabled = true;
    try {
      if (page === "demo") await refreshDemo();
      if (page === "live") await refreshLive();
    } catch (error) {
      showIssue(`状态读取失败：${error.message}`);
    } finally {
      if (button) button.disabled = false;
    }
  }

  byId("refreshButton")?.addEventListener("click", refresh);
  byId("closeDrawer")?.addEventListener("click", closeStrategyDrawer);
  byId("drawerBackdrop")?.addEventListener("click", closeStrategyDrawer);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeStrategyDrawer();
  });
  refresh();
  window.setInterval(refresh, 15000);
})();
