const statusOptions = [
  "research_only",
  "local_paper_ready",
  "forward_testing",
  "dry_run_candidate",
  "disabled",
];

const statusLabels = {
  research_only: "研究观察",
  local_paper_ready: "本地模拟候选",
  forward_testing: "前向观察",
  dry_run_candidate: "Dry-run 候选",
  disabled: "禁用",
  waiting_for_import: "等待导入",
  ok: "正常",
  failed: "失败",
  public_only: "仅公共行情",
  private_disabled: "私有权限关闭",
  not_probed: "未探测",
};

const readinessLabels = {
  local_paper_review_ready: "本地模拟复核就绪",
  research_observer_ready: "研究观察就绪",
  needs_quant_report_import: "等待导入策略报告",
};

const healthLabels = {
  healthy_research_runtime: "研究运行状态良好",
  partial_research_runtime: "研究运行状态部分就绪",
  needs_more_data: "需要更多数据",
  runtime_contract_ready: "运行契约就绪",
  runtime_contract_partial: "运行契约部分就绪",
  runtime_contract_needs_data: "运行契约需要数据",
};

const sectionLabels = {
  overview: "驾驶舱",
  command: "策略总控",
  runtime: "运行监控",
  exchanges: "公共行情",
  mobile: "手机控制台",
  audit: "审计日志",
};

let latestStrategies = [];

function el(id) {
  return document.getElementById(id);
}

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`${url} failed: ${response.status}`);
  return response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`${url} failed: ${response.status}`);
  return response.json();
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toFixed(digits);
}

function formatPercent(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return `${Number(value).toFixed(digits)}%`;
}

function formatDate(value) {
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
    hour12: false,
  }).format(date);
}

function tStatus(value) {
  return statusLabels[value] || value || "--";
}

function tReadiness(value) {
  return readinessLabels[value] || value || "--";
}

function tHealth(value) {
  return healthLabels[value] || value || "--";
}

function badge(value) {
  const normalized = String(value ?? "--");
  const label = tStatus(normalized);
  let kind = "";
  if (["local_paper_ready", "ok", "public_only"].includes(normalized)) kind = "ok";
  if (["research_only", "waiting_for_import", "not_probed", "forward_testing"].includes(normalized)) kind = "warn";
  if (normalized.includes("false") || normalized === "failed" || normalized === "disabled") kind = "danger";
  return `<span class="badge ${kind}">${label}</span>`;
}

function pickPrimaryStrategy(strategies) {
  return (
    strategies.find((item) => item.consoleStatus === "local_paper_ready") ||
    strategies.find((item) => item.consoleStatus === "forward_testing") ||
    strategies[0] ||
    null
  );
}

function getMetrics(strategy) {
  return (strategy && strategy.metrics) || {};
}

function getSignalCount(strategy) {
  const metrics = getMetrics(strategy);
  return strategy?.selectedSignalCount ?? metrics.filledSignalCount ?? metrics.tradeCount ?? null;
}

function renderCommandCenter(strategies, reports, mobile) {
  const primary = pickPrimaryStrategy(strategies);
  const metrics = getMetrics(primary);
  const summary = mobile.commandSummary || {};
  const readyCount = strategies.filter((item) => item.consoleStatus === "local_paper_ready").length;
  const researchCount = strategies.filter((item) => item.consoleStatus === "research_only").length;
  const connected = mobile.exchangeConnectivity?.connectedExchangeCount ?? 0;
  const totalExchangeResults = mobile.exchangeConnectivity?.resultCount ?? 0;

  el("strategyCount").textContent = String(strategies.length);
  el("reportCount").textContent = String(reports.length);
  el("exchangeConnectedCount").textContent = `${connected}/${totalExchangeResults}`;
  el("readyStrategyCount").textContent = String(readyCount);
  el("researchStrategyCount").textContent = String(researchCount);
  el("strategyDonut").textContent = strategies.length ? String(strategies.length) : "--";

  const hasReady = readyCount > 0;
  el("portfolioBias").textContent = hasReady ? "本地模拟候选可用" : "研究观察模式";
  el("portfolioMeta").textContent = hasReady
    ? `${readyCount}/${strategies.length} 个策略处于本地模拟候选`
    : "尚无可进入模拟观察的策略包";

  el("probeSymbolLabel").textContent = mobile.exchangeConnectivity?.symbol || "--";
  el("probeTimeframeLabel").textContent = mobile.exchangeConnectivity?.timeframe || "--";
  el("latestProbeAt").textContent = formatDate(mobile.exchangeConnectivity?.latestProbeAt);

  el("activeStrategyTitle").textContent = primary?.title || "--";
  el("activeStrategyStatus").innerHTML = primary ? badge(primary.consoleStatus) : "--";
  el("signalCount").textContent = getSignalCount(primary) ?? "--";
  el("signalMeta").textContent = primary?.version ? `${primary.version} 本地样本` : "本地样本";
  el("paperPositionLimit").textContent = primary?.maxConcurrentPositions
    ? `上限 ${primary.maxConcurrentPositions}`
    : "无真实持仓";
  el("backtestPf").textContent = metrics.profitFactor ? `PF ${formatNumber(metrics.profitFactor)}` : "--";
  el("backtestMeta").textContent = `RR ${formatNumber(metrics.rewardRiskRatio)} / DD ${formatPercent(metrics.maxDrawdownPct)}`;
  el("metricWinRate").textContent = formatPercent(metrics.winRatePct);
  el("metricRewardRisk").textContent = formatNumber(metrics.rewardRiskRatio);
  el("metricDrawdown").textContent = formatPercent(metrics.maxDrawdownPct);
  el("metricStopLoss").textContent = primary?.stopLossPct ? formatPercent(primary.stopLossPct * 100, 1) : "--";
  el("metricTargetR").textContent = primary?.targetRMultiple ? `${formatNumber(primary.targetRMultiple, 1)}R` : "--";
  el("executionLock").textContent = mobile.safetyBoundary?.orderCreationAllowed ? "异常开启" : "关闭";
  el("metricHealthScore").textContent = summary.healthScore === undefined ? "--" : `${summary.healthScore}/100`;
  el("metricReadiness").textContent = tReadiness(summary.readiness);
}

function renderRuntimeMonitor(strategies, mobile) {
  const primary = pickPrimaryStrategy(strategies);
  const summary = mobile.commandSummary || {};
  const exchange = mobile.exchangeConnectivity || {};
  const runtimeStatus = mobile.runtimeStatus || {};
  const signalTape = mobile.signalTape || {};
  const paperLedger = mobile.paperObservationLedger || {};
  const runtimeHealth = runtimeStatus.runtimeHealth || {};
  const signalSummary = signalTape.summary || {};
  const paperSummary = paperLedger.summary || {};
  const connected = exchange.connectedExchangeCount ?? 0;
  const total = exchange.resultCount ?? 0;
  const executionLocked = !mobile.safetyBoundary?.orderCreationAllowed;

  el("runtimeStrategy").textContent =
    runtimeStatus.activeStrategy?.strategyTitle || summary.activeStrategyTitle || primary?.title || "--";
  el("runtimeStrategyMeta").textContent = [
    runtimeStatus.activeStrategy?.strategyVersion || summary.activeStrategyVersion || primary?.version || "--",
    tStatus(runtimeStatus.activeStrategy?.status || summary.activeStatus || primary?.consoleStatus),
  ].filter(Boolean).join(" / ");
  el("runtimeSignals").textContent = runtimeStatus.signalTapeCount ?? summary.signalCount ?? getSignalCount(primary) ?? "--";
  el("runtimeHealth").textContent = runtimeHealth.score === undefined
    ? summary.healthScore === undefined ? "--" : `${summary.healthScore}/100`
    : `${runtimeHealth.score}/100`;
  el("runtimeHealthLabel").textContent = tHealth(runtimeHealth.label || summary.healthLabel);
  el("runtimeExecutionLock").textContent = executionLocked ? "关闭" : "异常开启";
  el("runtimeNextStep").textContent = runtimeStatus.nextStep || summary.nextStep || "等待本地策略报告导入。";
  el("runtimeDataHealth").textContent = `公共行情连接 ${connected}/${total}，最近探测 ${formatDate(exchange.latestProbeAt)}。`;
  el("runtimeSignalTapeSummary").textContent =
    `源信号 ${signalSummary.totalSourceSignals ?? "--"}，展示 ${signalSummary.publishedSignalCount ?? "--"}，最近 ${formatDate(signalSummary.latestSignalTime)}。`;
  el("runtimePaperLedgerSummary").textContent =
    `观察 ${paperSummary.totalObservations ?? "--"}，胜率 ${formatPercent(paperSummary.winRatePct)}，PF ${formatNumber(paperSummary.profitFactor)}。`;
  renderRuntimeSignalTape(signalTape.signals || []);
  renderRuntimePaperObservations(paperLedger.observations || []);
}

function renderRuntimeSignalTape(signals) {
  el("runtimeSignalTapeList").innerHTML = signals.slice(0, 6).map((item) => `
    <div class="compact-row">
      <strong>${item.symbol || "--"}</strong>
      <span>${item.direction || "--"} · ${item.timeframe || "--"}</span>
      <span>${formatDate(item.entryReferenceTime)} · R ${formatNumber(item.rMultiple)}</span>
    </div>
  `).join("") || '<div class="compact-empty">暂无信号流水。</div>';
}

function renderRuntimePaperObservations(observations) {
  el("runtimePaperObservationList").innerHTML = observations.slice(0, 6).map((item) => `
    <div class="compact-row">
      <strong>${item.symbol || "--"}</strong>
      <span>${item.exitReason || "--"} · ${item.status || "--"}</span>
      <span>${formatDate(item.exitTime)} · R ${formatNumber(item.rMultiple)}</span>
    </div>
  `).join("") || '<div class="compact-empty">暂无纸面观察。</div>';
}

function renderStrategies(strategies) {
  latestStrategies = strategies;

  if (!strategies.length) {
    el("strategyList").innerHTML = '<div class="item">未发现策略包。请在 Quant Engine 生成报告后点击“导入报告”。</div>';
    return;
  }

  const rows = strategies.map((item) => {
    const metrics = item.metrics || {};
    return `
      <tr>
        <td>
          <strong>${item.version || "--"}</strong>
          <div>${item.title || item.strategyId}</div>
          <small>${item.strategyId}</small>
        </td>
        <td>${badge(item.consoleStatus)}</td>
        <td>
          <div>PF ${formatNumber(metrics.profitFactor)}</div>
          <div>RR ${formatNumber(metrics.rewardRiskRatio)}</div>
          <div>胜率 ${formatPercent(metrics.winRatePct)}</div>
          <div>回撤 ${formatPercent(metrics.maxDrawdownPct)}</div>
        </td>
        <td>
          <div>信号 ${getSignalCount(item) ?? "--"}</div>
          <div>止损 ${item.stopLossPct ? formatPercent(item.stopLossPct * 100, 1) : "--"}</div>
          <div>目标 ${item.targetRMultiple ? formatNumber(item.targetRMultiple, 1) : "--"}R</div>
          <div>真实执行 ${item.liveTradingApproved ? "异常开启" : "关闭"}</div>
        </td>
        <td>
          <div class="note-row">
            <select data-strategy="${item.strategyId}">
              ${statusOptions.map((status) => `<option value="${status}" ${status === item.consoleStatus ? "selected" : ""}>${tStatus(status)}</option>`).join("")}
            </select>
            <input data-note="${item.strategyId}" value="${item.consoleNote || ""}" placeholder="本地备注，不会触发交易…" autocomplete="off" />
            <button class="secondary" data-save="${item.strategyId}" type="button">保存</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  el("strategyList").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>策略</th>
          <th>状态</th>
          <th>回测指标</th>
          <th>风险参数</th>
          <th>本地操作</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;

  document.querySelectorAll("[data-save]").forEach((button) => {
    button.addEventListener("click", async () => {
      const strategyId = button.getAttribute("data-save");
      const status = document.querySelector(`[data-strategy="${strategyId}"]`).value;
      const note = document.querySelector(`[data-note="${strategyId}"]`).value;
      button.disabled = true;
      try {
        await postJson("/api/strategy-status", { strategyId, status, note });
        await refreshAll();
      } finally {
        button.disabled = false;
      }
    });
  });
}

function renderReports(reports) {
  el("reportList").innerHTML = reports.slice(0, 8).map((item) => {
    const summary = item.summary || {};
    return `
      <div class="item report-item">
        <div>
          <strong>${item.version || item.reportId}</strong>
          <small>${formatDate(item.generatedAt)}</small>
          <div>${item.reportId}</div>
        </div>
        <div class="report-metrics">
          <span>信号 ${summary.filledSignalCount ?? summary.tradeCount ?? "--"}</span>
          <span>胜率 ${formatPercent(summary.winRatePct)}</span>
          <span>PF ${formatNumber(summary.profitFactor)}</span>
          <span>RR ${formatNumber(summary.rewardRiskRatio)}</span>
        </div>
      </div>
    `;
  }).join("") || '<div class="item">暂无报告。</div>';
}

function renderExchanges(sources, mobile) {
  const connectivity = mobile.exchangeConnectivity || {};
  const latestByExchange = {};
  (connectivity.exchanges || []).forEach((item) => {
    latestByExchange[item.exchange] = item;
  });

  el("exchangeList").innerHTML = (sources || []).map((item) => {
    const latest = latestByExchange[item.exchange] || {};
    const status = latest.ok === true ? "ok" : latest.ok === false ? "failed" : "not_probed";
    return `
      <div class="exchange-card">
        <div class="exchange-card-head">
          <strong>${item.displayName}</strong>
          ${badge(item.publicOnly ? "public_only" : "private_disabled")}
        </div>
        <div>${badge(status)}</div>
        <div class="kv">
          <span>Ticker</span><strong>${item.supportsTicker ? "支持" : "不支持"}</strong>
          <span>OHLCV</span><strong>${item.supportsOhlcv ? "支持" : "不支持"}</strong>
          <span>Funding</span><strong>${item.supportsFundingRate ? "支持" : "不支持"}</strong>
          <span>Open Interest</span><strong>${item.supportsOpenInterest ? "支持" : "不支持"}</strong>
          <span>延迟</span><strong>${formatNumber(latest.latencyMs, 0)} ms</strong>
        </div>
        <small>${item.documentationUrl}</small>
      </div>
    `;
  }).join("") || '<div class="item">未配置公共行情源。</div>';
}

function renderStrategySlots(slots) {
  el("strategySlotList").innerHTML = (slots || []).map((slot) => {
    const strategy = slot.strategy || {};
    return `
      <div class="slot-card">
        <div class="exchange-card-head">
          <strong>${slot.label}</strong>
          ${badge(slot.status)}
        </div>
        <div class="kv">
          <span>角色</span><strong>${slot.role}</strong>
          <span>预期策略</span><strong>${slot.expectedStrategyId || "--"}</strong>
          <span>已载入</span><strong>${strategy.strategyId || "--"}</strong>
          <span>手动导入</span><strong>${slot.manualImportOnly ? "是" : "否"}</strong>
          <span>执行权限</span><strong>${slot.executionAllowed ? "开启" : "关闭"}</strong>
        </div>
      </div>
    `;
  }).join("") || '<div class="item">未配置策略槽位。</div>';
}

function translateConnectionNote(note) {
  const translations = {
    "Use the LAN URL on a real phone; 127.0.0.1 points to the phone itself.": "真机请使用局域网 URL；127.0.0.1 指向手机自身。",
    "Keep the phone and desktop on the same Wi-Fi or LAN.": "手机和电脑需要在同一 Wi-Fi 或局域网。",
    "If the phone cannot connect, allow Python through Windows Firewall for this local port.": "如果手机无法连接，请允许 Python 通过 Windows 防火墙访问本地端口。",
    "This endpoint only exposes read-only status and cannot execute trades.": "该接口只暴露只读状态，不能执行交易。",
    "The console is currently bound to localhost only. Restart with scripts/start_console.ps1 -Mobile for phone testing.": "当前控制台只绑定本机地址；真机测试请用 scripts/start_console.ps1 -Mobile 重启。",
  };
  return translations[note] || note;
}

function renderAudit(events) {
  el("auditList").innerHTML = events.slice().reverse().slice(0, 12).map((item) => `
    <div class="item audit-item">
      <strong>${item.eventType}</strong>
      <small>${formatDate(item.createdAt)}</small>
      <div>${JSON.stringify(item.payload)}</div>
    </div>
  `).join("") || '<div class="item">暂无审计事件。</div>';
}

async function refreshAll() {
  const [strategies, reports, mobile, connection, audit, exchanges, slots] = await Promise.all([
    getJson("/api/strategies"),
    getJson("/api/reports"),
    getJson("/api/mobile/status"),
    getJson("/api/mobile/connection-info"),
    getJson("/api/audit"),
    getJson("/api/exchanges"),
    getJson("/api/strategy-slots"),
  ]);
  const strategyItems = strategies.strategies || [];
  const reportItems = reports.reports || [];
  renderCommandCenter(strategyItems, reportItems, mobile);
  renderRuntimeMonitor(strategyItems, mobile);
  renderStrategies(strategyItems);
  renderReports(reportItems);
  renderAudit(audit.events || []);
  renderExchanges(exchanges.sources || [], mobile);
  renderStrategySlots(slots.slots || []);
  renderMobileConnectionInfo(connection);
  el("mobilePreview").textContent = JSON.stringify(mobile, null, 2);
}

function renderMobileConnectionInfo(connection) {
  const recommended = connection.recommendedMobileUrl || "手机测试请用 scripts/start_console.ps1 -Mobile 重启控制台。";
  el("recommendedMobileUrl").textContent = recommended;
  const urls = connection.mobileStatusUrls || [];
  const notes = connection.notes || [];
  el("mobileConnectionNotes").innerHTML = `
    <div class="item">
      <strong>手机连接准备</strong>
      <div>电脑和手机需要在同一 Wi-Fi 或局域网。</div>
      <div>局域网可见：${connection.serverLanVisible ? "是" : "否"}</div>
      <div>候选 URL：${urls.length ? urls.join(", ") : "--"}</div>
    </div>
    ${notes.map((note) => `<div class="item">${translateConnectionNote(note)}</div>`).join("")}
  `;
}

function updateCurrentSection() {
  const sections = Object.keys(sectionLabels)
    .map((id) => document.getElementById(id))
    .filter(Boolean);
  const active = sections.reduce((best, section) => {
    const top = Math.abs(section.getBoundingClientRect().top - 84);
    if (!best || top < best.top) return { id: section.id, top };
    return best;
  }, null);
  if (!active) return;
  document.querySelectorAll(".rail-item").forEach((item) => {
    item.classList.toggle("active", item.getAttribute("href") === `#${active.id}`);
  });
  const current = el("currentSectionLabel");
  if (current) current.textContent = `当前：${sectionLabels[active.id] || active.id}`;
}

function scrollToOverview() {
  document.getElementById("overview")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

el("refreshButton").addEventListener("click", refreshAll);
el("importButton").addEventListener("click", async () => {
  el("importButton").disabled = true;
  try {
    await postJson("/api/import", {});
    await refreshAll();
  } finally {
    el("importButton").disabled = false;
  }
});

el("probeExchangesButton").addEventListener("click", async () => {
  el("probeExchangesButton").disabled = true;
  try {
    await postJson("/api/exchanges/probe-public", {
      symbol: el("probeSymbol").value,
      timeframe: el("probeTimeframe").value,
      limit: Number(el("probeLimit").value || 2),
    });
    await refreshAll();
  } finally {
    el("probeExchangesButton").disabled = false;
  }
});

el("backHomeButton").addEventListener("click", scrollToOverview);
window.addEventListener("scroll", updateCurrentSection, { passive: true });
window.addEventListener("hashchange", updateCurrentSection);

refreshAll().catch((error) => {
  el("strategyList").innerHTML = `<div class="item">加载失败：${error.message}</div>`;
});
updateCurrentSection();
