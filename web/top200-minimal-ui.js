(function () {
  "use strict";

  const POLL_MS = 3000;
  let strategyLoading = false;
  let demoLoading = false;
  let liveLoading = false;
  let activeFactoryRunId = null;
  let activeFactoryStatus = null;
  let continuousActionLoading = false;
  let runtimeControlsLoading = false;
  let pendingRuntimeRiskOverlay = null;

  const byId = (id) => document.getElementById(id);

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  async function fetchJson(path, options = {}) {
    const request = { cache: "no-store", ...options };
    if (request.body && !request.headers) {
      request.headers = { "Content-Type": "application/json" };
    }
    const response = await fetch(path, request);
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

  const LIVE_NEXT_ACTION_LABELS = {
    complete_adaptive_learning_readiness: "完成 Qlib、因子、模型验证、漂移与回滚证据，再申请精确批准。",
    review_exact_live_release_approval: "复核精确 Live Release 与风险覆盖；批准后仍需单独 ARM。",
  };

  function renderLiveCanaryReadiness(summary) {
    const badge = byId("top200LiveReadinessBadge");
    badge.textContent = summary.statusLabel || "未知";
    badge.className = summary.status === "armed" ? "badge ok" : "badge warn";
    byId("top200LiveSmoke").textContent = summary.engineeringSmoke?.status === "passed" ? "已通过" : "未通过";
    byId("top200LiveAdaptive").textContent = summary.adaptiveLearning?.passed
      ? "已通过"
      : `${summary.adaptiveLearning?.blockerCount || 0} 项未完成`;
    byId("top200LiveApproval").textContent = summary.execution?.approvalStatus === "approved" ? "已批准" : "未执行";
    byId("top200LiveExecution").textContent = summary.execution?.armStatus === "armed"
      ? "已 ARM"
      : `未 ARM · ${summary.orders?.count || 0} 订单`;
    const risk = summary.risk || {};
    byId("top200LiveRisk").textContent = [
      `资金上限 ${formatValue(risk.allocatedCapitalUSDT, " USDT")}`,
      `单笔风险 ${formatValue(risk.riskPerTradeUSDT, " USDT")}`,
      `最多 ${formatValue(risk.maximumConcurrentPositions)} 个持仓`,
      `${formatValue(risk.maximumLeverage, "x")} ${risk.marginMode === "isolated" ? "逐仓" : formatValue(risk.marginMode)}`,
      `扫描 Top${formatValue(risk.scanTopN)}`,
    ].join(" · ");
    byId("top200LiveNextAction").textContent = LIVE_NEXT_ACTION_LABELS[summary.nextAction]
      || "等待可复核的下一步。";
    byId("top200LiveAudit").textContent = JSON.stringify({
      release: summary.release,
      risk: summary.risk,
      engineeringSmoke: summary.engineeringSmoke,
      adaptiveLearning: summary.adaptiveLearning,
      execution: summary.execution,
      orders: summary.orders,
      fills: summary.fills,
      positions: summary.positions,
      latency: summary.latency,
      audit: summary.audit,
    }, null, 2);
    setIssue(byId("top200LiveIssue"), summary.issues || []);
  }

  async function refreshLive() {
    if (liveLoading || !byId("top200MinimalLive")) return;
    liveLoading = true;
    try {
      renderLiveCanaryReadiness(await fetchJson("/api/live/canary-readiness"));
    } catch (error) {
      byId("top200LiveReadinessBadge").textContent = "状态不可用";
      byId("top200LiveReadinessBadge").className = "badge danger";
      setIssue(byId("top200LiveIssue"), [{ message: `Live 状态读取失败：${error.message}` }], true);
    } finally {
      liveLoading = false;
    }
  }

  const FACTORY_STAGE_LABELS = {
    idle: "等待启动",
    prepare_material: "准备研究材料",
    generate_plan: "生成研究计划",
    data_check: "检查数据",
    tuning_backtest: "开发回测",
    robustness: "稳健性检查",
    portfolio_evaluation: "组合评估",
    formal_handoff: "正式验证准备",
    complete: "研究完成",
    release_ready: "Release 已冻结",
  };

  const DEMO_STRATEGY_STATUS_LABELS = {
    waiting_approval: "等待批准",
    approved_not_armed: "已批准，待启动",
    armed: "已启动",
  };

  const RUNTIME_RISK_FIELD_LABELS = {
    allocatedCapital: "分配资金 USDT",
    riskPerTradePercent: "单笔风险 %",
    riskPerTradeUSDT: "单笔风险 USDT",
    maximumPortfolioOpenRiskPercent: "组合开仓风险 %",
    maximumPortfolioOpenRiskUSDT: "组合开仓风险 USDT",
    maximumConcurrentPositions: "最大同时持仓",
    maximumInstrumentRisk: "单币种风险 %",
    maximumSameDirectionRisk: "同方向风险 %",
    maximumCorrelationClusterRisk: "相关性簇风险 %",
    maximumPortfolioBeta: "组合 Beta 上限",
    maximumLeverage: "最大杠杆",
    marginMode: "保证金模式",
    dailyLossLimit: "日亏损停止 %",
    programLossLimit: "项目亏损停止 %",
    hardKillLossLimit: "硬停损 USDT",
    scanTopN: "扫描 Top N",
  };

  function formatEvidenceNumber(value, digits = 2) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "--";
    return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: digits }).format(number);
  }

  function evidenceRows(rows) {
    return `<div class="strategy-factory-evidence-list">${rows.map(([label, value]) => (
      `<span>${escapeHtml(label)}：<strong>${escapeHtml(value)}</strong></span>`
    )).join("")}</div>`;
  }

  function renderStrategyFactoryTaskEvidence(factory) {
    const container = byId("strategyFactoryTaskEvidence");
    if (!container || !factory?.researchRunId) return;
    const evidence = factory.executionEvidence || {};
    const development = evidence.development || {};
    const formal = evidence.formal || {};
    const runtime = evidence.runtime || {};
    const progress = Math.max(0, Math.min(100, Number(factory.progressPercent || 0)));
    const stage = FACTORY_STAGE_LABELS[factory.stage] || factory.stage || "等待启动";
    container.hidden = false;
    byId("strategyFactoryTaskStage").textContent = `${stage} · ${factory.timeframe || "--"}`;
    byId("strategyFactoryTaskRuntime").textContent = runtime.elapsedSeconds === null || runtime.elapsedSeconds === undefined
      ? `开始 ${formatTimestamp(runtime.startedAt || runtime.createdAt)}`
      : `运行 ${formatEvidenceNumber(runtime.elapsedSeconds, 1)} 秒`;
    const progressTrack = byId("strategyFactoryTaskProgress");
    progressTrack.setAttribute("aria-valuenow", String(progress));
    byId("strategyFactoryTaskProgressBar").style.width = `${progress}%`;

    const timeframes = (development.timeframes || []).join(" / ") || factory.timeframe || "--";
    byId("strategyFactoryDataEvidence").innerHTML = evidenceRows([
      ["证据层", development.status === "completed" ? "Development 回测（真实本地快照）" : "等待 Development 回测"],
      ["数据分区", `${formatEvidenceNumber(development.verifiedPartitionCount, 0)} 个已校验`],
      ["币种 / 周期", `${formatEvidenceNumber(development.instrumentCount, 0)} / ${timeframes}`],
      ["K 线行数", formatEvidenceNumber(development.totalRowCount, 0)],
      ["时间窗口", `${formatTimestamp(development.developmentStart)} 至 ${formatTimestamp(development.developmentEnd)}`],
      ["候选 / 试验", `${formatEvidenceNumber(development.candidateCount, 0)} / ${formatEvidenceNumber(development.trialCount, 0)}`],
    ]);

    const best = development.bestTrial || {};
    byId("strategyFactoryMetricEvidence").innerHTML = evidenceRows([
      ["事件数", formatEvidenceNumber(development.eventCount, 0)],
      ["最佳 PF", formatEvidenceNumber(best.profitFactor)],
      ["平均净 R", formatEvidenceNumber(best.averageNetR, 3)],
      ["累计净 R", formatEvidenceNumber(best.totalNetR, 3)],
      ["最大回撤 R", formatEvidenceNumber(best.maxDrawdownR, 3)],
      ["成本压力 R", formatEvidenceNumber(best.totalCostR, 3)],
    ]);

    const formalLabel = formal.status === "completed"
      ? "Formal 正式验证：已有可复核结果"
      : formal.status === "running"
        ? "Formal 正式验证：运行中"
        : "Formal 正式验证：未运行 · 锁定 OOS 未读取";
    byId("strategyFactoryFormalEvidence").innerHTML = evidenceRows([
      ["状态", formalLabel],
      ["Formal 运行 / 结果读取", `${formatEvidenceNumber(formal.formalRunCount, 0)} / ${formatEvidenceNumber(formal.resultReadCount, 0)}`],
      ["锁定 OOS 读取", formatEvidenceNumber(formal.lockedOosReadCount, 0)],
      ["Release", formatEvidenceNumber(formal.releaseCount, 0)],
    ]);

    const artifacts = evidence.artifacts || [];
    byId("strategyFactoryArtifactEvidence").innerHTML = artifacts.length
      ? artifacts.map((artifact) => (
        `<div><code>${escapeHtml(artifact.name)}</code>${artifact.sha256 ? ` · ${escapeHtml(artifact.sha256.slice(0, 12))}` : ""}</div>`
      )).join("")
      : "尚未生成 Artifact。";
  }

  function openStrategyFactoryDialog() {
    const dialog = byId("strategyFactoryDialog");
    byId("strategyFactoryFormStatus").textContent = "";
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    refreshStrategy();
  }

  function closeStrategyFactoryDialog() {
    const dialog = byId("strategyFactoryDialog");
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  }

  async function submitStrategyFactory(event) {
    event.preventDefault();
    const submit = byId("strategyFactorySubmit");
    const status = byId("strategyFactoryFormStatus");
    submit.disabled = true;
    status.textContent = "正在启动研究任务。";
    try {
      const created = await fetchJson("/api/research-factory/runs", {
        method: "POST",
        body: JSON.stringify({
          operation: byId("strategyFactoryOperation").value,
          timeframe: byId("strategyFactoryTimeframe").value,
          mode: byId("strategyFactoryMode").value,
          maxCandidateCount: Number(byId("strategyFactoryCandidateBudget").value),
          maxTrialBudget: Number(byId("strategyFactoryTrialBudget").value),
        }),
      });
      activeFactoryRunId = created.runId;
      activeFactoryStatus = created.status;
      status.textContent = "研究任务已在后台启动。";
      renderStrategyFactoryTaskEvidence(created);
      await refreshStrategy();
    } catch (error) {
      status.textContent = `启动失败：${error.message}`;
    } finally {
      submit.disabled = false;
    }
  }

  async function toggleStrategyFactoryRun() {
    if (!activeFactoryRunId || activeFactoryStatus === "pause_requested" || !["running", "queued", "paused"].includes(activeFactoryStatus)) return;
    const runId = activeFactoryRunId;
    const action = activeFactoryStatus === "paused" ? "resume" : "pause";
    const route = action === "resume"
      ? `/api/research-factory/runs/${encodeURIComponent(runId)}/resume`
      : `/api/research-factory/runs/${encodeURIComponent(runId)}/pause`;
    const button = byId("top200FactoryPauseResumeButton");
    button.disabled = true;
    try {
      const updated = await fetchJson(route, {
        method: "POST",
        body: "{}",
      });
      activeFactoryStatus = updated.status;
      await refreshStrategy();
    } catch (error) {
      setIssue(byId("top200StrategyIssue"), [{ message: `研究任务操作失败：${error.message}` }], true);
    } finally {
      button.disabled = false;
    }
  }

  function renderStrategyFactoryContinuous(state) {
    const button = byId("strategyFactoryContinuousButton");
    const status = byId("strategyFactoryContinuousStatus");
    if (!button || !status) return;
    const enabled = Boolean(state?.enabled);
    const cycle = Array.isArray(state?.cycle) ? state.cycle : [];
    const nextIndex = Number(state?.nextIndex || 0);
    const nextItem = cycle[nextIndex] || {};
    const operationLabel = nextItem.operation === "combine" ? "组合" : "生成";
    const phaseLabels = {
      disabled: "持续研究未启动",
      disabled_after_current_run: "本轮完成后停止",
      ready: "准备启动下一项",
      running: "正在运行",
      waiting_existing_run: "等待当前人工任务完成",
      waiting_current_run: "正在核对本轮结果",
      cycle_item_failed: "本项失败，已记录并继续下一项",
    };
    button.dataset.enabled = enabled ? "true" : "false";
    button.disabled = continuousActionLoading;
    button.textContent = enabled ? "停止持续研究" : "持续研究";
    const currentLabel = nextItem.timeframe
      ? `${nextItem.timeframe} ${operationLabel}`
      : "等待研究项";
    status.textContent = `${phaseLabels[state?.phase] || state?.phase || "状态未知"} · 下一项 ${currentLabel} · 已完成 ${Number(state?.completedRunCount || 0)} 次 / ${Number(state?.completedCycleCount || 0)} 轮`;
  }

  async function toggleStrategyFactoryContinuous() {
    const button = byId("strategyFactoryContinuousButton");
    if (!button || continuousActionLoading) return;
    const action = button.dataset.enabled === "true" ? "disable" : "enable";
    continuousActionLoading = true;
    button.disabled = true;
    try {
      const state = await fetchJson(`/api/research-factory/continuous/${action}`, {
        method: "POST",
        body: "{}",
      });
      renderStrategyFactoryContinuous(state);
      await refreshStrategy();
    } catch (error) {
      setIssue(byId("top200StrategyIssue"), [{ message: `持续研究操作失败：${error.message}` }], true);
    } finally {
      continuousActionLoading = false;
      button.disabled = false;
    }
  }

  function renderAiControl(payload) {
    const health = payload?.providerHealth || {};
    const healthLabel = Object.entries(health)
      .map(([provider, status]) => `${provider}: ${status === "configured" ? "已配置" : "待配置"}`)
      .join(" · ") || "无 Provider 状态";
    const modelCount = Number(payload?.modelCount ?? payload?.models?.length ?? 0);
    const batchCount = Number(payload?.queue?.batchJobCount || 0);
    const campaignBudget = payload?.budget?.defaultCampaignLimitUsd;
    byId("strategyAiProviderHealth").textContent = healthLabel;
    byId("strategyAiModelSummary").textContent = `${modelCount} 个版本化模型别名`;
    byId("strategyAiQueueSummary").textContent = batchCount ? `${batchCount} 个批量任务` : "队列为空";
    byId("strategyAiBudgetSummary").textContent = campaignBudget == null
      ? "按版本化策略限制"
      : `单 Campaign 上限 ${campaignBudget} USD`;
    byId("strategyAiRoutingSummary").textContent = JSON.stringify({
      status: payload?.status || "unknown",
      routing: payload?.routing || {},
      promptVersionCount: payload?.promptVersionCount || 0,
      auditEventCount: payload?.auditEventCount || 0,
      credentialsPersisted: payload?.credentialsPersisted === true,
      exchangeCredentialsAvailableToWorker: payload?.exchangeCredentialsAvailableToWorker === true,
      executionAuthorized: payload?.executionAuthorized === true,
    }, null, 2);
  }

  async function refreshStrategy() {
    if (strategyLoading || !byId("top200MinimalStrategy")) return;
    strategyLoading = true;
    try {
      const [factory, summary, releases, continuous, aiControl] = await Promise.all([
        fetchJson("/api/research-factory/summary"),
        fetchJson("/api/strategy/summary"),
        fetchJson("/api/strategy/releases"),
        fetchJson("/api/research-factory/continuous"),
        fetchJson("/api/ai/control"),
      ]);
      renderAiControl(aiControl);
      const current = (releases.releases || []).find((item) => item.status === "can_enter_demo");
      const progress = Math.max(0, Math.min(100, Number(factory.progressPercent || 0)));
      const track = byId("top200ResearchProgressBar")?.parentElement;
      activeFactoryRunId = factory.readOnly ? null : factory.researchRunId;
      activeFactoryStatus = factory.status;
      if (byId("strategyFactoryDialog")?.open) {
        renderStrategyFactoryTaskEvidence(factory);
      }
      byId("top200ResearchStage").textContent = FACTORY_STAGE_LABELS[factory.stage] || factory.stage;
      byId("top200ResearchProgressLabel").textContent = `${factory.completedCount} / ${factory.totalCount}`;
      byId("top200ResearchProgressBar").style.width = `${progress}%`;
      if (track) track.setAttribute("aria-valuenow", String(progress));
      byId("top200ResearchCurrent").textContent = `当前：${factory.currentCandidate || "--"}`;
      const pauseResume = byId("top200FactoryPauseResumeButton");
      const factoryActive = !factory.readOnly && ["running", "queued", "pause_requested", "paused"].includes(factory.status);
      pauseResume.hidden = !factoryActive;
      pauseResume.disabled = factory.status === "pause_requested";
      pauseResume.textContent = factory.status === "pause_requested"
        ? "正在安全暂停"
        : factory.status === "paused" ? "继续研究" : "暂停研究";
      renderStrategyFactoryContinuous(continuous);
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
        factoryAutomaticPromotionAllowed: factory.automaticPromotionAllowed ?? false,
        factoryDemoArm: factory.demoArm ?? false,
        factoryOrderCount: factory.orderCount ?? 0,
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
        <span class="top200-state-badge">${escapeHtml(DEMO_STRATEGY_STATUS_LABELS[strategy.status] || strategy.status)}</span>
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

  function renderRuntimeRiskFields(contract) {
    const container = byId("runtimeRiskFields");
    if (!container) return;
    const fields = contract?.fields || {};
    container.innerHTML = Object.entries(RUNTIME_RISK_FIELD_LABELS).map(([field, label]) => {
      const bounds = fields[field];
      if (!bounds) return "";
      if (field === "marginMode") {
        return `<label><span>${escapeHtml(label)}</span><select data-runtime-risk-field="${field}">
          <option value="isolated" ${bounds.currentValue === "isolated" ? "selected" : ""}>逐仓</option>
          <option value="cross" ${bounds.currentValue === "cross" ? "selected" : ""}>全仓</option>
        </select><small>允许范围：${escapeHtml(bounds.minimumAllowed)} - ${escapeHtml(bounds.maximumAllowed)}</small></label>`;
      }
      return `<label><span>${escapeHtml(label)}</span><input data-runtime-risk-field="${field}" type="number" step="any"
        min="${escapeHtml(bounds.minimumAllowed)}" max="${escapeHtml(bounds.maximumAllowed)}"
        value="${escapeHtml(bounds.currentValue)}" />
        <small>范围 ${escapeHtml(bounds.minimumAllowed)} - ${escapeHtml(bounds.maximumAllowed)} · 新订单生效</small></label>`;
    }).join("");
  }

  function readRuntimeRiskOverrides() {
    const overrides = {};
    document.querySelectorAll("[data-runtime-risk-field]").forEach((input) => {
      const field = input.dataset.runtimeRiskField;
      overrides[field] = input.tagName === "SELECT" ? input.value : Number(input.value);
    });
    return overrides;
  }

  function showPendingRuntimeRiskOverlay(overlay, exactConfirmation = null) {
    pendingRuntimeRiskOverlay = overlay || null;
    const panel = byId("runtimeRiskApprovalPanel");
    if (!panel) return;
    panel.hidden = !pendingRuntimeRiskOverlay;
    byId("runtimeRiskPendingHash").textContent = exactConfirmation
      || pendingRuntimeRiskOverlay?.contentHash
      || "--";
    byId("runtimeRiskApprovalConfirmation").value = "";
  }

  async function refreshRuntimeControls() {
    const details = byId("top200RuntimeControls");
    if (!details?.open || runtimeControlsLoading) return;
    runtimeControlsLoading = true;
    try {
      const [risk, switches, interventions] = await Promise.all([
        fetchJson("/api/risk-profiles"),
        fetchJson("/api/strategy-version-switch"),
        fetchJson("/api/manual-interventions"),
      ]);
      const environment = byId("runtimeRiskEnvironment").value;
      renderRuntimeRiskFields(risk.runtimeRiskContracts?.[environment]);
      const pending = (risk.runtimeOverlays || []).find((item) => (
        item.environment === environment && item.status === "pending_exact_approval"
      ));
      showPendingRuntimeRiskOverlay(pending);
      const active = risk.activeRuntimeOverlays?.[environment];
      byId("runtimeRiskStatus").textContent = active
        ? `当前覆盖：${active.contentHash} · 仅影响新订单`
        : "当前使用冻结风险配置；创建覆盖不会开启执行。";
      byId("strategyVersionStatus").textContent = switches.strategies?.length
        ? `已登记 ${switches.strategies.length} 条策略版本；操作不会开启执行。`
        : "尚无版本切换记录；已有持仓始终保留开仓时版本。";
      byId("manualInterventionStatus").textContent = interventions.recentEvents?.length
        ? `最近已记录 ${interventions.recentEvents.length} 条人工干预；不会隐式创建订单。`
        : "这里只登记审计请求，不会隐式创建订单。";
    } catch (error) {
      byId("runtimeRiskStatus").textContent = `运行配置读取失败：${error.message}`;
    } finally {
      runtimeControlsLoading = false;
    }
  }

  async function createRuntimeRiskOverlay(event) {
    event.preventDefault();
    const status = byId("runtimeRiskStatus");
    try {
      const result = await fetchJson("/api/risk-profiles/runtime-overlays/create", {
        method: "POST",
        body: JSON.stringify({
          environment: byId("runtimeRiskEnvironment").value,
          overrides: readRuntimeRiskOverrides(),
          actor: "user_manual",
          reason: byId("runtimeRiskReason").value,
        }),
      });
      if (result.executionEnabled) throw new Error("风险覆盖不应直接开启执行");
      const overlay = result.runtimeRiskOverlay;
      status.textContent = result.approvalRequired
        ? "风险提高版本已创建，等待精确确认。"
        : "风险降低或等值版本已应用到后续新订单。";
      showPendingRuntimeRiskOverlay(
        result.approvalRequired ? overlay : null,
        result.exactConfirmation,
      );
      await refreshDemo();
    } catch (error) {
      status.textContent = `风险覆盖创建失败：${error.message}`;
    }
  }

  async function approveRuntimeRiskOverlay() {
    if (!pendingRuntimeRiskOverlay) return;
    const status = byId("runtimeRiskStatus");
    try {
      const result = await fetchJson("/api/risk-profiles/runtime-overlays/approve", {
        method: "POST",
        body: JSON.stringify({
          runtimeRiskOverlayId: pendingRuntimeRiskOverlay.runtimeRiskOverlayId,
          actor: "user_manual",
          confirmation: byId("runtimeRiskApprovalConfirmation").value,
          reason: "operator_exact_runtime_risk_approval",
        }),
      });
      if (result.executionEnabled) throw new Error("风险批准不应直接开启执行");
      status.textContent = "风险覆盖版本已精确批准，仅对后续新订单生效。";
      showPendingRuntimeRiskOverlay(null);
      await refreshRuntimeControls();
    } catch (error) {
      status.textContent = `精确批准失败：${error.message}`;
    }
  }

  async function submitStrategyVersionSwitch(event) {
    event.preventDefault();
    const status = byId("strategyVersionStatus");
    try {
      const result = await fetchJson("/api/strategy-version-switch/action", {
        method: "POST",
        body: JSON.stringify({
          action: byId("strategyVersionAction").value,
          strategyId: byId("strategyVersionStrategyId").value,
          releaseId: byId("strategyVersionReleaseId").value,
          releaseHash: byId("strategyVersionReleaseHash").value,
          mode: byId("strategyVersionMode").value,
          actor: "user_manual",
          reason: byId("strategyVersionReason").value,
          confirmation: byId("strategyVersionConfirmation").value,
          openPositionBindings: [],
        }),
      });
      if (result.result?.executionEnabled) throw new Error("版本操作不应直接开启执行");
      status.textContent = "策略版本操作已写入不可变审计；已有持仓绑定保持不变。";
      await refreshRuntimeControls();
    } catch (error) {
      status.textContent = `策略版本操作失败：${error.message}`;
    }
  }

  function parseObjectJson(value, label) {
    const parsed = JSON.parse(value || "{}");
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new Error(`${label}必须是 JSON 对象`);
    }
    return parsed;
  }

  async function submitManualIntervention(event) {
    event.preventDefault();
    const status = byId("manualInterventionStatus");
    try {
      const result = await fetchJson("/api/manual-interventions/record", {
        method: "POST",
        body: JSON.stringify({
          environment: byId("manualInterventionEnvironment").value,
          action: byId("manualInterventionAction").value,
          operator: "user_manual",
          strategyId: byId("manualInterventionStrategyId").value,
          instrumentId: byId("manualInterventionInstrumentId").value || null,
          positionId: byId("manualInterventionPositionId").value || null,
          before: parseObjectJson(byId("manualInterventionBefore").value, "变更前"),
          after: parseObjectJson(byId("manualInterventionAfter").value, "变更后"),
          reason: byId("manualInterventionReason").value,
        }),
      });
      if (result.event?.executionEnabled) throw new Error("人工干预审计不应直接执行");
      status.textContent = `已记录：${result.event.interventionId}`;
      await refreshRuntimeControls();
    } catch (error) {
      status.textContent = `人工干预登记失败：${error.message}`;
    }
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
    byId("top200StrategyGenerateButton")?.addEventListener("click", openStrategyFactoryDialog);
    byId("strategyFactoryClose")?.addEventListener("click", closeStrategyFactoryDialog);
    byId("strategyFactoryCancel")?.addEventListener("click", closeStrategyFactoryDialog);
    byId("strategyFactoryForm")?.addEventListener("submit", submitStrategyFactory);
    byId("top200FactoryPauseResumeButton")?.addEventListener("click", toggleStrategyFactoryRun);
    byId("strategyFactoryContinuousButton")?.addEventListener("click", toggleStrategyFactoryContinuous);
    byId("top200RuntimeControls")?.addEventListener("toggle", refreshRuntimeControls);
    byId("runtimeRiskEnvironment")?.addEventListener("change", refreshRuntimeControls);
    byId("runtimeRiskForm")?.addEventListener("submit", createRuntimeRiskOverlay);
    byId("runtimeRiskApproveButton")?.addEventListener("click", approveRuntimeRiskOverlay);
    byId("strategyVersionSwitchForm")?.addEventListener("submit", submitStrategyVersionSwitch);
    byId("manualInterventionForm")?.addEventListener("submit", submitManualIntervention);
    refreshStrategy();
    refreshDemo();
    refreshLive();
    window.setInterval(refreshStrategy, POLL_MS);
    window.setInterval(refreshDemo, POLL_MS);
    window.setInterval(refreshLive, POLL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
