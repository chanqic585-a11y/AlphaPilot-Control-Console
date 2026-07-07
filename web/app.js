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

const artifactReviewLabels = {
  unreviewed: "未复核",
  continue_observing: "继续观察",
  paper_observation: "纸面观察",
  paused: "暂停",
  rejected: "淘汰",
};

const baselineComparisonLabels = {
  above_baseline: "高于基线",
  below_baseline: "低于基线",
  return_available_without_baseline: "有收益数据，缺基线",
  not_available: "缺少基线",
};

const checklistStatusLabels = {
  active: "观察中",
  not_started: "未开始",
};

const paperTaskStatusLabels = {
  planned: "计划中",
  active: "观察中",
  paused: "已暂停",
  completed: "已完成",
  rejected: "已淘汰",
};

const paperLogTypeLabels = {
  no_signal: "无信号",
  signal_seen: "看到信号",
  rule_matched: "规则匹配",
  missed: "错过观察",
  invalidated: "条件失效",
  risk_warning: "风险提醒",
};

const paperHealthLabels = {
  healthy_observation: "观察健康",
  watching: "继续观察",
  needs_review: "需要复核",
  needs_more_observation: "样本不足",
  paused: "已暂停",
  completed: "已完成",
  rejected: "已淘汰",
};

const forwardGateLabels = {
  needs_active_validation: "还没有正式验证中的策略",
  waiting_until_review_date: "等待 7 月 10 日前向验收",
  needs_observation_logs: "需要补观察日志",
  needs_rule_match: "需要至少一次规则匹配",
  needs_risk_review: "需要先复核风险/失效记录",
  eligible_for_paper_review: "可进入纸面模拟观察复核",
};

const methodTypeLabels = {
  rule_based: "规则策略",
  factor_based: "因子策略",
  ml_model: "机器学习模型",
  benchmark: "基准策略",
  report_only: "报告资产",
};

const mlStatusLabels = {
  trained_model_reported: "已报告训练模型",
  ml_dataset_ready: "可生成 ML 训练集",
  label_ready_needs_more_samples: "有标签但样本偏少",
  factor_features_available: "有因子特征",
  missing_labels: "缺少 ML 标签",
  not_ml_strategy: "非 ML 策略",
};

const labelStatusLabels = {
  has_2r_and_win_loss_labels: "已有 2R / 胜负标签",
  has_win_loss_labels: "已有胜负标签",
  has_path_quality_labels: "已有路径质量标签",
  has_sample_labels: "已有样本标签",
  missing_labels: "缺标签",
};

const candidateDecisionLabels = {
  can_forward_validate: "可进入前向验证",
  ml_evaluation_queue: "ML 评价队列",
  needs_backtest: "需要补回测",
  backtest_completed_not_ready: "补测完成未通过",
  needs_labels: "需要补标签",
  research_only: "只做研究观察",
  paused: "暂停",
  rejected_or_archived: "淘汰 / 归档",
};

const candidateQueueLabels = {
  priority_forward_validation: "前向验证优先",
  ml_evaluation: "ML 评价队列",
  needs_backtest: "需要补回测",
  needs_labels: "需要补标签",
  research_watchlist: "研究观察",
  paused: "暂停",
  rejected: "淘汰 / 归档",
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
  artifacts: "策略资产",
  observationTasks: "观察任务",
  learning: "学习闭环",
  exchanges: "公共行情",
  mobile: "手机控制台",
  audit: "审计日志",
};

let latestStrategies = [];
let latestArtifactIndex = {};
let latestPaperTasks = [];
let selectedArtifactId = null;
const artifactFilters = {
  search: "",
  tier: "all",
  reviewStatus: "all",
  mlDecision: "all",
  sort: "tier_score",
};

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

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
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

function tArtifactTier(value) {
  const labels = {
    paper_observation_ready: "纸面观察候选",
    research_watchlist: "研究观察",
    needs_review: "需要复核",
    archived_or_failed: "归档/失败",
    blocked_by_safety_review: "安全复核阻断",
  };
  return labels[value] || value || "--";
}

function tArtifactReview(value) {
  return artifactReviewLabels[value] || value || "未复核";
}

function artifactReviewBadge(value) {
  const normalized = String(value || "unreviewed");
  let kind = "";
  if (normalized === "paper_observation" || normalized === "continue_observing") kind = "ok";
  if (normalized === "unreviewed" || normalized === "paused") kind = "warn";
  if (normalized === "rejected") kind = "danger";
  return `<span class="badge ${kind}">${tArtifactReview(normalized)}</span>`;
}

function tPaperTaskStatus(value) {
  return paperTaskStatusLabels[value] || value || "--";
}

function tPaperLogType(value) {
  return paperLogTypeLabels[value] || value || "--";
}

function renderPaperLogTypeOptions(selected = "no_signal") {
  return Object.entries(paperLogTypeLabels).map(([value, label]) => (
    `<option value="${value}" ${value === selected ? "selected" : ""}>${escapeHtml(label)}</option>`
  )).join("");
}

function tPaperHealth(value) {
  return paperHealthLabels[value] || value || "--";
}

function tForwardGate(value) {
  return forwardGateLabels[value] || value || "--";
}

function tMethodType(value) {
  return methodTypeLabels[value] || value || "--";
}

function tMlStatus(value) {
  return mlStatusLabels[value] || value || "--";
}

function tLabelStatus(value) {
  return labelStatusLabels[value] || value || "--";
}

function tCandidateDecision(value) {
  return candidateDecisionLabels[value] || value || "--";
}

function tCandidateQueue(value) {
  return candidateQueueLabels[value] || value || "--";
}

function paperTaskBadge(value) {
  const normalized = String(value || "planned");
  let kind = "";
  if (normalized === "active" || normalized === "completed") kind = "ok";
  if (normalized === "planned" || normalized === "paused") kind = "warn";
  if (normalized === "rejected") kind = "danger";
  return `<span class="badge ${kind}">${tPaperTaskStatus(normalized)}</span>`;
}

function paperHealthBadge(health) {
  const label = health?.healthLabel || "needs_more_observation";
  const tone = health?.healthTone || "warn";
  const kind = tone === "good" ? "ok" : tone === "danger" ? "danger" : "warn";
  return `<span class="badge ${kind}">${tPaperHealth(label)} · ${formatNumber(health?.healthScore, 0)}分</span>`;
}

function forwardGateBadge(value) {
  let kind = "warn";
  if (value === "eligible_for_paper_review") kind = "ok";
  if (value === "needs_active_validation" || value === "needs_risk_review") kind = "danger";
  return `<span class="badge ${kind}">${escapeHtml(tForwardGate(value))}</span>`;
}

function candidateDecisionBadge(value) {
  let kind = "warn";
  if (value === "can_forward_validate" || value === "ml_evaluation_queue") kind = "ok";
  if (value === "paused" || value === "rejected_or_archived") kind = "danger";
  return `<span class="badge ${kind}">${escapeHtml(tCandidateDecision(value))}</span>`;
}

function candidateQueueBadge(value) {
  let kind = "warn";
  if (value === "priority_forward_validation" || value === "ml_evaluation") kind = "ok";
  if (value === "paused" || value === "rejected") kind = "danger";
  return `<span class="badge ${kind}">${escapeHtml(tCandidateQueue(value))}</span>`;
}

function tBaselineComparison(value) {
  return baselineComparisonLabels[value] || value || "--";
}

function artifactBadge(value) {
  const normalized = String(value ?? "--");
  let kind = "";
  if (normalized === "paper_observation_ready") kind = "ok";
  if (normalized === "research_watchlist" || normalized === "needs_review") kind = "warn";
  if (normalized === "archived_or_failed" || normalized === "blocked_by_safety_review") kind = "danger";
  return `<span class="badge ${kind}">${tArtifactTier(normalized)}</span>`;
}

function getArtifactMetric(item, key) {
  const value = item?.metrics?.[key];
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function artifactTierRank(value) {
  const ranks = {
    paper_observation_ready: 0,
    research_watchlist: 1,
    needs_review: 2,
    blocked_by_safety_review: 3,
    archived_or_failed: 4,
  };
  return ranks[value] ?? 9;
}

function getArtifactRows(index) {
  const artifacts = Array.isArray(index.artifacts) ? index.artifacts : [];
  const fallback = Array.isArray(index.topArtifacts) ? index.topArtifacts : [];
  return artifacts.length ? artifacts : fallback;
}

function filterAndSortArtifacts(index) {
  const query = artifactFilters.search.trim().toLowerCase();
  const rows = getArtifactRows(index).filter((item) => {
    const ml = item.mlCoverage || {};
    if (artifactFilters.tier !== "all" && item.readinessTier !== artifactFilters.tier) return false;
    if (artifactFilters.reviewStatus !== "all" && (item.reviewStatus || "unreviewed") !== artifactFilters.reviewStatus) return false;
    if (artifactFilters.mlDecision !== "all" && (ml.candidateDecision || "research_only") !== artifactFilters.mlDecision) return false;
    if (!query) return true;
    return [
      item.displayName,
      item.displaySubtitle,
      item.title,
      item.strategyId,
      item.reportId,
      item.version,
      item.sourceFile,
      item.readinessTier,
      item.recommendedAction,
      ml.methodType,
      ml.methodLabel,
      ml.mlStatus,
      ml.mlStatusLabel,
      ml.labelStatus,
      ml.candidateDecision,
      ml.candidateDecisionLabel,
    ].some((field) => String(field ?? "").toLowerCase().includes(query));
  });

  const sorted = rows.slice();
  sorted.sort((a, b) => {
    if (artifactFilters.sort === "score_desc") {
      return Number(b.researchScore ?? -1) - Number(a.researchScore ?? -1);
    }
    if (artifactFilters.sort === "return_desc") {
      return Number(getArtifactMetric(b, "totalReturnPct") ?? -Infinity) - Number(getArtifactMetric(a, "totalReturnPct") ?? -Infinity);
    }
    if (artifactFilters.sort === "profit_factor_desc") {
      return Number(getArtifactMetric(b, "profitFactor") ?? -Infinity) - Number(getArtifactMetric(a, "profitFactor") ?? -Infinity);
    }
    if (artifactFilters.sort === "drawdown_asc") {
      return Number(getArtifactMetric(a, "maxDrawdownPct") ?? Infinity) - Number(getArtifactMetric(b, "maxDrawdownPct") ?? Infinity);
    }
    if (artifactFilters.sort === "generated_desc") {
      return new Date(b.generatedAt || 0).getTime() - new Date(a.generatedAt || 0).getTime();
    }
    const tierDelta = artifactTierRank(a.readinessTier) - artifactTierRank(b.readinessTier);
    if (tierDelta !== 0) return tierDelta;
    return Number(b.researchScore ?? -1) - Number(a.researchScore ?? -1);
  });
  return sorted;
}

function renderCountGroup(title, counts, labeler) {
  const entries = Object.entries(counts || {});
  if (!entries.length) {
    return `<div class="ml-count-group"><strong>${escapeHtml(title)}</strong><span>暂无数据</span></div>`;
  }
  return `
    <div class="ml-count-group">
      <strong>${escapeHtml(title)}</strong>
      ${entries.map(([key, value]) => `
        <span>${escapeHtml(labeler(key))}<b>${formatNumber(value, 0)}</b></span>
      `).join("")}
    </div>
  `;
}

function renderMlCoverage(summary) {
  const ml = summary?.mlCoverage || {};
  if (!el("mlCoverageSummaryBadge")) return;
  el("mlCoverageSummaryBadge").textContent = `ML 体检完成 · ${formatNumber(ml.totalArtifacts, 0)} 个资产`;
  el("mlDatasetReady").textContent = formatNumber(ml.mlDatasetReadyCount, 0);
  el("mlTrainedModel").textContent = formatNumber(ml.trainedModelReportedCount, 0);
  el("mlForwardCandidates").textContent = formatNumber(ml.forwardCandidateCount, 0);
  el("mlEvaluationQueue").textContent = formatNumber(ml.mlEvaluationQueueCount, 0);
  el("mlCoverageBreakdown").innerHTML = [
    renderCountGroup("方法类型", ml.methodTypeCounts, tMethodType),
    renderCountGroup("ML 状态", ml.mlStatusCounts, tMlStatus),
    renderCountGroup("标签状态", ml.labelStatusCounts, tLabelStatus),
    renderCountGroup("候选决策", ml.candidateDecisionCounts, tCandidateDecision),
  ].join("");
}

function renderCandidateQueue(queuePayload) {
  const queue = queuePayload?.strategyCandidateQueue || queuePayload || {};
  const summary = queue.summary || {};
  const candidates = Array.isArray(queue.candidates) ? queue.candidates : [];
  if (!el("candidateQueueSummaryBadge")) return;
  el("candidateQueueSummaryBadge").textContent = `候选 ${formatNumber(summary.totalCandidates, 0)} · Top ${escapeHtml(summary.topCandidateTitle || "--")}`;
  el("candidateQueueForward").textContent = formatNumber(summary.forwardReadyCount, 0);
  el("candidateQueueMl").textContent = formatNumber(summary.mlEvaluationCount, 0);
  el("candidateQueueBacktest").textContent = formatNumber(summary.needsBacktestCount, 0);
  el("candidateQueueLabels").textContent = formatNumber(summary.needsLabelsCount, 0);
  el("candidateQueueList").innerHTML = candidates.slice(0, 8).map((item) => `
    <div class="candidate-queue-row">
      <div>
        <strong>#${formatNumber(item.rank, 0)} ${escapeHtml(item.title || item.strategyId || "--")}</strong>
        <small>${escapeHtml(item.displaySubtitle || item.originalTitle || item.strategyId || "--")} · ${escapeHtml(item.version || "--")}</small>
      </div>
      <div>
        ${candidateQueueBadge(item.queueType)}
        <span class="status-pill neutral">优先分 ${formatNumber(item.priorityScore, 1)}</span>
      </div>
      <div class="artifact-metrics">
        <span>样本 ${item.sampleCount ?? "--"}</span>
        <span>胜率 ${formatPercent(item.winRatePct)}</span>
        <span>PF ${formatNumber(item.profitFactor)}</span>
        <span>RR ${formatNumber(item.rewardRiskRatio)}</span>
        <span>回撤 ${formatPercent(item.maxDrawdownPct)}</span>
        <span>${escapeHtml(tMlStatus(item.mlStatus))}</span>
      </div>
      <div class="artifact-note">
        ${escapeHtml(item.nextAction || "继续人工复核。")}
        ${Array.isArray(item.decisionReasons) && item.decisionReasons.length ? `<br />原因：${item.decisionReasons.map(escapeHtml).join(" / ")}` : ""}
      </div>
    </div>
  `).join("") || '<div class="item">暂无候选队列。请先生成策略资产索引。</div>';
}

function researchTaskBadge(taskType) {
  const labels = {
    forward_observation: "前向观察",
    backtest_gap: "补回测",
    label_gap: "补标签",
    ml_evaluation: "ML 评价",
  };
  let kind = "warn";
  if (taskType === "forward_observation" || taskType === "ml_evaluation") kind = "ok";
  return `<span class="badge ${kind}">${escapeHtml(labels[taskType] || taskType || "--")}</span>`;
}

function renderResearchTaskRows(tasks, emptyText) {
  return tasks.slice(0, 6).map((task) => `
    <div class="research-task-row">
      <div class="research-task-head">
        <strong>${escapeHtml(task.title || task.strategyId || "--")}</strong>
        ${researchTaskBadge(task.taskType)}
      </div>
      <small>${escapeHtml(task.displaySubtitle || task.version || "--")} · 优先分 ${formatNumber(task.priorityScore, 1)}</small>
      <div class="artifact-metrics">
        <span>样本 ${task.sampleCount ?? "--"}</span>
        <span>胜率 ${formatPercent(task.winRatePct)}</span>
        <span>PF ${formatNumber(task.profitFactor)}</span>
        <span>RR ${formatNumber(task.rewardRiskRatio)}</span>
        <span>回撤 ${formatPercent(task.maxDrawdownPct)}</span>
      </div>
      <div class="artifact-note">
        下一步：${escapeHtml(task.nextAction || "继续人工复核。")}
        ${Array.isArray(task.acceptanceChecks) && task.acceptanceChecks.length ? `<br />验收：${task.acceptanceChecks.slice(0, 2).map(escapeHtml).join(" / ")}` : ""}
      </div>
    </div>
  `).join("") || `<div class="item">${escapeHtml(emptyText)}</div>`;
}

function renderResearchTaskBoard(taskPayload) {
  const board = taskPayload?.researchTaskBoard || taskPayload || {};
  const summary = board.summary || {};
  if (!el("researchTaskSummaryBadge")) return;
  el("researchTaskSummaryBadge").textContent = `任务 ${formatNumber(summary.totalResearchTasks, 0)} · ${escapeHtml(summary.acceptanceGateLabel || "研究排期")}`;
  el("researchTaskForward").textContent = formatNumber(summary.forwardObservationTaskCount, 0);
  el("researchTaskBacktest").textContent = formatNumber(summary.backtestTaskCount, 0);
  el("researchTaskLabels").textContent = formatNumber(summary.labelTaskCount, 0);
  el("researchTaskMl").textContent = formatNumber(summary.mlEvaluationTaskCount, 0);
  const forwardTasks = Array.isArray(board.forwardObservationTasks) ? board.forwardObservationTasks : [];
  const backtestTasks = Array.isArray(board.backtestTasks) ? board.backtestTasks : [];
  el("forwardResearchTaskList").innerHTML = renderResearchTaskRows(forwardTasks, "暂无前向观察任务。");
  el("backtestResearchTaskList").innerHTML = renderResearchTaskRows(backtestTasks, "暂无需要补回测的任务。");
}

function renderArtifactDetail(item) {
  if (!item) {
    el("artifactDetail").innerHTML = '<div class="item">请选择一个策略资产查看详情。</div>';
    return;
  }
  const metrics = item.metrics || {};
  const reasons = Array.isArray(item.readinessReasons) ? item.readinessReasons : [];
  const score = item.scoreBreakdown || {};
  const checklist = item.paperObservationChecklist || {};
  const task = item.paperObservationTask || {};
  const health = task.health || {};
  const recentLogs = Array.isArray(task.recentLogs) ? task.recentLogs : [];
  const ml = item.mlCoverage || {};
  const decisionReasons = Array.isArray(ml.decisionReasons) ? ml.decisionReasons : [];
  el("artifactDetail").innerHTML = `
    <div class="artifact-detail-main">
      <div>
        <p class="panel-eyebrow">SELECTED ARTIFACT</p>
        <h3>${escapeHtml(item.displayName || item.title || item.strategyId || "--")}</h3>
        <small>${escapeHtml(item.displaySubtitle || "本地策略资产")} · 原始ID ${escapeHtml(item.strategyId || "--")} · ${escapeHtml(item.version || "--")}</small>
      </div>
      <div class="artifact-detail-status">
        ${artifactBadge(item.readinessTier)}
        ${artifactReviewBadge(item.reviewStatus)}
        ${paperHealthBadge(health)}
        ${candidateDecisionBadge(ml.candidateDecision)}
        <span class="status-pill neutral">评分 ${formatNumber(item.researchScore, 0)}</span>
      </div>
    </div>
    <div class="artifact-detail-grid">
      <div><span>样本</span><strong>${metrics.sampleCount ?? metrics.tradeCount ?? "--"}</strong></div>
      <div><span>胜率</span><strong>${formatPercent(metrics.winRatePct)}</strong></div>
      <div><span>PF</span><strong>${formatNumber(metrics.profitFactor)}</strong></div>
      <div><span>盈亏比</span><strong>${formatNumber(metrics.rewardRiskRatio)}</strong></div>
      <div><span>回撤</span><strong>${formatPercent(metrics.maxDrawdownPct)}</strong></div>
      <div><span>收益</span><strong>${formatPercent(metrics.totalReturnPct)}</strong></div>
      <div><span>纸面观察</span><strong>${item.paperObservationEligible ? "可观察" : "不可观察"}</strong></div>
      <div><span>实盘权限</span><strong>${item.liveTradingApproved ? "异常开启" : "关闭"}</strong></div>
    </div>
    <div class="artifact-ml-grid">
      <div><span>方法类型</span><strong>${escapeHtml(tMethodType(ml.methodType))}</strong></div>
      <div><span>ML 状态</span><strong>${escapeHtml(tMlStatus(ml.mlStatus))}</strong></div>
      <div><span>标签状态</span><strong>${escapeHtml(tLabelStatus(ml.labelStatus))}</strong></div>
      <div><span>前向验证</span><strong>${escapeHtml(ml.walkForwardStatusLabel || ml.walkForwardStatus || "--")}</strong></div>
      <div><span>候选决策</span><strong>${escapeHtml(tCandidateDecision(ml.candidateDecision))}</strong></div>
    </div>
    <div class="artifact-score-grid">
      <div><span>胜率贡献</span><strong>${formatNumber(score.winRateContribution, 1)}</strong></div>
      <div><span>盈亏比贡献</span><strong>${formatNumber(score.rewardRiskContribution, 1)}</strong></div>
      <div><span>样本惩罚</span><strong>${formatNumber(score.sampleSizePenalty, 1)}</strong></div>
      <div><span>回撤惩罚</span><strong>${formatNumber(score.drawdownPenalty, 1)}</strong></div>
      <div><span>基线对比</span><strong>${tBaselineComparison(score.baselineComparison)}</strong></div>
    </div>
    <div class="artifact-checklist-grid">
      <div><span>观察状态</span><strong>${checklistStatusLabels[checklist.status] || checklist.status || "--"}</strong></div>
      <div><span>开始时间</span><strong>${formatDate(checklist.startAt)}</strong></div>
      <div><span>样本进度</span><strong>${checklist.currentSampleCount ?? "--"} / ${checklist.targetSampleCount ?? "--"}</strong></div>
      <div><span>进度</span><strong>${formatPercent(checklist.progressPct)}</strong></div>
    </div>
    <div class="artifact-checklist-grid">
      <div><span>任务状态</span><strong>${tPaperTaskStatus(task.taskStatus)}</strong></div>
      <div><span>任务开始</span><strong>${formatDate(task.startedAt)}</strong></div>
      <div><span>目标样本</span><strong>${task.currentSampleCount ?? "--"} / ${task.targetSampleCount ?? "--"}</strong></div>
      <div><span>观察天数</span><strong>${task.observationDays ?? "--"} 天</strong></div>
    </div>
    <div class="artifact-health-grid">
      <div><span>健康分</span><strong>${formatNumber(health.healthScore, 0)}</strong></div>
      <div><span>健康状态</span><strong>${tPaperHealth(health.healthLabel)}</strong></div>
      <div><span>观察日志</span><strong>${health.logCount ?? 0}</strong></div>
      <div><span>规则匹配</span><strong>${health.ruleMatchedCount ?? 0}</strong></div>
      <div><span>风险提醒</span><strong>${health.riskWarningCount ?? 0}</strong></div>
      <div><span>最新日志</span><strong>${formatDate(health.latestLogAt)}</strong></div>
    </div>
    <div class="artifact-detail-note">
      <strong>ML 覆盖说明</strong>
      <span>${escapeHtml(ml.note || "ML 状态只代表研究数据准备度，不是交易信号。")}</span>
      ${decisionReasons.length ? `<small>决策原因：${decisionReasons.map(escapeHtml).join(" / ")}</small>` : ""}
    </div>
    <div class="artifact-review-actions">
      <input id="artifactReviewNote" value="${escapeHtml(item.reviewNote || "")}" placeholder="复核备注，只保存在本地，不会触发交易…" autocomplete="off" />
      <button type="button" data-review-status="continue_observing">继续观察</button>
      <button type="button" data-review-status="paper_observation">进入纸面观察</button>
      <button type="button" data-review-status="paused">暂停</button>
      <button type="button" data-review-status="rejected">淘汰</button>
    </div>
    <div class="paper-task-actions">
      <input id="paperTaskTarget" type="number" min="10" max="500" value="${escapeHtml(task.targetSampleCount || checklist.targetSampleCount || 50)}" autocomplete="off" />
      <input id="paperTaskDays" type="number" min="7" max="365" value="${escapeHtml(task.observationDays || 60)}" autocomplete="off" />
      <input id="paperTaskNote" value="${escapeHtml(task.note || item.reviewNote || "")}" placeholder="观察任务备注，只保存在本地…" autocomplete="off" />
      <button type="button" data-task-status="active">启动任务</button>
      <button type="button" data-task-status="paused">暂停任务</button>
      <button type="button" data-task-status="completed">完成任务</button>
      <button type="button" data-task-status="rejected">淘汰任务</button>
    </div>
    <div class="paper-log-actions">
      <select id="paperLogType" autocomplete="off">
        ${Object.entries(paperLogTypeLabels).map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}
      </select>
      <label><input id="paperLogSignalObserved" type="checkbox" /> 看到信号</label>
      <label><input id="paperLogRuleMatched" type="checkbox" /> 规则匹配</label>
      <input id="paperLogOutcome" value="" placeholder="观察结果，例如：未触发 / 符合 / 失效" autocomplete="off" />
      <input id="paperLogNote" value="" placeholder="添加纸面观察日志，不会创建订单…" autocomplete="off" />
      <button type="button" data-log-action="add">记录日志</button>
    </div>
    <div class="paper-log-list">
      ${recentLogs.length ? recentLogs.map((log) => `
        <div class="paper-log-row">
          <strong>${tPaperLogType(log.logType)}</strong>
          <span>${formatDate(log.createdAt)} · ${escapeHtml(log.outcome || "未写结果")}</span>
          <small>${escapeHtml(log.note || "无备注")}</small>
        </div>
      `).join("") : '<div class="paper-log-empty">暂无观察日志。先记录无信号、看到信号、规则匹配或风险提醒。</div>'}
    </div>
    <div class="artifact-detail-note">
      <strong>下一步复核动作</strong>
      <span>${escapeHtml(health.nextReviewAction || "继续记录纸面观察日志。")} ${Array.isArray(health.riskFlags) && health.riskFlags.length ? `风险：${health.riskFlags.map(escapeHtml).join(" / ")}` : ""}</span>
    </div>
    <div class="artifact-detail-note">
      <strong>建议动作</strong>
      <span>${escapeHtml(item.recommendedAction || "本地研究资产，不代表交易指令。")}</span>
    </div>
    <div class="artifact-detail-note">
      <strong>候选原因</strong>
      <span>${reasons.length ? reasons.map(escapeHtml).join(" / ") : "未记录额外原因"}</span>
    </div>
    <div class="artifact-detail-note">
      <strong>复核备注</strong>
      <span>${escapeHtml(item.reviewNote || "暂无复核备注。")}</span>
    </div>
    <div class="artifact-detail-note">
      <strong>纸面观察清单</strong>
      <span>${Array.isArray(checklist.requiredChecks) ? checklist.requiredChecks.map(escapeHtml).join(" / ") : "等待复核。"} ${escapeHtml(checklist.safetyNote || "")}</span>
    </div>
  `;
  el("artifactDetail").querySelectorAll("[data-review-status]").forEach((button) => {
    button.addEventListener("click", async () => {
      const reviewStatus = button.getAttribute("data-review-status");
      const note = el("artifactReviewNote")?.value || "";
      button.disabled = true;
      try {
        const response = await postJson("/api/strategy-artifact-review", {
          artifactId: item.artifactId,
          reviewStatus,
          note,
        });
        latestArtifactIndex = response.strategyArtifactIndex || latestArtifactIndex;
        await refreshAll();
      } finally {
        button.disabled = false;
      }
    });
  });
  el("artifactDetail").querySelectorAll("[data-task-status]").forEach((button) => {
    button.addEventListener("click", async () => {
      const taskStatus = button.getAttribute("data-task-status");
      const note = el("paperTaskNote")?.value || "";
      const targetSampleCount = Number(el("paperTaskTarget")?.value || 50);
      const observationDays = Number(el("paperTaskDays")?.value || 60);
      button.disabled = true;
      try {
        const response = await postJson("/api/paper-observation-task", {
          artifactId: item.artifactId,
          taskStatus,
          note,
          targetSampleCount,
          observationDays,
        });
        latestArtifactIndex = response.strategyArtifactIndex || latestArtifactIndex;
        await refreshAll();
      } finally {
        button.disabled = false;
      }
    });
  });
  el("artifactDetail").querySelectorAll("[data-log-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const response = await postJson("/api/paper-observation-log", {
          artifactId: item.artifactId,
          logType: el("paperLogType")?.value || "no_signal",
          signalObserved: Boolean(el("paperLogSignalObserved")?.checked),
          ruleMatched: Boolean(el("paperLogRuleMatched")?.checked),
          outcome: el("paperLogOutcome")?.value || "",
          note: el("paperLogNote")?.value || "",
        });
        latestArtifactIndex = response.strategyArtifactIndex || latestArtifactIndex;
        await refreshAll();
      } finally {
        button.disabled = false;
      }
    });
  });
}

function renderStrategyArtifacts(indexPayload) {
  const index = indexPayload?.strategyArtifactIndex || indexPayload || {};
  const summary = index.summary || {};
  latestArtifactIndex = index;
  const allArtifacts = getArtifactRows(index);
  const artifacts = filterAndSortArtifacts(index);

  el("artifactTotal").textContent = summary.totalArtifacts ?? "--";
  el("artifactPaperReady").textContent = summary.paperObservationReadyCount ?? "--";
  el("artifactWatchlist").textContent = summary.researchWatchlistCount ?? "--";
  el("artifactNeedsReview").textContent = summary.manualReviewCount ?? summary.needsReviewCount ?? "--";
  el("artifactGeneratedAt").textContent = formatDate(index.generatedAt);
  el("artifactResultLine").textContent = `当前显示 ${artifacts.length}/${allArtifacts.length} 个策略资产，排序：${el("artifactSort")?.selectedOptions?.[0]?.textContent || "候选优先"}`;
  renderMlCoverage(summary);

  if (!artifacts.some((item) => item.artifactId === selectedArtifactId)) {
    selectedArtifactId = artifacts[0]?.artifactId || null;
  }
  renderArtifactDetail(artifacts.find((item) => item.artifactId === selectedArtifactId));

  el("artifactList").innerHTML = artifacts.slice(0, 18).map((item) => {
    const metrics = item.metrics || {};
    const ml = item.mlCoverage || {};
    const selected = item.artifactId === selectedArtifactId ? " selected" : "";
    return `
      <button class="artifact-row${selected}" data-artifact-id="${escapeHtml(item.artifactId)}" type="button">
        <div>
          <strong>${escapeHtml(item.displayName || item.title || item.strategyId || "--")}</strong>
          <small>${escapeHtml(item.displaySubtitle || item.strategyId || "--")} · ${escapeHtml(item.version || "--")}</small>
        </div>
        <div>
          ${artifactBadge(item.readinessTier)}
          ${artifactReviewBadge(item.reviewStatus)}
          ${candidateDecisionBadge(ml.candidateDecision)}
        </div>
        <div class="artifact-metrics">
          <span>样本 ${metrics.sampleCount ?? "--"}</span>
          <span>胜率 ${formatPercent(metrics.winRatePct)}</span>
          <span>PF ${formatNumber(metrics.profitFactor)}</span>
          <span>RR ${formatNumber(metrics.rewardRiskRatio)}</span>
          <span>回撤 ${formatPercent(metrics.maxDrawdownPct)}</span>
          <span>收益 ${formatPercent(metrics.totalReturnPct)}</span>
        </div>
        <div class="artifact-note">
          ${escapeHtml(item.recommendedAction || "本地研究资产，不代表交易指令。")}
          <br />方法 ${escapeHtml(tMethodType(ml.methodType))} · ML ${escapeHtml(tMlStatus(ml.mlStatus))} · 标签 ${escapeHtml(tLabelStatus(ml.labelStatus))}
        </div>
      </button>
    `;
  }).join("") || '<div class="item">暂无策略资产索引。请先在 Quant Engine 生成 strategy_artifact_index.json。</div>';

  document.querySelectorAll("[data-artifact-id]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedArtifactId = button.getAttribute("data-artifact-id");
      renderStrategyArtifacts(latestArtifactIndex);
    });
  });
}

function renderPaperObservationTasks(taskPayload) {
  const tasks = Array.isArray(taskPayload?.tasks) ? taskPayload.tasks : [];
  const summary = taskPayload?.summary || {};
  latestPaperTasks = tasks;
  el("paperTaskTotal").textContent = String(summary.totalTasks ?? tasks.length);
  el("paperTaskActive").textContent = String(summary.activeCount ?? tasks.filter((item) => item.taskStatus === "active").length);
  el("paperTaskPaused").textContent = String(summary.pausedCount ?? tasks.filter((item) => item.taskStatus === "paused").length);
  el("paperTaskCompleted").textContent = String(summary.completedCount ?? tasks.filter((item) => item.taskStatus === "completed").length);
  el("paperTaskHealthy").textContent = String(summary.healthyCount ?? tasks.filter((item) => item.health?.healthLabel === "healthy_observation").length);
  el("paperTaskNeedsReview").textContent = String(summary.needsReviewCount ?? tasks.filter((item) => item.health?.healthLabel === "needs_review").length);
  el("paperTaskLogCount").textContent = String(summary.totalLogCount ?? tasks.reduce((total, item) => total + Number(item.health?.logCount || 0), 0));
  el("paperTaskLatestLog").textContent = formatDate(summary.latestLogAt);

  el("paperObservationTaskList").innerHTML = tasks.slice(0, 20).map((task) => {
    const progress = Number(task.progressPct || 0);
    const metrics = task.metrics || {};
    const health = task.health || {};
    const logs = Array.isArray(task.recentLogs) ? task.recentLogs.slice(0, 2) : [];
    return `
      <div class="paper-task-row">
        <div>
          <strong>${escapeHtml(task.title || task.artifactId || "--")}</strong>
          <small>${escapeHtml(task.displaySubtitle || task.originalTitle || task.strategyId || "--")} · ${escapeHtml(task.version || "--")}</small>
          ${paperTaskBadge(task.taskStatus)}
          ${paperHealthBadge(health)}
        </div>
        <div>
          <span>样本进度</span>
          <strong>${task.currentSampleCount ?? "--"} / ${task.targetSampleCount ?? "--"}</strong>
          <div class="paper-task-progress"><i style="width:${Math.max(0, Math.min(100, progress))}%"></i></div>
        </div>
        <div><span>观察天数</span><strong>${task.observationDays ?? "--"} 天</strong></div>
        <div><span>胜率 / PF</span><strong>${formatPercent(metrics.winRatePct)} / ${formatNumber(metrics.profitFactor)}</strong></div>
        <div><span>日志 / 匹配</span><strong>${health.logCount ?? 0} / ${health.ruleMatchedCount ?? 0}</strong></div>
        <div><span>更新时间</span><strong>${formatDate(task.updatedAt || task.startedAt)}</strong></div>
        <div class="paper-task-log-strip">
          ${logs.length ? logs.map((log) => `<small>${tPaperLogType(log.logType)} · ${formatDate(log.createdAt)} · ${escapeHtml(log.note || log.outcome || "无备注")}</small>`).join("") : "<small>暂无日志</small>"}
        </div>
      </div>
    `;
  }).join("") || '<div class="item">暂无纸面观察任务。请在策略资产详情中点击“进入纸面观察”或“启动任务”。</div>';
}

function renderForwardValidation(forwardValidation) {
  const summary = forwardValidation || {};
  el("forwardValidationAnswer").textContent = summary.answerSummary || "等待前向验证数据。";
  el("forwardValidationGate").outerHTML = forwardGateBadge(summary.acceptanceGate).replace("<span ", '<span id="forwardValidationGate" ');
  el("forwardStrictActive").textContent = String(summary.strictActiveValidationCount ?? 0);
  el("forwardRawActive").textContent = String(summary.rawActiveTaskCount ?? 0);
  el("forwardTestTasks").textContent = String(summary.testOnlyActiveTaskCount ?? 0);
  el("forwardCandidatePool").textContent = String(summary.candidatePoolCount ?? 0);
  el("forwardLogCount").textContent = String(summary.totalObservationLogCount ?? 0);
  el("forwardRuleMatches").textContent = String(summary.ruleMatchedCount ?? 0);
  el("forwardReviewDate").textContent = summary.reviewDateLabel || "--";
  el("forwardDaysLeft").textContent = `${summary.daysUntilReview ?? "--"} 天`;
  const checks = Array.isArray(summary.minimumAcceptanceChecks) ? summary.minimumAcceptanceChecks : [];
  const method = Array.isArray(summary.validationMethod) ? summary.validationMethod : [];
  el("forwardValidationMethod").innerHTML = `
    <div>
      <strong>如何验证</strong>
      ${method.map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
    </div>
    <div>
      <strong>最低验收门槛</strong>
      ${checks.map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
    </div>
  `;
}

function renderStrategyLearningLoop(loopPayload) {
  const payload = loopPayload?.strategyLearningLoop || loopPayload || {};
  const summary = payload.summary || {};
  const learningLoop = payload.learningLoop || {};
  const refactorReport = payload.refactorCandidates || {};
  const experimentReport = payload.experimentSpecs || {};
  const rereviewReport = payload.paperReReview || {};
  const observationTaskPack = payload.paperObservationTaskPack || {};
  const graveyard = Array.isArray(learningLoop.strategyGraveyard) ? learningLoop.strategyGraveyard : [];
  const refactors = Array.isArray(refactorReport.refactorCandidates) ? refactorReport.refactorCandidates : [];
  const experiments = Array.isArray(experimentReport.experimentSpecs) ? experimentReport.experimentSpecs : [];
  const reviews = Array.isArray(rereviewReport.paperObservationReviews) ? rereviewReport.paperObservationReviews : [];
  const observationTasks = Array.isArray(observationTaskPack.paperObservationTasks)
    ? observationTaskPack.paperObservationTasks
    : [];
  const logbook = payload.paperObservationLogbook || {};
  const logbookSummary = logbook.summary || {};

  el("learningItemCount").textContent = String(summary.learningItemCount ?? "--");
  el("learningGraveyardCount").textContent = String(summary.graveyardCount ?? graveyard.length);
  el("learningWatchlistCount").textContent = String(summary.researchWatchlistCount ?? "--");
  el("learningRefactorCount").textContent = String(summary.refactorCandidateCount ?? refactors.length);
  el("learningExperimentCount").textContent = String(summary.experimentSpecCount ?? experiments.length);
  el("learningPaperApproved").textContent = String(summary.paperObservationApprovedCount ?? 0);
  el("learningBacktestTradeCount").textContent = String(summary.deterministicBacktestTradeCount ?? "--");
  el("learningBacktestPf").textContent = formatNumber(summary.deterministicBacktestProfitFactor);
  el("learningFiveStrategyApproved").textContent = String(summary.fiveStrategyApprovedCount ?? "--");
  el("learningFiveStrategyTarget").textContent = String(summary.fiveStrategyTargetApprovedCount ?? "--");
  el("learningObservationTaskPack").textContent = String(summary.observationTaskPackCount ?? observationTasks.length ?? "--");
  el("learningObservationTargetSamples").textContent = String(summary.observationTaskTargetClosedSamplesTotal ?? "--");
  if (el("learningObservationLogCount")) {
    el("learningObservationLogCount").textContent = String(summary.observationCurrentLogCount ?? logbookSummary.currentLogCount ?? 0);
  }
  if (el("learningObservationRuleMatches")) {
    el("learningObservationRuleMatches").textContent = String(summary.observationRuleMatchedCount ?? logbookSummary.ruleMatchedCount ?? 0);
  }
  if (el("learningObservationClosedSamples")) {
    el("learningObservationClosedSamples").textContent = String(summary.observationClosedPaperSampleCount ?? logbookSummary.closedPaperSampleCount ?? 0);
  }
  el("learningDryRun").textContent = summary.dryRunApproved ? "异常：开启" : "关闭";
  el("learningLive").textContent = summary.liveTradingApproved ? "异常：开启" : "关闭";
  el("learningNextStep").textContent = summary.nextExecutableResearchStep || "等待下一轮确定性回测实现。";

  el("learningRefactorList").innerHTML = refactors.slice(0, 8).map((item) => `
    <div class="research-task-row">
      <strong>${escapeHtml(item.title || item.candidateId || "--")}</strong>
      <small>${escapeHtml(item.candidateId || "--")} · 优先级 ${escapeHtml(item.priority || "--")}</small>
      <div>${escapeHtml(item.hypothesis || "等待研究假设。")}</div>
      <div>
        <span class="badge ${item.specReadyForResearchBacktest ? "ok" : "warn"}">${item.specReadyForResearchBacktest ? "可转研究回测规格" : "需要补证据"}</span>
        <span class="badge danger">${item.paperObservationAllowed ? "纸面观察异常开启" : "纸面观察未开放"}</span>
      </div>
    </div>
  `).join("") || '<div class="item">暂无重构候选。</div>';

  el("learningExperimentList").innerHTML = experiments.slice(0, 8).map((item) => {
    const gates = item.passGate || {};
    const gateText = Object.entries(gates).slice(0, 4).map(([key, value]) => `${key}: ${value}`).join(" / ");
    return `
      <div class="research-task-row">
        <strong>${escapeHtml(item.experimentId || "--")}</strong>
        <small>${escapeHtml((item.timeframes || []).join(" / ") || "--")} · ${escapeHtml(item.sourceCandidateId || "--")}</small>
        <div>${escapeHtml((item.entryResearchConditions || []).slice(0, 3).join("；") || "等待入场研究条件。")}</div>
        <div><span class="badge warn">${escapeHtml(gateText || "等待回测门槛")}</span></div>
      </div>
    `;
  }).join("") || '<div class="item">暂无实验规格。</div>';

  el("learningGraveyardList").innerHTML = graveyard.slice(0, 8).map((item) => `
    <div class="item">
      <strong>${escapeHtml(item.title || item.subjectId || "--")}</strong>
      <small>${escapeHtml(item.subjectId || "--")}</small>
      <div>${escapeHtml(item.reason || "失败原因待补充。")}</div>
      <div>复活条件：${escapeHtml(item.resurrectionRule || "暂无")}</div>
    </div>
  `).join("") || '<div class="item">暂无失败归档。</div>';

  el("learningPaperReviewList").innerHTML = reviews.slice(0, 8).map((item) => `
    <div class="item">
      <strong>${escapeHtml(item.experimentId || "--")}</strong>
      <small>${escapeHtml(item.paperObservationStatus || "--")} · readiness ${formatNumber(item.readinessScore, 0)}</small>
      <div>缺失证据：${escapeHtml((item.missingEvidence || []).join(" / ") || "无")}</div>
      <div>允许下一步：${escapeHtml(item.allowedNextAction || "研究回测")}</div>
    </div>
  `).join("") || '<div class="item">暂无纸面观察复审。</div>';

  el("learningObservationTaskPackList").innerHTML = observationTasks.slice(0, 5).map((task) => {
    const metrics = task.historicalMetrics || {};
    const plan = task.observationPlan || {};
    const localObservation = task.localObservation || {};
    const recentLogs = Array.isArray(task.recentLogs) ? task.recentLogs.slice(0, 3) : [];
    const weakPoints = Array.isArray(task.weakPoints) ? task.weakPoints : [];
    return `
      <div class="research-task-row task-pack-card" data-task-pack-card="${escapeHtml(task.taskId || "")}">
        <div class="research-task-head">
          <strong>${escapeHtml(task.title || task.candidateId || "--")}</strong>
          <span class="status-pill ok">${escapeHtml(plan.confidenceTier || "paper")}</span>
        </div>
        <small>${escapeHtml(task.displaySubtitle || "固定 2R · 本地纸面观察")} · ${escapeHtml(task.candidateId || "--")}</small>
        <div class="artifact-metrics">
          <span>目标样本 ${plan.targetClosedSamples ?? "--"}</span>
          <span>观察 ${plan.observationDays ?? "--"} 天</span>
          <span>历史 ${metrics.tradeCount ?? "--"} 笔</span>
          <span>PF ${formatNumber(metrics.profitFactor)}</span>
          <span>胜率 ${formatPercent(metrics.winRatePct)}</span>
          <span>回撤 ${formatPercent(metrics.maxDrawdownPct)}</span>
        </div>
        <div class="artifact-metrics">
          <span>日志 ${localObservation.logCount ?? 0}</span>
          <span>规则匹配 ${localObservation.ruleMatchedCount ?? 0}</span>
          <span>信号出现 ${localObservation.signalObservedCount ?? 0}</span>
          <span>闭合样本 ${localObservation.closedPaperSampleCount ?? 0}</span>
          <span>最近 ${formatDate(localObservation.latestLogAt)}</span>
        </div>
        <div>弱点：${weakPoints.slice(0, 2).map(escapeHtml).join(" / ") || "等待前向样本验证"}</div>
        <div class="task-pack-recent-logs">
          ${recentLogs.length ? recentLogs.map((log) => `
            <small>${escapeHtml(tPaperLogType(log.logType))} · ${formatDate(log.createdAt)} · ${escapeHtml(log.outcome || log.note || "已记录")}</small>
          `).join("") : "<small>暂无本地观察日志</small>"}
        </div>
        <div class="task-pack-log-form">
          <select data-task-pack-log-type>
            ${renderPaperLogTypeOptions("no_signal")}
          </select>
          <input data-task-pack-outcome placeholder="纸面结果R，例如 0 / 1.2 / -1" autocomplete="off" />
          <input data-task-pack-note placeholder="观察备注：币种、形态、无效原因、截图说明" autocomplete="off" />
          <button type="button" data-task-pack-log="${escapeHtml(task.taskId || "")}">记录观察</button>
        </div>
      </div>
    `;
  }).join("") || '<div class="item">暂无五策略纸面观察任务包。</div>';
  el("learningObservationTaskPackList").querySelectorAll("[data-task-pack-log]").forEach((button) => {
    button.addEventListener("click", async () => {
      const card = button.closest("[data-task-pack-card]");
      const taskId = button.getAttribute("data-task-pack-log") || "";
      const logType = card?.querySelector("[data-task-pack-log-type]")?.value || "no_signal";
      const outcome = card?.querySelector("[data-task-pack-outcome]")?.value || "";
      const note = card?.querySelector("[data-task-pack-note]")?.value || "";
      button.disabled = true;
      try {
        await postJson("/api/paper-observation-log", {
          artifactId: taskId,
          logType,
          signalObserved: ["signal_seen", "rule_matched"].includes(logType),
          ruleMatched: logType === "rule_matched",
          outcome,
          note,
        });
        await refreshAll();
      } finally {
        button.disabled = false;
      }
    });
  });
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
  const [strategies, reports, mobile, connection, audit, exchanges, slots, artifacts, paperTasks, candidateQueue, researchTaskBoard, strategyLearningLoop] = await Promise.all([
    getJson("/api/strategies"),
    getJson("/api/reports"),
    getJson("/api/mobile/status"),
    getJson("/api/mobile/connection-info"),
    getJson("/api/audit"),
    getJson("/api/exchanges"),
    getJson("/api/strategy-slots"),
    getJson("/api/strategy-artifacts"),
    getJson("/api/paper-observation-tasks"),
    getJson("/api/candidate-queue"),
    getJson("/api/research-task-board"),
    getJson("/api/strategy-learning-loop"),
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
  renderStrategyArtifacts(artifacts);
  renderCandidateQueue(candidateQueue);
  renderResearchTaskBoard(researchTaskBoard);
  renderStrategyLearningLoop(strategyLearningLoop);
  renderForwardValidation(mobile.forwardValidation);
  renderPaperObservationTasks(paperTasks);
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
el("artifactSearch").addEventListener("input", (event) => {
  artifactFilters.search = event.target.value || "";
  selectedArtifactId = null;
  renderStrategyArtifacts(latestArtifactIndex);
});
el("artifactTierFilter").addEventListener("change", (event) => {
  artifactFilters.tier = event.target.value || "all";
  selectedArtifactId = null;
  renderStrategyArtifacts(latestArtifactIndex);
});
el("artifactReviewFilter").addEventListener("change", (event) => {
  artifactFilters.reviewStatus = event.target.value || "all";
  selectedArtifactId = null;
  renderStrategyArtifacts(latestArtifactIndex);
});
el("artifactMlDecisionFilter").addEventListener("change", (event) => {
  artifactFilters.mlDecision = event.target.value || "all";
  selectedArtifactId = null;
  renderStrategyArtifacts(latestArtifactIndex);
});
el("artifactSort").addEventListener("change", (event) => {
  artifactFilters.sort = event.target.value || "tier_score";
  renderStrategyArtifacts(latestArtifactIndex);
});
window.addEventListener("scroll", updateCurrentSection, { passive: true });
window.addEventListener("hashchange", updateCurrentSection);

refreshAll().catch((error) => {
  el("strategyList").innerHTML = `<div class="item">加载失败：${error.message}</div>`;
});
updateCurrentSection();
