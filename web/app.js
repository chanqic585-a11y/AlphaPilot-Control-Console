const statusOptions = [
  "research_only",
  "local_paper_ready",
  "forward_testing",
  "dry_run_candidate",
  "disabled",
];

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

function badge(value) {
  const normalized = String(value ?? "--");
  let kind = "";
  if (normalized === "local_paper_ready" || normalized === "ok" || normalized === "public_only") kind = "ok";
  if (normalized === "disabled" || normalized === "research_only") kind = "warn";
  if (normalized.includes("false") || normalized === "failed") kind = "danger";
  return `<span class="badge ${kind}">${normalized}</span>`;
}

function renderStrategies(strategies) {
  latestStrategies = strategies;
  el("strategyCount").textContent = String(strategies.length);
  const anyDry = strategies.some((item) => item.exchangeDryRunApproved);
  const anyLive = strategies.some((item) => item.liveTradingApproved);
  el("dryRunStatus").textContent = anyDry ? "True" : "False";
  el("liveStatus").textContent = anyLive ? "True" : "False";

  if (!strategies.length) {
    el("strategyList").innerHTML = '<div class="item">No strategy packages found. Run Import Reports after Quant Engine reports exist.</div>';
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
          <div>Win ${formatNumber(metrics.winRatePct)}%</div>
          <div>DD ${formatNumber(metrics.maxDrawdownPct)}%</div>
        </td>
        <td>
          <div>Signals ${item.selectedSignalCount ?? metrics.filledSignalCount ?? metrics.tradeCount ?? "--"}</div>
          <div>SL ${formatNumber(item.stopLossPct, 3)}</div>
          <div>Target ${formatNumber(item.targetRMultiple, 1)}R</div>
        </td>
        <td>
          <div class="note-row">
            <select data-strategy="${item.strategyId}">
              ${statusOptions.map((status) => `<option value="${status}" ${status === item.consoleStatus ? "selected" : ""}>${status}</option>`).join("")}
            </select>
            <input data-note="${item.strategyId}" value="${item.consoleNote || ""}" placeholder="Local note only" />
            <button class="secondary" data-save="${item.strategyId}" type="button">Save</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  el("strategyList").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Package</th>
          <th>Status</th>
          <th>Metrics</th>
          <th>Risk</th>
          <th>Console Action</th>
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
  el("reportCount").textContent = String(reports.length);
  el("reportList").innerHTML = reports.slice(0, 10).map((item) => `
    <div class="item">
      <strong>${item.version || item.reportId}</strong>
      <small>${item.generatedAt || "--"}</small>
      <div>${item.reportId}</div>
      <div>${badge(`dryRun:${item.exchangeDryRunApproved}`)} ${badge(`live:${item.liveTradingApproved}`)}</div>
    </div>
  `).join("") || '<div class="item">No reports found.</div>';
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
          <span>Ticker</span><strong>${item.supportsTicker ? "yes" : "no"}</strong>
          <span>OHLCV</span><strong>${item.supportsOhlcv ? "yes" : "no"}</strong>
          <span>Funding</span><strong>${item.supportsFundingRate ? "yes" : "no"}</strong>
          <span>Open Interest</span><strong>${item.supportsOpenInterest ? "yes" : "no"}</strong>
          <span>Latest latency</span><strong>${formatNumber(latest.latencyMs, 0)} ms</strong>
        </div>
        <small>${item.documentationUrl}</small>
      </div>
    `;
  }).join("") || '<div class="item">No public exchange sources configured.</div>';
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
          <span>Role</span><strong>${slot.role}</strong>
          <span>Expected</span><strong>${slot.expectedStrategyId || "--"}</strong>
          <span>Loaded</span><strong>${strategy.strategyId || "--"}</strong>
          <span>Manual import</span><strong>${slot.manualImportOnly ? "yes" : "no"}</strong>
          <span>Execution</span><strong>${slot.executionAllowed ? "enabled" : "disabled"}</strong>
        </div>
      </div>
    `;
  }).join("") || '<div class="item">No strategy slots configured.</div>';
}

function renderAudit(events) {
  el("auditList").innerHTML = events.slice().reverse().slice(0, 12).map((item) => `
    <div class="item">
      <strong>${item.eventType}</strong>
      <small>${item.createdAt}</small>
      <div>${JSON.stringify(item.payload)}</div>
    </div>
  `).join("") || '<div class="item">No audit events yet.</div>';
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
  renderStrategies(strategies.strategies || []);
  renderReports(reports.reports || []);
  renderAudit(audit.events || []);
  renderExchanges(exchanges.sources || [], mobile);
  renderStrategySlots(slots.slots || []);
  renderMobileConnectionInfo(connection);
  el("mobilePreview").textContent = JSON.stringify(mobile, null, 2);
}

function renderMobileConnectionInfo(connection) {
  const recommended = connection.recommendedMobileUrl || "Restart with scripts/start_console.ps1 -Mobile for phone testing.";
  el("recommendedMobileUrl").textContent = recommended;
  const urls = connection.mobileStatusUrls || [];
  const notes = connection.notes || [];
  el("mobileConnectionNotes").innerHTML = `
    <div class="item">
      <strong>Phone setup</strong>
      <div>Keep desktop and phone on the same Wi-Fi or LAN.</div>
      <div>LAN visible: ${connection.serverLanVisible ? "yes" : "no"}</div>
      <div>Candidate LAN URLs: ${urls.length ? urls.join(", ") : "--"}</div>
    </div>
    ${notes.map((note) => `<div class="item">${note}</div>`).join("")}
  `;
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

refreshAll().catch((error) => {
  el("strategyList").innerHTML = `<div class="item">Load failed: ${error.message}</div>`;
});
