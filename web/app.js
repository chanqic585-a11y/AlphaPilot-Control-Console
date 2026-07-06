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
  if (normalized === "local_paper_ready") kind = "ok";
  if (normalized === "disabled" || normalized === "research_only") kind = "warn";
  if (normalized.includes("false")) kind = "danger";
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
  const [strategies, reports, mobile, audit] = await Promise.all([
    getJson("/api/strategies"),
    getJson("/api/reports"),
    getJson("/api/mobile/status"),
    getJson("/api/audit"),
  ]);
  renderStrategies(strategies.strategies || []);
  renderReports(reports.reports || []);
  renderAudit(audit.events || []);
  el("mobilePreview").textContent = JSON.stringify(mobile, null, 2);
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

refreshAll().catch((error) => {
  el("strategyList").innerHTML = `<div class="item">Load failed: ${error.message}</div>`;
});
