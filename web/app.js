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

const observationQualityLabels = {
  not_started: "未开始",
  needs_more_logs: "需要补日志",
  continue_observing: "继续观察",
  priority_watch: "优先观察",
  needs_risk_review: "需要风险复核",
  pause_candidate: "暂停候选",
};

const forwardGateLabels = {
  needs_active_validation: "还没有正式验证中的策略",
  waiting_until_review_date: "等待 7 月 10 日前向验收",
  needs_observation_logs: "需要补观察日志",
  needs_rule_match: "需要至少一次规则匹配",
  needs_risk_review: "需要先复核风险/失效记录",
  eligible_for_paper_review: "可进入纸面观察复核",
};

const simulationReviewStatusLabels = {
  collecting_samples: "样本收集中",
  under_review: "进入复核",
  promoted_candidate: "晋级候选",
  watchlist: "观察名单",
  paused: "暂停",
  demoted: "降级",
  archived_reference: "归档参考",
};

const simulationReviewActionLabels = {
  "继续收集样本": "继续收样",
  "进入人工复核": "人工复核",
  "可列入晋级候选，继续人工复核": "晋级候选",
  "降级为参考或暂停观察": "降级参考",
  "先复核风险或失效样本": "风险复核",
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

const shortCycleValidationLabels = {
  existing_report_needs_expanded_retest: "已有资产 · 扩样本复测",
  existing_report_needs_quality_review: "已有资产 · 质量复核",
  existing_report_needs_failure_filter: "已有资产 · 失败过滤",
  derived_needs_30m_backtest: "派生候选 · 补 30m 回测",
  derived_needs_15m_backtest: "派生候选 · 补 15m 回测",
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
  simpleConsole: "策略",
  localLab: "本地模拟",
  exchangeDemo: "Demo模拟",
  liveTradingPage: "实盘交易",
  mobileConsole: "手机控制台",
  overview: "驾驶舱",
  command: "策略总控",
  runtime: "运行监控",
  artifacts: "策略资产",
  observationTasks: "观察任务",
  learning: "学习闭环",
  liveReadiness: "实盘准备",
  forwardReview: "前向复核",
  exchanges: "公共行情",
  mobile: "手机控制台",
  audit: "审计日志",
};

const hashAliases = {
  mobile: "mobileConsole",
};

const primaryPageIds = ["simpleConsole", "localLab", "exchangeDemo", "liveTradingPage", "mobileConsole"];

let latestStrategies = [];
let latestArtifactIndex = {};
let latestPaperTasks = [];
let latestStrategyLearningLoopPayload = {};
let selectedArtifactId = null;
let selectedStrategyPlaybookTaskId = null;
let latestStrategyPlaybookTask = null;
let latestSimpleConsolePayload = {};
let latestQualityCenterPayload = {};
let latestConcentrationReviewPayload = {};
let latestResultReviewPayload = {};
let latestStrategyAssetPlaybookPayload = {};
let selectedQualityCenterTaskId = null;
let latestClosedSampleReplayPayload = {};
let selectedClosedSampleReplayTaskId = null;
let latestWeaknessActionBoardPayload = {};
let latestResearchPipelinePayload = {};
let latestTestnetDesignBoundaryPayload = {};
let latestPreLivePreparationPayload = {};
let latestTestnetDrillPayload = {};
let latestTestnetAuditPayload = {};
let latestTestnetPermissionPayload = {};
let latestTestnetSmallOrderPayload = {};
let latestExchangeDemoPayload = {};
let latestExchangeDemoCandidate = null;
let latestDemoWorkflowPayload = { summary: {}, queues: {} };
let demoWorkflowLoading = null;
let demoWorkflowPollTimer = null;
let activeDemoOverrideStrategyId = null;
let demoRuntimeLaunchInProgress = false;
let latestNoKeyPreLivePayload = {};
let latestNoKeyPreLiveCandidate = null;
let latestAutoExecutionEnginePayload = {};
let latestAutoExecutionLifecyclePayload = {};
let latestAutoExecutionReviewPayload = {};
let latestAutoExecutionLearningPayload = {};
let latestLiveCandidatePayload = {};
let latestLiveCanaryPayload = {};
let selectedLiveCandidatePackageId = null;
let latestRiskProfilePayload = {};
let selectedRiskProfileId = null;
let latestExecutionOutcomeExportPath = "";
let latestMobilePayload = {};
let latestSandboxReviewPayload = {};
let latestCoreConsolePayload = {};
let sandboxReviewLoading = null;
let localLabEnrichmentLoading = null;
let advancedDataLoading = null;
let mobileStatusLoading = null;
let advancedDataLoaded = false;
let mobileStatusLoaded = false;
let latestAdvancedPayload = {};
let latestWorkflowPayload = {};
let latestStrategyLifecyclePayload = {};
let workflowPollTimer = null;
let activeOptimizationContext = null;

const emptyMobileStatus = {
  commandSummary: {},
  exchangeConnectivity: {},
  runtimeStatus: {},
  signalTape: {},
  paperObservationLedger: {},
  safetyBoundary: { orderCreationAllowed: false },
};
const emptySimulationBridge = { summary: {}, observationTasks: [] };
const emptySimulationReview = { queue: [], summary: {} };
const emptyStrategyLearningLoop = { summary: {}, refactorCandidates: [], experimentSpecs: [] };
const emptyStrategyLifecycle = {
  summary: {},
  items: [],
  byStage: {},
  archiveSummary: {},
  sourceWarnings: [],
};
const emptyWorkflow = {
  version: "V13.27.1.5",
  summary: {},
  items: [],
  archivedItems: [],
  safetyBoundary: { createsOrders: false, usesApiKey: false },
};
const artifactFilters = {
  search: "",
  tier: "all",
  reviewStatus: "all",
  mlDecision: "all",
  sort: "tier_score",
};
const weaknessActionFilters = {
  status: "active",
  priority: "all",
};
const weaknessActionStatusLabels = {
  todo: "待处理",
  in_progress: "处理中",
  needs_more_samples: "待更多样本",
  resolved: "已处理",
  archived: "已归档",
};

function el(id) {
  return document.getElementById(id);
}

const issueController = window.AlphaPilotIssueGuidance?.createController() || null;

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`${url} failed: ${response.status}`);
  return response.json();
}

async function getJsonSafe(url, fallback, timeoutMs = 6000) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { cache: "no-store", signal: controller.signal });
    if (!response.ok) throw new Error(`${url} failed: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.warn(`[AlphaPilot] ${url} fallback`, error);
    return {
      ...fallback,
      loadError: error?.name === "AbortError" ? "timeout" : String(error?.message || error),
      sourceUrl: url,
    };
  } finally {
    window.clearTimeout(timeout);
  }
}

async function loadJsonMap(requests, concurrency = 4) {
  const results = {};
  let cursor = 0;
  const workerCount = Math.max(1, Math.min(concurrency, requests.length));
  async function worker() {
    while (cursor < requests.length) {
      const request = requests[cursor];
      cursor += 1;
      results[request.key] = await getJsonSafe(request.url, request.fallback, request.timeoutMs);
    }
  }
  await Promise.all(Array.from({ length: workerCount }, worker));
  return results;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const responsePayload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const payload = responsePayload || {};
    throw new Error(payload.message || payload.error || `${url} failed: ${response.status}`);
  }
  return responsePayload;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toFixed(digits);
}

function formatPercent(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return `${Number(value).toFixed(digits)}%`;
}

function formatUsd(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return `$${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
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

function setList(elementId, items) {
  const target = el(elementId);
  if (!target) return;
  target.innerHTML = (items || [])
    .filter(Boolean)
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("") || "<li>等待本地报告导入。</li>";
}

function getLearningLoopPayload(loopPayload) {
  return loopPayload?.strategyLearningLoop || loopPayload || {};
}

function getObservationTasksFromLoop(loopPayload) {
  const payload = getLearningLoopPayload(loopPayload);
  const pack = payload.paperObservationTaskPack || {};
  return Array.isArray(pack.paperObservationTasks) ? pack.paperObservationTasks : [];
}

function getBeijingDateKey(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date).reduce((acc, part) => {
    if (part.type !== "literal") acc[part.type] = part.value;
    return acc;
  }, {});
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function flattenStrategyObservationLogs(observationTasks) {
  return (observationTasks || []).flatMap((task) => {
    const recentLogs = Array.isArray(task.recentLogs) ? task.recentLogs : [];
    return recentLogs.map((log) => ({
      ...log,
      taskId: task.taskId || log.artifactId || "",
      taskTitle: task.title || task.candidateId || log.taskLabel || "--",
    }));
  }).sort((a, b) => new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime());
}

function isSignalObservationLog(log) {
  return Boolean(log?.signalObserved) || ["signal_seen", "rule_matched"].includes(log?.logType);
}

function isRuleMatchedLog(log) {
  return Boolean(log?.ruleMatched) || log?.logType === "rule_matched";
}

function buildStrategyObservationDailyReport(observationTasks, qualityRows) {
  const todayKey = getBeijingDateKey(new Date());
  const allLogs = flattenStrategyObservationLogs(observationTasks);
  const todayLogs = allLogs.filter((log) => getBeijingDateKey(log.createdAt) === todayKey);
  const todayTaskIds = new Set(todayLogs.map((log) => log.taskId).filter(Boolean));
  const signalCount = todayLogs.filter(isSignalObservationLog).length;
  const ruleCount = todayLogs.filter(isRuleMatchedLog).length;
  const riskCount = todayLogs.filter((log) => log.logType === "risk_warning").length;
  const invalidatedCount = todayLogs.filter((log) => log.logType === "invalidated").length;
  const strategyRows = (qualityRows && qualityRows.length ? qualityRows : observationTasks).map((row) => {
    const taskId = row.taskId || "";
    const matchingTask = (observationTasks || []).find((task) => task.taskId === taskId) || {};
    const localObservation = matchingTask.localObservation || {};
    return {
      taskId,
      title: row.title || matchingTask.title || row.candidateId || matchingTask.candidateId || "--",
      qualityLabel: row.qualityLabelCn || tObservationQuality(row.qualityLabel) || "等待观察",
      qualityScore: row.qualityScore,
      logCount: row.logCount ?? localObservation.logCount ?? 0,
      ruleMatchedCount: row.ruleMatchedCount ?? localObservation.ruleMatchedCount ?? 0,
      closedPaperSampleCount: row.closedPaperSampleCount ?? localObservation.closedPaperSampleCount ?? 0,
      targetClosedSamples: row.targetClosedSamples ?? matchingTask.observationPlan?.targetClosedSamples,
      remainingClosedSamples: row.remainingClosedSamples,
      riskWarningCount: row.riskWarningCount ?? 0,
      invalidatedCount: row.invalidatedCount ?? 0,
      latestLogAt: row.latestLogAt || localObservation.latestLogAt,
      nextAction: row.nextAction || matchingTask.observationPlan?.nextAction || "继续记录纸面观察，不进入 Dry-run。",
      loggedToday: todayTaskIds.has(taskId),
    };
  });

  let action = "今天还没有观察记录：优先记录无信号日，不要只记录好看的信号。";
  if (invalidatedCount > 0 || riskCount > 0) {
    action = "今天有失效或风险记录：先复盘失效原因，再继续观察。";
  } else if (ruleCount > 0) {
    action = "今天有规则匹配：补充币种、截图、纸面结果 R 和失效条件。";
  } else if (todayLogs.length > 0) {
    action = "今天已有观察日志：继续补齐未记录策略，保持样本口径一致。";
  }

  return {
    todayKey,
    allLogs,
    todayLogs,
    signalCount,
    ruleCount,
    riskCount,
    invalidatedCount,
    coverageText: `${todayTaskIds.size}/${(observationTasks || []).length}`,
    action,
    strategyRows,
  };
}

function renderStrategyObservationDailyReport(observationTasks, qualityRows) {
  if (!el("learningDailyLogCount")) return;
  const report = buildStrategyObservationDailyReport(observationTasks, qualityRows);
  el("learningDailyReportDate").textContent = `${report.todayKey} 北京时间`;
  el("learningDailyLogCount").textContent = String(report.todayLogs.length);
  el("learningDailySignalCount").textContent = String(report.signalCount);
  el("learningDailyRuleCount").textContent = String(report.ruleCount);
  el("learningDailyRiskCount").textContent = String(report.riskCount);
  el("learningDailyInvalidatedCount").textContent = String(report.invalidatedCount);
  el("learningDailyCoverage").textContent = report.coverageText;
  el("learningDailyAction").textContent = report.action;

  el("learningDailyStrategyList").innerHTML = report.strategyRows.slice(0, 8).map((row) => {
    const tone = row.riskWarningCount > 0 || row.invalidatedCount > 0
      ? "danger"
      : row.loggedToday ? "ok" : "warn";
    return `
      <div class="observation-daily-row">
        <div>
          <strong>${escapeHtml(row.title)}</strong>
          <small>${escapeHtml(row.taskId || "--")} · ${escapeHtml(row.qualityLabel)} · ${formatNumber(row.qualityScore, 0)}分</small>
        </div>
        <span class="badge ${tone}">${row.loggedToday ? "今日已记录" : "今日待记录"}</span>
        <div class="artifact-metrics">
          <span>日志 ${row.logCount}</span>
          <span>规则 ${row.ruleMatchedCount}</span>
          <span>闭合 ${row.closedPaperSampleCount}/${row.targetClosedSamples ?? "--"}</span>
          <span>剩余 ${row.remainingClosedSamples ?? "--"}</span>
          <span>最新 ${formatDate(row.latestLogAt)}</span>
        </div>
        <small>下一步：${escapeHtml(row.nextAction)}</small>
      </div>
    `;
  }).join("") || '<div class="observation-daily-empty">暂无策略观察任务。</div>';

  const recentLogs = report.todayLogs.length ? report.todayLogs : report.allLogs.slice(0, 8);
  el("learningDailyRecentLogs").innerHTML = recentLogs.slice(0, 8).map((log) => `
    <div class="observation-daily-row compact">
      <strong>${escapeHtml(log.taskTitle || log.taskId || "--")}</strong>
      <small>${escapeHtml(tPaperLogType(log.logType))} · ${formatDate(log.createdAt)}</small>
      <span>${escapeHtml(log.outcome || log.note || "已记录本地观察")}</span>
    </div>
  `).join("") || '<div class="observation-daily-empty">暂无本地观察日志。今天可以先记录“无信号日”。</div>';
}

const simulationAdmissionThresholds = {
  minQualityScore: 60,
  minLogCount: 10,
  minRuleMatchedCount: 3,
  minClosedPaperSamples: 5,
  maxRiskWarningCount: 1,
  maxInvalidatedCount: 0,
};

function buildSimulationGateRows(observationTasks, qualityRows) {
  return (qualityRows && qualityRows.length ? qualityRows : observationTasks).map((row) => {
    const taskId = row.taskId || "";
    const matchingTask = (observationTasks || []).find((task) => task.taskId === taskId) || {};
    const localObservation = matchingTask.localObservation || {};
    const logCount = Number(row.logCount ?? localObservation.logCount ?? 0);
    const ruleMatchedCount = Number(row.ruleMatchedCount ?? localObservation.ruleMatchedCount ?? 0);
    const closedPaperSampleCount = Number(row.closedPaperSampleCount ?? localObservation.closedPaperSampleCount ?? 0);
    const riskWarningCount = Number(row.riskWarningCount ?? 0);
    const invalidatedCount = Number(row.invalidatedCount ?? 0);
    const qualityScore = Number(row.qualityScore ?? 0);
    const targetClosedSamples = Number(row.targetClosedSamples ?? matchingTask.observationPlan?.targetClosedSamples ?? 0);
    const missing = [];
    const passed = [];

    if (qualityScore >= simulationAdmissionThresholds.minQualityScore) passed.push("质量分达标");
    else missing.push(`质量分还差 ${formatNumber(simulationAdmissionThresholds.minQualityScore - qualityScore, 0)}`);

    if (logCount >= simulationAdmissionThresholds.minLogCount) passed.push("日志数量达标");
    else missing.push(`还需 ${simulationAdmissionThresholds.minLogCount - logCount} 条观察日志`);

    if (ruleMatchedCount >= simulationAdmissionThresholds.minRuleMatchedCount) passed.push("规则匹配达标");
    else missing.push(`还需 ${simulationAdmissionThresholds.minRuleMatchedCount - ruleMatchedCount} 次规则匹配`);

    if (closedPaperSampleCount >= simulationAdmissionThresholds.minClosedPaperSamples) passed.push("闭合样本达标");
    else missing.push(`还需 ${simulationAdmissionThresholds.minClosedPaperSamples - closedPaperSampleCount} 个闭合样本`);

    if (riskWarningCount <= simulationAdmissionThresholds.maxRiskWarningCount) passed.push("风险记录可控");
    else missing.push("风险记录过多，需要先复盘");

    if (invalidatedCount <= simulationAdmissionThresholds.maxInvalidatedCount) passed.push("暂无失效记录");
    else missing.push("存在失效记录，需要暂停复核");

    const gateScore = Math.max(0, Math.min(100,
      (qualityScore * 0.35)
      + (Math.min(logCount / simulationAdmissionThresholds.minLogCount, 1) * 20)
      + (Math.min(ruleMatchedCount / simulationAdmissionThresholds.minRuleMatchedCount, 1) * 15)
      + (Math.min(closedPaperSampleCount / simulationAdmissionThresholds.minClosedPaperSamples, 1) * 20)
      + (riskWarningCount <= simulationAdmissionThresholds.maxRiskWarningCount ? 5 : 0)
      + (invalidatedCount <= simulationAdmissionThresholds.maxInvalidatedCount ? 5 : 0)
    ));

    let status = "continue_observing";
    let statusLabel = "继续观察";
    let tone = "warn";
    if (invalidatedCount > 0 || riskWarningCount > simulationAdmissionThresholds.maxRiskWarningCount) {
      status = "pause_review";
      statusLabel = "暂停复核";
      tone = "danger";
    } else if (missing.length === 0) {
      status = "simulation_review_ready";
      statusLabel = "可升级 testnet 复核";
      tone = "ok";
    }

    const nextAction = status === "simulation_review_ready"
      ? "可以进入 testnet 升级复核；仍不连接交易所、不创建订单。"
      : status === "pause_review"
        ? "先复盘风险或失效记录，暂不进入 testnet 升级复核。"
        : missing[0] || "继续补齐本地观察样本。";

    return {
      taskId,
      title: row.title || matchingTask.title || row.candidateId || matchingTask.candidateId || "--",
      qualityLabel: row.qualityLabelCn || tObservationQuality(row.qualityLabel) || "等待观察",
      qualityScore,
      gateScore,
      status,
      statusLabel,
      tone,
      logCount,
      ruleMatchedCount,
      closedPaperSampleCount,
      targetClosedSamples,
      riskWarningCount,
      invalidatedCount,
      latestLogAt: row.latestLogAt || localObservation.latestLogAt,
      missing,
      passed,
      nextAction,
    };
  }).sort((a, b) => {
    const rank = { simulation_review_ready: 0, continue_observing: 1, pause_review: 2 };
    return (rank[a.status] ?? 9) - (rank[b.status] ?? 9) || b.gateScore - a.gateScore;
  });
}

const sandboxSimulationSettings = {
  virtualCapitalPerStrategy: 1000,
  riskUnitPercent: 1,
};

function renderUsableStrategyCatalog(payload) {
  if (!el("usableStrategyCatalogList")) return;
  const summary = payload?.summary || {};
  const rows = Array.isArray(payload?.strategies) ? payload.strategies : [];
  el("usableStrategyCatalogStatus").textContent = rows.length ? "已整理" : "等待目录";
  el("usableStrategyTotal").textContent = String(summary.totalUsableStrategies ?? rows.length);
  el("usableStrategyLowFrequency").textContent = String(summary.lowFrequencyCount ?? 0);
  el("usableStrategyShortCycle").textContent = String(summary.shortCycleCount ?? 0);
  el("usableStrategySandboxReady").textContent = String(summary.sandboxReadyCount ?? 0);
  el("usableStrategyTargetR").textContent = `${formatNumber(summary.targetR ?? 2, 1)}R`;
  el("usableStrategyCapital").textContent = formatUsd(summary.virtualCapitalPerStrategy ?? sandboxSimulationSettings.virtualCapitalPerStrategy);
  el("usableStrategyCatalogAction").textContent =
    rows.length
      ? `已把 ${rows.length} 条策略整理为本地沙盒观察目录：低频 ${summary.lowFrequencyCount ?? 0} 条，短周期 ${summary.shortCycleCount ?? 0} 条。可用不等于可交易。`
      : "未找到可整理策略，请先确认量化仓库报告存在。";

  el("usableStrategyCatalogList").innerHTML = rows.map((row) => {
    const metrics = row.metrics || {};
    const testMetrics = row.testMetrics || {};
    const pairs = Array.isArray(row.selectedPairs) ? row.selectedPairs : [];
    const tone = row.frequencyBucket === "short_cycle" ? "warn" : "ok";
    return `
      <div class="sandbox-lane-row">
        <div class="sandbox-lane-row-head">
          <div>
            <strong>${escapeHtml(row.name || row.candidateId || row.strategyId || "--")}</strong>
            <small>${escapeHtml(row.frequencyLabel || "--")} · ${escapeHtml(row.timeframe || "--")} · ${escapeHtml(row.direction || "--")} · score ${formatNumber(row.score, 1)}</small>
          </div>
          <span class="badge ${tone}">${escapeHtml(row.approvalTier || "sandbox_ready")}</span>
        </div>
        <div class="artifact-metrics">
          <span>目标 ${formatNumber(row.targetR ?? 2, 1)}R</span>
          <span>样本 ${metrics.tradeCount ?? "--"}</span>
          <span>胜率 ${formatPercent(metrics.winRatePct)}</span>
          <span>PF ${formatNumber(metrics.profitFactor)}</span>
          <span>测试 PF ${formatNumber(testMetrics.profitFactor)}</span>
          <span>回撤 ${formatPercent(metrics.maxDrawdownPctAt1PctRisk ?? metrics.maxDrawdownPct)}</span>
        </div>
        <div class="artifact-metrics">
          <span>家族 ${escapeHtml(row.family || "--")}</span>
          <span>候选币种 ${pairs.length}</span>
          <span>${escapeHtml(pairs.slice(0, 8).join(", ") || "--")}${pairs.length > 8 ? "..." : ""}</span>
        </div>
        <div class="sandbox-lane-next">${escapeHtml(row.nextAction || "继续本地沙盒持续观察。")}</div>
      </div>
    `;
  }).join("") || '<div class="sandbox-lane-empty">暂无可用策略目录。</div>';
}

function buildUsableCatalogObservationTasks(payload) {
  const rows = Array.isArray(payload?.strategies) ? payload.strategies : [];
  return rows.map((row) => ({
    taskId: row.taskId || row.catalogId || row.candidateId || row.strategyId || "",
    strategyId: row.strategyId || row.candidateId || "",
    candidateId: row.candidateId || "",
    title: row.name || row.shortName || row.candidateId || row.strategyId || "--",
    timeframe: row.timeframe || "",
    family: row.family || "",
    historicalMetrics: row.metrics || {},
    frequencyBucket: row.frequencyBucket || "",
    selectedPairs: row.selectedPairs || [],
  })).filter((row) => row.taskId);
}

function parsePaperOutcomeR(value) {
  if (value === null || value === undefined) return null;
  const match = String(value).match(/-?\d+(?:\.\d+)?/);
  if (!match) return null;
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildSandboxSimulationRows(observationTasks, qualityRows) {
  const qualityMap = new Map((qualityRows || []).map((row) => [row.taskId, row]));
  return (observationTasks || []).map((task) => {
    const row = qualityMap.get(task.taskId) || {};
    const localObservation = task.localObservation || {};
    const recentLogs = Array.isArray(task.recentLogs) ? task.recentLogs : [];
    const latestLog = recentLogs[0] || {};
    const parsedRValues = recentLogs
      .map((log) => parsePaperOutcomeR(log.rMultiple ?? log.outcome))
      .filter((value) => value !== null);
    const fallbackR = Number(row.totalR ?? localObservation.totalR ?? 0);
    const realizedR = parsedRValues.length
      ? parsedRValues.reduce((sum, value) => sum + value, 0)
      : (Number.isFinite(fallbackR) ? fallbackR : 0);
    const capital = sandboxSimulationSettings.virtualCapitalPerStrategy;
    const fallbackEquity = Number(row.virtualEquity ?? localObservation.virtualEquity);
    const equity = Number.isFinite(fallbackEquity)
      ? fallbackEquity
      : capital * (1 + ((realizedR * sandboxSimulationSettings.riskUnitPercent) / 100));
    const pnl = equity - capital;
    const closedPaperSampleCount = Number(row.closedPaperSampleCount ?? localObservation.closedPaperSampleCount ?? 0);
    const riskWarningCount = Number(row.riskWarningCount ?? localObservation.riskWarningCount ?? 0);
    const invalidatedCount = Number(row.invalidatedCount ?? localObservation.invalidatedCount ?? 0);
    let status = "waiting_samples";
    let statusLabel = "等待信号样本";
    let tone = "warn";
    if (riskWarningCount > 0 || invalidatedCount > 0) {
      status = "needs_review";
      statusLabel = "需要复盘";
      tone = "danger";
    } else if (Number(localObservation.logCount ?? row.logCount ?? 0) > 0) {
      status = "sandbox_running";
      statusLabel = "沙盒运行中";
      tone = "ok";
    }

    return {
      taskId: task.taskId || row.taskId || "",
      title: task.title || row.title || task.candidateId || row.candidateId || "--",
      status,
      statusLabel,
      tone,
      capital,
      equity,
      pnl,
      realizedR,
      closedPaperSampleCount,
      signalObservedCount: Number(localObservation.signalObservedCount ?? row.signalObservedCount ?? 0),
      ruleMatchedCount: Number(localObservation.ruleMatchedCount ?? row.ruleMatchedCount ?? 0),
      logCount: Number(localObservation.logCount ?? row.logCount ?? 0),
      latestLogAt: row.latestLogAt || localObservation.latestLogAt,
      historicalMetrics: task.historicalMetrics || row.historicalMetrics || {},
      pair: latestLog.pair || task.replayPair || task.pair || "",
      timeframe: latestLog.timeframe || task.timeframe || row.timeframe || "",
      dataStatus: latestLog.dataStatus || "",
      dataMode: latestLog.dataMode || "",
      nextAction: status === "needs_review"
        ? "先记录风险原因和失效条件，再继续沙盒观察。"
        : "继续记录信号、无信号日、规则匹配和虚拟结果 R。",
    };
  });
}

function setText(id, value) {
  const node = el(id);
  if (node) node.textContent = value;
}

const workflowPhaseLabels = {
  manifest_validated: "清单已校验",
  adapter_lock_waiting: "等待同类回测资源",
  adapter_running: "正在执行回测",
  adapter_process_started: "回测进程已启动",
  adapter_report_loaded: "正在核对报告",
  result_persisted: "结果已保存",
};

const workflowFailureLabels = {
  data_snapshot_id_missing: "缺少已注册的数据快照",
  purged_walk_forward_manifest_missing: "缺少防泄漏 Walk-forward 清单",
  locked_oos_manifest_missing: "缺少锁定样本外证据",
  cost_model_missing: "缺少手续费与滑点模型",
  gate_profile_missing: "缺少回测门槛配置",
  target_r_below_2: "目标盈亏比低于 2R",
};

function workflowReadableText(value) {
  const text = String(value || "").trim();
  if (!text) return "--";
  return text.split("; ").map((part) => {
    const exact = workflowFailureLabels[part];
    if (exact) return exact;
    if (part.startsWith("data_snapshot_not_registered:")) return "数据快照尚未注册";
    if (part.startsWith("data_snapshot_not_point_in_time_validated:")) return "数据快照未通过时点校验";
    if (part.startsWith("data_snapshot_not_formal_research_eligible:")) return "数据快照不满足正式研究条件";
    return part;
  }).join("；");
}

function workflowProgressText(item) {
  const progress = item?.progress || {};
  const phase = workflowPhaseLabels[progress.phase] || item?.statusLabel || "等待运行";
  const completed = Number(progress.completedUnits ?? progress.completedShards ?? 0);
  const total = Number(progress.totalUnits ?? progress.totalShards ?? 0);
  return total > 0 ? `${phase} · ${completed}/${total}` : phase;
}

function workflowMetricText(item) {
  const metrics = item?.result?.metrics || {};
  const rows = [];
  if (metrics.tradeCount !== undefined) rows.push(`交易 ${Number(metrics.tradeCount)}`);
  if (metrics.filledSignalCount !== undefined && metrics.tradeCount === undefined) rows.push(`样本 ${Number(metrics.filledSignalCount)}`);
  if (metrics.profitFactor !== undefined) rows.push(`PF ${formatNumber(metrics.profitFactor)}`);
  if (metrics.averageNetR !== undefined) rows.push(`平均 ${formatNumber(metrics.averageNetR)}R`);
  const drawdown = metrics.maximumDrawdownR ?? metrics.maxDrawdownR;
  if (drawdown !== undefined) rows.push(`回撤 ${formatNumber(drawdown)}R`);
  return rows;
}

function workflowCardActions(item) {
  const actions = [];
  if (item.status === "awaiting") actions.push({ action: "run-selected", label: "运行回测", primary: true });
  if (item.status === "queued") actions.push({ action: "cancel", label: "取消排队" });
  if (item.status === "running") {
    actions.push({ action: "pause", label: "暂停" });
    actions.push({ action: "cancel", label: "取消" });
  }
  if (item.status === "paused") actions.push({ action: "run-selected", label: "继续回测", primary: true });
  if (["failed", "blocked"].includes(item.status) && item.failure?.retryDisposition === "same_version_retry") {
    actions.push({ action: "retry", label: "按检查点重试", primary: true });
  }
  if (item.status === "passed") actions.push({ action: "advance", label: "进入本地前向", primary: true });
  if (!["running", "queued"].includes(item.status)) actions.push({ action: "archive", label: "归档" });
  return actions;
}

function renderWorkflowCard(item, archived = false) {
  const metrics = workflowMetricText(item);
  const failure = item.failure || null;
  const failureText = failure ? workflowReadableText(failure.summary) : "";
  const disposition = failure?.retryDisposition === "new_version_required"
    ? "策略表现未通过，必须修改参数或逻辑并创建新版本。"
    : failure?.retryDisposition === "manual_review"
      ? "需要先补齐数据或证据，再创建可回测版本。"
      : failure?.retryDisposition === "same_version_retry"
        ? "运行故障，可用同一版本从检查点重试。"
        : "";
  const actions = archived ? [] : workflowCardActions(item);
  return `
    <article class="workflow-card" data-workflow-run-id="${escapeHtml(item.workflowRunId || "")}">
      <div class="workflow-card-head">
        <div><h5>${escapeHtml(item.displayName || "未命名策略")}</h5><small>第 ${Number(item.attemptNumber || 1)} 次尝试</small></div>
        <span class="badge ${item.status === "passed" ? "ok" : ["failed", "blocked"].includes(item.status) ? "danger" : item.status === "running" ? "warn" : "neutral"}">${escapeHtml(archived ? "已归档" : item.statusLabel || item.status || "--")}</span>
      </div>
      <p class="workflow-progress">${escapeHtml(workflowProgressText(item))}</p>
      ${metrics.length ? `<div class="workflow-metrics">${metrics.map((row) => `<span>${escapeHtml(row)}</span>`).join("")}</div>` : ""}
      ${failureText ? `<div class="workflow-failure"><strong>${escapeHtml(failureText)}</strong><small>${escapeHtml(disposition)}</small></div>` : ""}
      ${actions.length ? `<div class="workflow-actions">${actions.map((action) => `<button type="button" class="${action.primary ? "" : "secondary"}" data-workflow-action="${escapeHtml(action.action)}" data-workflow-run-id="${escapeHtml(item.workflowRunId || "")}" data-strategy-version-id="${escapeHtml(item.strategyVersionId || "")}">${escapeHtml(action.label)}</button>`).join("")}</div>` : ""}
      <details class="workflow-details"><summary>高级详情</summary><div><span>版本 ID</span><code>${escapeHtml(item.strategyVersionId || "--")}</code><span>运行 ID</span><code>${escapeHtml(item.workflowRunId || "--")}</code><span>内容校验</span><code>${escapeHtml(item.contentHash || "--")}</code></div></details>
    </article>
  `;
}

function renderWorkflowLane(targetId, countId, rows, emptyText) {
  const target = el(targetId);
  if (!target) return;
  setText(countId, String(rows.length));
  target.innerHTML = rows.length
    ? rows.map((item) => renderWorkflowCard(item)).join("")
    : `<div class="workflow-empty">${escapeHtml(emptyText)}</div>`;
}

function scheduleWorkflowPoll(items) {
  if (workflowPollTimer) window.clearTimeout(workflowPollTimer);
  const active = (items || []).some((item) => ["queued", "running"].includes(item.status));
  if (!active) return;
  workflowPollTimer = window.setTimeout(() => {
    void refreshWorkflow();
  }, 5000);
}

function renderWorkflowBacktest(payload = emptyWorkflow) {
  latestWorkflowPayload = payload || emptyWorkflow;
  const items = Array.isArray(payload?.items) ? payload.items.filter((item) => item.stage === "backtest") : [];
  const archived = Array.isArray(payload?.archivedItems) ? payload.archivedItems.filter((item) => item.stage === "backtest") : [];
  const awaiting = items.filter((item) => item.status === "awaiting");
  const running = items.filter((item) => ["queued", "running", "paused"].includes(item.status));
  const passed = items.filter((item) => item.status === "passed");
  const failed = items.filter((item) => ["failed", "blocked", "cancelled"].includes(item.status));
  const summary = payload?.summary || {};
  const summaryTarget = el("workflowBacktestSummary");
  if (summaryTarget) {
    const cards = [
      { label: "待回测", value: awaiting.length, meta: "可一键启动真实本地回测" },
      { label: "回测中", value: running.length, meta: "排队、运行或暂停" },
      { label: "已通过", value: passed.length, meta: "等待进入本地前向" },
      { label: "未通过", value: failed.length, meta: "保留原因与改进路径" },
      { label: "已归档", value: archived.length || Number(summary.archivedCount || 0), meta: "默认折叠，不删除证据" },
    ];
    summaryTarget.innerHTML = cards.map((card) => `<div class="lifecycle-summary-card"><span>${escapeHtml(card.label)}</span><strong>${card.value}</strong><small>${escapeHtml(card.meta)}</small></div>`).join("");
  }
  renderWorkflowLane("workflowAwaitingList", "workflowAwaitingCount", awaiting, "没有待回测策略。");
  renderWorkflowLane("workflowRunningList", "workflowRunningCount", running, "当前没有回测任务运行。");
  renderWorkflowLane("workflowPassedList", "workflowPassedCount", passed, "还没有策略通过正式回测门槛。");
  renderWorkflowLane("workflowFailedList", "workflowFailedCount", failed, "当前没有未通过或阻塞记录。");
  setText("workflowArchivedCount", String(archived.length));
  const archiveTarget = el("workflowArchivedList");
  if (archiveTarget) archiveTarget.innerHTML = archived.length ? archived.map((item) => renderWorkflowCard(item, true)).join("") : '<div class="workflow-empty">暂无归档策略。</div>';
  const loadError = payload?.loadError;
  setText("workflowStrategyMeta", loadError
    ? `工作流读取失败：${loadError}`
    : `${items.length} 条策略位于回测阶段；每个版本只显示一次。`);
  setText("simpleConsoleOneLine", loadError
    ? "Quant Engine 工作流暂时不可用，请检查本地服务。"
    : `当前策略工作流：待回测 ${awaiting.length} · 回测中 ${running.length} · 已通过 ${passed.length} · 未通过 ${failed.length}。`);
  scheduleWorkflowPoll(items);
}

async function refreshWorkflow() {
  const payload = await getJsonSafe("/api/workflow?fresh=1", { ...emptyWorkflow, loadError: "无法读取工作流" }, 10000);
  renderDualLayerWorkflow(payload);
  return payload;
}

async function runWorkflowAction(action, item = {}) {
  const status = el("workflowActionStatus");
  if (status) status.textContent = "正在提交工作流动作...";
  try {
    const response = await postJson("/api/workflow/action", {
      action,
      workflowRunId: item.workflowRunId,
      strategyVersionId: item.strategyVersionId,
    });
    renderDualLayerWorkflow(response.workflow || emptyWorkflow);
    if (status) status.textContent = action === "run-all-awaiting"
      ? `已请求 ${Number(response.result?.requestedCount || 0)} 条待回测策略。`
      : "动作已提交，状态会自动刷新。";
  } catch (error) {
    if (status) status.textContent = `操作失败：${error.message}`;
  }
}

const dualLayerPhaseLabels = {
  checking_local_data: "检查本地数据",
  research_smoke_running: "本地研究烟测",
  preparing_official_data: "准备 OKX 官方数据",
  validating_official_data: "校验正式数据",
  freezing_data_snapshot: "冻结正式快照",
  building_validation_manifests: "构建正式验证集",
  formal_backtest_running: "正式回测中",
  evaluating_gate: "评估回测门槛",
  public_forward_observation: "本地前向运行中",
};

const dualLayerStatusLabels = {
  awaiting: "待回测",
  queued: "排队中",
  running: "运行中",
  paused: "已暂停",
  passed: "已通过",
  failed: "未通过",
  blocked: "已阻塞",
  cancelled: "已取消",
  retired: "已归档",
};

const dualLayerFailureLabels = {
  evaluation_binding_missing: "缺少不可变正式评估绑定",
  data_snapshot_id_missing: "缺少正式数据快照",
  purged_walk_forward_manifest_missing: "缺少防泄漏 Walk-forward 验证集",
  locked_oos_manifest_missing: "缺少锁定样本外验证集",
  cost_model_missing: "缺少手续费、滑点与延迟模型",
  gate_profile_missing: "缺少正式回测门槛",
  target_r_below_2: "目标盈亏比低于 2R",
};

function dualLayerReadableFailure(item) {
  const failure = item?.failure || {};
  const raw = String(failure.summary || item?.result?.blocker || "").trim();
  if (!raw) return "--";
  return raw.split("; ").map((part) => {
    if (dualLayerFailureLabels[part]) return dualLayerFailureLabels[part];
    if (part.startsWith("official_collection_not_complete:")) return "OKX 官方数据尚未准备完成，可从断点继续";
    if (part.startsWith("official_collection_partition_failures:")) return "部分官方数据分区校验失败，可补齐后重试";
    if (part.startsWith("dual_layer_worker_error:")) return "本次运行遇到工程故障，可从检查点重试";
    if (part.startsWith("data_snapshot_not_")) return "正式数据快照未满足校验要求";
    return part;
  }).join("；");
}

function dualLayerProgressText(item) {
  const phase = item?.phase || item?.progress?.phase;
  const label = dualLayerPhaseLabels[phase] || item?.phaseLabel || dualLayerStatusLabels[item?.status] || "等待运行";
  const download = item?.downloadProgress || {};
  const completed = Number(download.completed || 0);
  const required = Number(download.required || 0);
  return required > 0 ? `${label} · 数据分区 ${completed}/${required}` : label;
}

function dualLayerProgressModel(item) {
  const status = String(item?.status || "awaiting");
  const phase = item?.phase || item?.progress?.phase;
  const phases = Object.keys(dualLayerPhaseLabels);
  const downloadProgress = item?.downloadProgress || {};
  const workflowProgress = item?.progress || {};
  let completed = Number(downloadProgress.completed ?? workflowProgress.completed ?? 0);
  let required = Number(downloadProgress.required ?? workflowProgress.required ?? 0);
  let percent = Number(workflowProgress.percent);

  if (!Number.isFinite(percent)) {
    percent = required > 0 ? (completed / required) * 100 : 0;
  }
  if (required <= 0 && ["queued", "running", "paused"].includes(status)) {
    const phaseIndex = Math.max(0, phases.indexOf(phase));
    completed = phaseIndex;
    required = Math.max(1, phases.length);
    percent = phaseIndex > 0 ? (phaseIndex / required) * 100 : (status === "queued" ? 4 : 8);
  }
  if (status === "passed") percent = 100;
  if (["awaiting", "cancelled", "retired"].includes(status) && required <= 0) percent = 0;
  if (status === "paused") percent = Math.max(4, percent);

  return {
    status,
    label: dualLayerProgressText(item),
    completed,
    required,
    percent: Math.max(0, Math.min(100, Math.round(percent))),
  };
}

function dualLayerEvidenceText(item) {
  if (item?.evidenceClass === "formal_backtest") return "正式证据：OKX 官方公共数据";
  if (item?.evidenceClass === "research_smoke") return "研究烟测：本地旧数据，不参与晋级";
  return "证据尚未生成";
}

function dualLayerMetricRows(item) {
  const metrics = item?.result?.metrics || {};
  const rows = [];
  if (metrics.tradeCount !== undefined) rows.push(`样本 ${Number(metrics.tradeCount)}`);
  if (metrics.profitFactor !== undefined) rows.push(`PF ${formatNumber(metrics.profitFactor)}`);
  if (metrics.averageNetR !== undefined) rows.push(`平均 ${formatNumber(metrics.averageNetR)}R`);
  const drawdown = metrics.maximumDrawdownR ?? metrics.maxDrawdownR;
  if (drawdown !== undefined) rows.push(`最大回撤 ${formatNumber(drawdown)}R`);
  if (metrics.holdoutTradeCount !== undefined) rows.push(`未见币种 ${Number(metrics.holdoutTradeCount)}`);
  if (metrics.lockedTradeCount !== undefined) rows.push(`锁定样本 ${Number(metrics.lockedTradeCount)}`);
  return rows;
}

function dualLayerCardActions(item) {
  if (item.status === "awaiting") return [{ action: "run-dual-layer", label: "一键双层回测", primary: true }];
  if (item.status === "queued") return [{ action: "cancel", label: "取消排队" }];
  if (item.status === "running") return [
    { action: "pause", label: "暂停" },
    { action: "cancel", label: "取消" },
  ];
  if (item.status === "paused") return [{ action: "run-dual-layer", label: "继续运行", primary: true }];
  if (["failed", "blocked"].includes(item.status)) {
    return [
      {
        action: "rerun",
        label: "重新回测",
        primary: item.failure?.category === "data_integrity" || item.failure?.retryDisposition === "same_version_retry",
      },
      { action: "optimize", label: "改善优化" },
      { action: "archive", label: "归档" },
    ];
  }
  if (!["running", "queued"].includes(item.status)) return [{ action: "archive", label: "归档" }];
  return [];
}

function dualLayerNextStep(item) {
  if (item.status === "passed") return "正式门槛已通过，系统将自动进入本地前向。";
  if (item.status === "failed") return "策略表现未通过。调整参数或逻辑后创建新版本，再重新回测。";
  if (item.status === "blocked") return item.failure?.retryDisposition === "same_version_retry"
    ? "这是数据或工程阻塞，不改策略版本即可从检查点重试。"
    : "先补齐缺失证据，再继续。";
  if (["queued", "running", "paused"].includes(item.status)) return "完成官方数据校验和正式回测后，系统会自动判断下一阶段。";
  return "点击一键双层回测：本地烟测只做实现检查，正式晋级只认 OKX 官方公共数据。";
}

function renderDualLayerCard(item, archived = false) {
  const metrics = dualLayerMetricRows(item);
  const failure = ["failed", "blocked", "cancelled"].includes(item.status) ? dualLayerReadableFailure(item) : "";
  const actions = archived ? [] : dualLayerCardActions(item);
  const dataCoverage = item?.dataCoverage || {};
  const statusLabel = archived ? "已归档" : dualLayerStatusLabels[item.status] || item.status || "--";
  const tone = item.status === "passed" ? "ok" : ["failed", "blocked"].includes(item.status) ? "danger" : item.status === "running" ? "warn" : "neutral";
  const runProgress = dualLayerProgressModel(item);
  const issueKey = archived ? "" : strategyIssueKey(item);
  return `
    <article class="workflow-card" data-workflow-run-id="${escapeHtml(item.workflowRunId || "")}">
      <div class="workflow-card-head">
        <div><h5>${escapeHtml(item.displayName || "未命名策略")}</h5><small>第 ${Number(item.attemptNumber || 1)} 次尝试</small></div>
        <span class="badge ${tone}">${escapeHtml(statusLabel)}</span>
      </div>
      <div class="workflow-run-progress-head"><span>${escapeHtml(runProgress.label)}</span><strong>${runProgress.percent}%</strong></div>
      <div class="workflow-run-progress-track ${escapeHtml(runProgress.status)}"><i style="width:${runProgress.percent}%"></i></div>
      ${runProgress.required > 0 ? `<small class="workflow-run-progress-note">${runProgress.completed}/${runProgress.required} 个可核验步骤</small>` : ""}
      <div class="workflow-evidence-row"><span>${escapeHtml(dualLayerEvidenceText(item))}</span><small>目标 ≥ 2R</small></div>
      ${metrics.length ? `<div class="workflow-metrics">${metrics.map((row) => `<span>${escapeHtml(row)}</span>`).join("")}</div>` : ""}
      ${failure && failure !== "--" ? `<div class="workflow-failure"><strong>${escapeHtml(failure)}</strong></div>` : ""}
      <p class="workflow-next-step">${escapeHtml(dualLayerNextStep(item))}</p>
      ${actions.length || issueKey ? `<div class="workflow-actions">${actions.map((action) => `<button type="button" class="${action.primary ? "" : "secondary"}" data-workflow-action="${escapeHtml(action.action)}" data-workflow-run-id="${escapeHtml(item.workflowRunId || "")}" data-strategy-version-id="${escapeHtml(item.strategyVersionId || "")}">${escapeHtml(action.label)}</button>`).join("")}${issueKey ? `<button type="button" class="secondary" data-issue-guidance-key="${escapeHtml(issueKey)}">查看处理办法</button>` : ""}</div>` : ""}
      <details class="workflow-details"><summary>高级详情</summary><div>
        <span>策略版本 ID</span><code>${escapeHtml(item.strategyVersionId || "--")}</code>
        <span>运行 ID</span><code>${escapeHtml(item.workflowRunId || "--")}</code>
        <span>数据合约</span><code>${escapeHtml(item.strategyDataContractId || dataCoverage.strategyDataContractId || "--")}</code>
        <span>正式快照</span><code>${escapeHtml(dataCoverage.dataSnapshotId || "--")}</code>
        <span>评估绑定</span><code>${escapeHtml(item.evaluationBindingId || "--")}</code>
        <span>内容校验</span><code>${escapeHtml(item.contentHash || "--")}</code>
      </div></details>
    </article>
  `;
}

function renderDualLayerLane(targetId, countId, rows, emptyText) {
  const target = el(targetId);
  if (!target) return;
  setText(countId, String(rows.length));
  target.innerHTML = rows.length
    ? rows.map((item) => renderDualLayerCard(item)).join("")
    : `<div class="workflow-empty">${escapeHtml(emptyText)}</div>`;
}

function renderDualLayerWorkflow(payload = emptyWorkflow) {
  latestWorkflowPayload = payload || emptyWorkflow;
  const items = Array.isArray(payload?.items) ? payload.items.filter((item) => item.stage === "backtest") : [];
  const archived = Array.isArray(payload?.archivedItems) ? payload.archivedItems.filter((item) => item.stage === "backtest") : [];
  const awaiting = items.filter((item) => item.status === "awaiting");
  const running = items.filter((item) => ["queued", "running", "paused"].includes(item.status));
  const passed = items.filter((item) => item.status === "passed");
  const failed = items.filter((item) => ["failed", "blocked", "cancelled"].includes(item.status));
  const summaryTarget = el("workflowBacktestSummary");
  if (summaryTarget) {
    const cards = [
      { label: "待回测", value: awaiting.length, meta: "可启动双层数据回测" },
      { label: "运行中", value: running.length, meta: "下载、校验或正式回测" },
      { label: "正式通过", value: passed.length, meta: "自动进入本地前向" },
      { label: "未通过 / 阻塞", value: failed.length, meta: "显示原因与可操作下一步" },
      { label: "已归档", value: archived.length, meta: "历史证据仍保留" },
    ];
    summaryTarget.innerHTML = cards.map((card) => `<div class="lifecycle-summary-card"><span>${escapeHtml(card.label)}</span><strong>${card.value}</strong><small>${escapeHtml(card.meta)}</small></div>`).join("");
  }
  renderDualLayerLane("workflowAwaitingList", "workflowAwaitingCount", awaiting, "没有待回测策略。");
  renderDualLayerLane("workflowRunningList", "workflowRunningCount", running, "当前没有双层回测任务运行。");
  renderDualLayerLane("workflowPassedList", "workflowPassedCount", passed, "还没有策略通过正式回测门槛。");
  renderDualLayerLane("workflowFailedList", "workflowFailedCount", failed, "当前没有未通过或阻塞记录。");
  setText("workflowArchivedCount", String(archived.length));
  const archiveTarget = el("workflowArchivedList");
  if (archiveTarget) archiveTarget.innerHTML = archived.length
    ? archived.map((item) => renderDualLayerCard(item, true)).join("")
    : '<div class="workflow-empty">暂无归档策略。</div>';
  const loadError = payload?.loadError;
  setText("workflowStrategyMeta", loadError
    ? `工作流读取失败：${loadError}`
    : `${items.length} 条策略位于正式回测阶段；每个不可变版本只显示一次。`);
  setText("simpleConsoleOneLine", loadError
    ? "Quant Engine 工作流暂不可用，请检查本地服务。"
    : `待回测 ${awaiting.length} · 运行中 ${running.length} · 正式通过 ${passed.length} · 未通过或阻塞 ${failed.length}`);
  scheduleWorkflowPoll(items);
  registerPageIssues("simpleConsole", collectStrategyIssues(payload));
}

async function runDualLayerWorkflowAction(action, item = {}) {
  const currentItem = (latestWorkflowPayload?.items || []).find((row) => (
    row.workflowRunId === item.workflowRunId || row.strategyVersionId === item.strategyVersionId
  )) || item;
  if (action === "optimize") {
    openStrategyOptimizationDialog(currentItem);
    return;
  }
  if (action === "rerun") {
    const failure = currentItem.failure || {};
    if (failure.category === "data_integrity" && currentItem.status === "blocked") {
      await runDualLayerWorkflowAction("run-dual-layer", currentItem);
      return;
    }
    if (failure.retryDisposition === "same_version_retry") {
      await runDualLayerWorkflowAction("retry", currentItem);
      return;
    }
    const rerunStatus = el("workflowActionStatus");
    if (rerunStatus) rerunStatus.textContent = "该失败不能原版本重复回测；请先改善参数并创建新版本。";
    openStrategyOptimizationDialog(currentItem);
    return;
  }
  const status = el("workflowActionStatus");
  if (status) status.textContent = action === "run-all-awaiting"
    ? "正在启动全部待回测策略..."
    : "正在提交工作流动作...";
  try {
    const response = await postJson("/api/workflow/action", {
      action,
      workflowRunId: item.workflowRunId,
      strategyVersionId: item.strategyVersionId,
    });
    renderDualLayerWorkflow(response.workflow || emptyWorkflow);
    if (status) status.textContent = action === "run-all-awaiting"
      ? `已请求 ${Number(response.result?.requestedCount || 0)} 条待回测策略。`
      : "动作已提交，阶段状态会自动刷新。";
  } catch (error) {
    if (status) status.textContent = `操作失败：${error.message}`;
  }
}

function closeStrategyOptimizationDialog() {
  const dialog = el("strategyOptimizationDialog");
  activeOptimizationContext = null;
  if (!dialog) return;
  if (typeof dialog.close === "function" && dialog.open) dialog.close();
  else dialog.removeAttribute("open");
}

function optimizationInputMarkup(field, changedByKey) {
  const key = String(field.key || "");
  const current = field.currentValue;
  const proposed = field.proposedValue;
  const change = changedByKey.get(key);
  const locked = Boolean(field.locked);
  const inputType = typeof current === "number" ? "number" : "text";
  const value = typeof current === "boolean" ? String(Boolean(proposed)) : String(proposed ?? "");
  const control = typeof current === "boolean"
    ? `<select data-optimization-param-key="${escapeHtml(key)}" ${locked ? "disabled" : ""}><option value="true" ${proposed ? "selected" : ""}>是</option><option value="false" ${!proposed ? "selected" : ""}>否</option></select>`
    : `<input data-optimization-param-key="${escapeHtml(key)}" type="${inputType}" ${inputType === "number" ? 'step="any"' : ""} value="${escapeHtml(value)}" ${locked ? "disabled" : ""} />`;
  return `
    <label class="strategy-optimization-parameter ${change ? "is-suggested" : ""}">
      <span><strong>${escapeHtml(field.label || key)}</strong><small>当前：${escapeHtml(String(current ?? "--"))}${locked ? " · 固定" : ""}</small></span>
      ${control}
      <em>${escapeHtml(change?.reason || (locked ? "安全边界：目标盈亏比不得低于 2R。" : "可人工调整；保存后必须重新回测。"))}</em>
    </label>
  `;
}

function openStrategyOptimizationDialog(item) {
  const context = item?.optimizationContext || {};
  const dialog = el("strategyOptimizationDialog");
  if (!dialog) return;
  activeOptimizationContext = { item, context };
  setText("strategyOptimizationTitle", `${context.displayName || item?.displayName || "策略"} · 改善优化`);
  setText("strategyOptimizationStage", `当前阶段：${item?.stageLabel || item?.currentStage || item?.stage || "--"}。只调整已有参数，优化版本会回到策略页重新回测。`);
  const nameInput = el("strategyOptimizationName");
  if (nameInput) nameInput.value = `${context.displayName || item?.displayName || "策略"} 优化版`;
  const recommendations = Array.isArray(context.recommendations) ? context.recommendations : [];
  const recommendationTarget = el("strategyOptimizationRecommendations");
  if (recommendationTarget) recommendationTarget.innerHTML = recommendations.length
    ? recommendations.map((row) => `<li>${escapeHtml(row)}</li>`).join("")
    : "<li>暂无自动建议；请按阶段证据人工调整已登记参数。</li>";
  const changedByKey = new Map((context.changedFields || []).map((row) => [String(row.key || ""), row]));
  const fields = Array.isArray(context.parameterFields) ? context.parameterFields : [];
  const fieldTarget = el("strategyOptimizationParameterList");
  if (fieldTarget) fieldTarget.innerHTML = fields.length
    ? fields.map((field) => optimizationInputMarkup(field, changedByKey)).join("")
    : '<div class="workflow-empty">这条遗留策略没有可追溯参数，不能自动优化。请先补齐参数定义。</div>';
  setText("strategyOptimizationStatus", context.recommendationMode === "data_repair"
    ? "当前是数据证据阻塞，推荐先关闭本窗口并点击“重新回测”补齐数据。"
    : "请核对建议值；提交后会创建新版本并立即启动正式回测。");
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function parseOptimizationValue(rawValue, originalValue) {
  if (typeof originalValue === "number") {
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) throw new Error("参数必须是有效数字");
    return parsed;
  }
  if (typeof originalValue === "boolean") return rawValue === "true";
  return rawValue;
}

function collectOptimizationParameters(context) {
  const parameters = { ...(context.baseParameters || context.parameters || {}) };
  el("strategyOptimizationParameterList")?.querySelectorAll("[data-optimization-param-key]").forEach((input) => {
    if (input.disabled) return;
    const key = input.dataset.optimizationParamKey || "";
    parameters[key] = parseOptimizationValue(input.value, parameters[key]);
  });
  return parameters;
}

async function submitStrategyOptimization(event) {
  event.preventDefault();
  if (!activeOptimizationContext) return;
  const { context } = activeOptimizationContext;
  const submit = el("strategyOptimizationSubmitButton");
  const displayName = String(el("strategyOptimizationName")?.value || "").trim();
  if (!displayName) {
    setText("strategyOptimizationStatus", "请输入新版本名称。");
    return;
  }
  submit.disabled = true;
  setText("strategyOptimizationStatus", "正在创建不可变优化版本并启动回测...");
  try {
    const parameters = collectOptimizationParameters(context);
    const action = context.sourceKind === "workflow_version" ? "challenger" : "import-optimized";
    const payload = {
      action,
      displayName,
      definition: context.definition || {},
      baseParameters: context.baseParameters || context.parameters || {},
      parameters,
      startBacktest: true,
    };
    if (action === "challenger") payload.parentStrategyVersionId = context.parentStrategyVersionId;
    else payload.legacyStrategyId = context.legacyStrategyId;
    const response = await postJson("/api/workflow/action", payload);
    renderDualLayerWorkflow(response.workflow || emptyWorkflow);
    closeStrategyOptimizationDialog();
    window.location.hash = "#simpleConsole";
    setText("workflowActionStatus", "优化版本已创建并开始回测；原版本和历史样本保持不变。");
  } catch (error) {
    setText("strategyOptimizationStatus", `优化失败：${error.message}`);
  } finally {
    submit.disabled = false;
  }
}

const lifecycleStageTones = {
  research_candidate: "neutral",
  backtest_passed: "ok",
  local_simulation_running: "warn",
  local_simulation_passed: "ok",
  demo_trial: "warn",
  demo_validation_running: "warn",
  demo_validated: "ok",
  live_candidate: "danger",
};

const lifecycleBlockerLabels = {
  sample_size_below_review_threshold: "样本少于复核起点",
  loss_streak_warning: "连续亏损需要复核",
  concentration_risk: "样本集中度偏高",
  inactive_warning: "近期缺少新样本",
  invalidated_samples_need_review: "存在失效样本待复核",
  risk_warning_needs_review: "存在风险警告待复核",
  live_candidate_missing_demo_release: "缺少可追溯 Demo Release",
};

function lifecycleBlockerLabel(value) {
  return lifecycleBlockerLabels[value] || value || "--";
}

function lifecycleStageCount(summary, stageGroup) {
  return stageGroup.reduce((total, key) => total + Number(summary[key] || 0), 0);
}

function renderLifecycleSummary(targetId, summary = {}) {
  const target = el(targetId);
  if (!target) return;
  const localCount = lifecycleStageCount(summary, ["localSimulationRunningCount", "localSimulationPassedCount"]);
  const demoCount = lifecycleStageCount(summary, ["demoTrialCount", "demoValidationRunningCount", "demoValidatedCount"]);
  const cardsByTarget = {
    strategyLifecycleSummary: [
      { label: "研究待测", value: Number(summary.strategyCandidateCount || 0), meta: "尚未形成回测通过决定" },
      { label: "回测通过", value: Number(summary.backtestPassedCount || 0), meta: "等待进入本地模拟" },
      { label: "已在本地", value: localCount, meta: "只在本地模拟页显示" },
      { label: "已在 Demo", value: demoCount, meta: "只在 Demo 模拟页显示" },
    ],
    localLifecycleSummary: [
      { label: "当前本地模拟", value: Number(summary.localSimulationRunningCount || 0), meta: "本页当前策略" },
      { label: "本地正式通过", value: Number(summary.localSimulationPassedCount || 0), meta: "等待生成正式 Release" },
      { label: "已移入 Demo", value: Number(summary.demoTrialCount || 0), meta: "不在本页重复显示" },
    ],
    demoLifecycleSummary: [
      { label: "Demo 观察", value: Number(summary.demoTrialCount || 0), meta: "已晋级，尚非正式 Release" },
      { label: "正式验证", value: Number(summary.demoValidationRunningCount || 0), meta: "已有不可变 Demo Release" },
      { label: "Demo 通过", value: Number(summary.demoValidatedCount || 0), meta: "等待生成实盘候选包" },
      { label: "实盘候选", value: Number(summary.liveCandidateCount || 0), meta: "只认不可变候选包" },
    ],
    liveLifecycleSummary: [
      { label: "实盘候选", value: Number(summary.liveCandidateCount || 0), meta: "只认不可变候选包" },
      { label: "Demo 通过", value: Number(summary.demoValidatedCount || 0), meta: "尚未生成实盘候选包" },
      { label: "待对账", value: Number(summary.reconciliationRequiredCount || 0), meta: "一致性问题必须先处理" },
    ],
  };
  const cards = cardsByTarget[targetId] || [];
  target.innerHTML = cards.map((card) => `
    <div class="lifecycle-summary-card">
      <span>${escapeHtml(card.label)}</span>
      <strong>${card.value}</strong>
      <small>${escapeHtml(card.meta)}</small>
    </div>
  `).join("");
}

function renderLifecycleCards(targetId, items, allowedStages, emptyText) {
  const target = el(targetId);
  if (!target) return;
  const rows = (Array.isArray(items) ? items : []).filter((item) => allowedStages.includes(item.currentStage));
  target.innerHTML = rows.map((item) => {
    const metrics = item.metrics || {};
    const progress = item.progress || {};
    const progressPercent = Math.max(0, Math.min(100, Number(progress.percent || 0)));
    const blockers = Array.isArray(item.blockers) ? item.blockers.slice(0, 3) : [];
    const history = Array.isArray(item.history) ? item.history : [];
    const stageTone = lifecycleStageTones[item.currentStage] || "neutral";
    const reviewFlag = item.consistencyStatus === "reconciliation_required"
      ? '<span class="badge danger">状态待对账</span>'
      : "";
    const closedSamples = metrics.closedSamples;
    const metricRows = [
      closedSamples !== undefined && closedSamples !== null ? `闭合样本 ${closedSamples}` : "",
      metrics.profitFactor !== undefined && metrics.profitFactor !== null ? `PF ${formatNumber(metrics.profitFactor)}` : "",
      metrics.healthScore !== undefined && metrics.healthScore !== null ? `质量 ${formatNumber(metrics.healthScore, 0)}` : "",
      item.timeframe ? `周期 ${item.timeframe}` : "",
    ].filter(Boolean);
    const optimizationAvailable = [
      "local_simulation_running",
      "local_simulation_passed",
      "demo_trial",
      "demo_validation_running",
      "demo_validated",
    ].includes(item.currentStage);
    const issueKey = lifecycleIssueKey(item);
    return `
      <article class="lifecycle-card">
        <div class="lifecycle-card-head">
          <div>
            <h4>${escapeHtml(item.displayName || item.strategyId || "--")}</h4>
            <small>${escapeHtml(item.strategyId || "--")}</small>
          </div>
          <div class="lifecycle-card-badges">
            <span class="badge ${stageTone}">${escapeHtml(item.stageLabel || item.currentStage || "--")}</span>
            ${reviewFlag}
          </div>
        </div>
        <div class="lifecycle-progress">
          <div><span>当前步骤</span><strong>${escapeHtml(progress.label || "等待阶段任务")}</strong></div>
          <div class="lifecycle-progress-track"><i style="width:${progressPercent}%"></i></div>
          <small>${Number(progress.completed ?? 0)}/${Number(progress.required ?? 0)} · ${escapeHtml(progress.note || "等待可追溯证据。")}</small>
        </div>
        <div class="lifecycle-card-metrics">${metricRows.map((row) => `<span>${escapeHtml(row)}</span>`).join("") || "<span>等待阶段指标</span>"}</div>
        <p>${escapeHtml(item.evidenceSummary || "等待生命周期证据。")}</p>
        ${blockers.length ? `<div class="lifecycle-blockers">${blockers.map((row) => `<span>${escapeHtml(lifecycleBlockerLabel(row))}</span>`).join("")}</div>` : ""}
        <div class="lifecycle-next"><span>下一道门槛</span><strong>${escapeHtml(item.nextGate || "等待正式阶段决定。")}</strong></div>
        ${optimizationAvailable || issueKey ? `<div class="workflow-actions">${optimizationAvailable ? `<button type="button" class="secondary" data-lifecycle-action="optimize" data-strategy-id="${escapeHtml(item.strategyId || "")}">改善优化</button>` : ""}${issueKey ? `<button type="button" class="secondary" data-issue-guidance-key="${escapeHtml(issueKey)}">查看处理办法</button>` : ""}</div>` : ""}
        <small class="lifecycle-history">已保留 ${history.length} 条阶段证据 · 最近 ${formatDate(item.stageEnteredAt)}</small>
      </article>
    `;
  }).join("") || `<div class="lifecycle-empty">${escapeHtml(emptyText)}</div>`;
}

function renderStrategyLifecycle(payload = emptyStrategyLifecycle) {
  latestStrategyLifecyclePayload = payload || emptyStrategyLifecycle;
  const summary = payload?.summary || {};
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const loadFailed = Boolean(payload?.loadError);
  ["strategyLifecycleSummary", "localLifecycleSummary", "demoLifecycleSummary", "liveLifecycleSummary"]
    .forEach((targetId) => renderLifecycleSummary(targetId, summary));

  renderLifecycleCards(
    "strategyLifecycleList",
    items,
    ["research_candidate", "backtest_passed"],
    loadFailed ? "策略生命周期读取失败，请刷新控制台。" : "当前没有停留在候选或回测阶段的策略。",
  );
  renderLifecycleCards(
    "localLifecycleList",
    items,
    ["local_simulation_running", "local_simulation_passed"],
    loadFailed ? "本地模拟状态读取失败，请刷新控制台。" : "当前没有处于本地模拟阶段的策略。",
  );
  renderLifecycleCards(
    "demoLifecycleList",
    items,
    ["demo_trial", "demo_validation_running", "demo_validated"],
    loadFailed ? "Demo 生命周期读取失败，请刷新控制台。" : "暂无进入 Demo 的策略。策略从本地模拟晋级后会移动到这里。",
  );
  renderLifecycleCards(
    "liveLifecycleList",
    items,
    ["live_candidate"],
    loadFailed ? "实盘候选状态读取失败，请刷新控制台。" : "暂无实盘候选。只有完成 Demo 验证并生成 Live Candidate Package 后才会显示。",
  );

  const strategyCount = lifecycleStageCount(summary, ["strategyCandidateCount", "backtestPassedCount"]);
  const localCount = lifecycleStageCount(summary, ["localSimulationRunningCount", "localSimulationPassedCount"]);
  const demoCount = lifecycleStageCount(summary, ["demoTrialCount", "demoValidationRunningCount", "demoValidatedCount"]);
  setText("strategyLifecycleMeta", loadFailed ? "状态读取失败。" : `${strategyCount} 条策略仍在研究或回测阶段。`);
  setText("localLifecycleMeta", loadFailed ? "状态读取失败。" : localCount
    ? `${localCount} 条策略当前处于本地模拟；正式通过 ${summary.localSimulationPassedCount ?? 0} 条。`
    : `当前本地模拟为 0；已有 ${summary.demoTrialCount ?? 0} 条移入 Demo，历史样本仍保留。`);
  setText("demoLifecycleMeta", loadFailed ? "状态读取失败。" : demoCount
    ? `${demoCount} 条策略处于 Demo：观察中 ${summary.demoTrialCount ?? 0} · 正式验证 ${summary.demoValidationRunningCount ?? 0} · 已通过 ${summary.demoValidatedCount ?? 0}。`
    : "当前没有进入 Demo 的策略。");
  setText("liveLifecycleMeta", loadFailed ? "状态读取失败。" : `${summary.liveCandidateCount ?? 0} 条：只认不可变 Live Candidate Package。`);
  setText("strategyArchiveMeta", `默认隐藏 · 研究/失败/重复资产 ${summary.archivedCount ?? 0} 项`);
  const badge = el("simpleConsoleBadge");
  if (badge) {
    badge.className = "status-pill ok";
    badge.textContent = "单一阶段";
  }
  registerPageIssues("localLab", collectLocalIssues(payload));
}

function demoWorkflowValue(value, formatter = null) {
  if (value === null || value === undefined || value === "") return "--";
  return formatter ? formatter(value) : String(value);
}

function demoWorkflowStatusLabel(value) {
  const labels = {
    not_started: "尚未开始",
    prepared: "订单已准备",
    submitted: "订单已提交",
    live: "订单挂单中",
    partially_filled: "部分成交",
    filled: "已成交 / 持仓跟踪",
    canceled: "已取消",
    rejected: "已拒绝",
    unknown: "状态待对账",
    pending: "等待处理",
    completed: "已完成",
    blocked: "已阻塞",
    running: "运行中",
  };
  return labels[value] || translateExchangeDemoStatus(value);
}

function demoWorkflowReasonLabel(value) {
  const labels = {
    immutable_demo_release_missing: "缺少不可变 Demo Release",
    formal_strategy_candidate_not_registered: "尚未登记正式策略候选",
    formal_backtest_evidence_missing: "缺少正式回测证据",
    local_forward_evidence_incomplete: "本地前向闭合样本不足",
    target_r_below_2r: "目标盈亏比低于 2R",
    strategy_definition_incomplete: "策略家族、方向、周期或参数不完整",
    active_demo_risk_profile_missing: "缺少已启用的 OKX Demo 风险配置",
    override_reason_required: "需要填写受控放行原因",
    override_confirmation_mismatch: "受控放行确认语不匹配",
    demo_strategy_not_found: "找不到策略",
    unsupported_demo_workflow_action: "不支持的工作流动作",
  };
  return labels[value] || translateExchangeDemoBlocker(value);
}

function uniqueIssueCodes(values) {
  return [...new Set((Array.isArray(values) ? values : []).filter(Boolean).map(String))].sort();
}

function issueGroupKey(pageId, stage, blockers) {
  const signature = uniqueIssueCodes(blockers).map((value) => encodeURIComponent(value)).join("|") || "unknown";
  return `issue::${pageId}::${stage}::${signature}`;
}

function groupIssueItems(items, keyBuilder) {
  const groups = new Map();
  for (const item of Array.isArray(items) ? items : []) {
    const key = keyBuilder(item);
    if (!key) continue;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  return groups;
}

function currentPrimaryPageId() {
  const raw = (window.location.hash || "#simpleConsole").replace("#", "");
  return hashAliases[raw] || (primaryPageIds.includes(raw) ? raw : "simpleConsole");
}

function registerPageIssues(pageId, issues) {
  if (!issueController) return;
  issueController.replacePageIssues(pageId, issues);
  if (currentPrimaryPageId() === pageId) {
    window.setTimeout(() => issueController.presentHighestPriority(pageId), 0);
  }
}

function isLocalConsoleHost() {
  return ["127.0.0.1", "localhost", "::1", "[::1]"].includes(window.location.hostname);
}

function strategyIssueCodes(item) {
  const failure = item?.failure || {};
  const summaryCodes = String(failure.summary || item?.result?.blocker || "")
    .split("; ")
    .map((value) => value.trim())
    .filter(Boolean);
  return uniqueIssueCodes([failure.category, failure.retryDisposition, ...summaryCodes]);
}

function strategyIssueKey(item) {
  const codes = strategyIssueCodes(item);
  return codes.length ? issueGroupKey("simpleConsole", "formal_backtest", codes) : "";
}

function collectStrategyIssues(payload = emptyWorkflow) {
  const rows = (Array.isArray(payload?.items) ? payload.items : [])
    .filter((item) => item.stage === "backtest" && ["failed", "blocked", "cancelled"].includes(item.status));
  return [...groupIssueItems(rows, strategyIssueKey).entries()].map(([key, group]) => {
    const first = group[0];
    const blockers = strategyIssueCodes(first);
    return {
      key,
      pageId: "simpleConsole",
      stage: "formal_backtest",
      stageLabel: "策略 · 正式回测",
      priority: first.status === "blocked" ? 85 : 75,
      blockers,
      title: group.length > 1 ? `${group.length} 条策略需要回测处理` : `${first.displayName || "策略"} 需要回测处理`,
      summary: dualLayerReadableFailure(first),
      completed: ["不可变策略版本已登记", "失败或阻塞证据已保存", "目标盈亏比仍锁定不低于 2R"],
      nextAction: dualLayerNextStep(first),
      safety: "重新回测只使用研究与公共市场数据；参数变化必须创建新版本。",
      version: group.length > 1 ? "aggregate-1" : (first.strategyVersionId || first.workflowRunId || "1"),
    };
  });
}

function lifecycleIssueCodes(item) {
  return uniqueIssueCodes(item?.blockers || []);
}

function lifecycleIssueKey(item) {
  const codes = lifecycleIssueCodes(item);
  const pageId = String(item?.currentStage || "").startsWith("local_") ? "localLab" : "";
  return pageId && codes.length ? issueGroupKey(pageId, "local_forward", codes) : "";
}

function collectLocalIssues(payload = emptyStrategyLifecycle) {
  const rows = (Array.isArray(payload?.items) ? payload.items : [])
    .filter((item) => String(item.currentStage || "").startsWith("local_") && lifecycleIssueCodes(item).length);
  return [...groupIssueItems(rows, lifecycleIssueKey).entries()].map(([key, group]) => {
    const first = group[0];
    const blockers = lifecycleIssueCodes(first);
    return {
      key,
      pageId: "localLab",
      stage: "local_forward",
      stageLabel: "本地模拟 · 前向证据",
      priority: 70,
      blockers,
      title: group.length > 1 ? `${group.length} 条策略需要前向处理` : `${first.displayName || "策略"} 需要前向处理`,
      summary: blockers.map(lifecycleBlockerLabel).join("；"),
      completed: [first.evidenceSummary || "本地阶段证据已保存", `当前闭合样本 ${Number(first.metrics?.closedSamples || 0)}`],
      nextAction: first.nextGate || first.progress?.note || "继续收集真实时间闭合样本并复核风险记录。",
      safety: "本地前向不会连接交易所或创建订单；策略逻辑变化必须回到正式回测。",
      version: group.length > 1 ? "aggregate-1" : (first.strategyId || "1"),
    };
  });
}

function demoIssueCodes(item) {
  const failure = item?.failure || {};
  const evidenceRows = Array.isArray(item?.evidenceChecklist?.items) ? item.evidenceChecklist.items : [];
  const missingEvidence = evidenceRows
    .filter((row) => row.status === "missing" || (row.evidenceId === "okx_demo_runtime" && !["passed", "bypassed"].includes(row.status)))
    .map((row) => row.evidenceId);
  const actionId = item?.nextAction?.actionId;
  return uniqueIssueCodes([
    ...(Array.isArray(failure.blockers) ? failure.blockers : []),
    failure.reason && failure.reason !== "none" ? failure.reason : "",
    actionId === "start_with_demo_credentials" ? "okx_demo_runtime" : "",
    ...missingEvidence,
  ]);
}

function demoIssueKey(item) {
  const codes = demoIssueCodes(item);
  return codes.length ? issueGroupKey("exchangeDemo", "okx_demo", codes) : "";
}

function collectDemoIssues(payload = { queues: {} }) {
  const queues = payload?.queues || {};
  const rows = [
    ...(Array.isArray(queues.waiting) ? queues.waiting : []),
    ...(Array.isArray(queues.validating) ? queues.validating : []),
  ].filter((item) => demoIssueCodes(item).length);
  return [...groupIssueItems(rows, demoIssueKey).entries()].map(([key, group]) => {
    const first = group[0];
    const blockers = demoIssueCodes(first);
    const runtimeBlocked = blockers.includes("okx_demo_runtime");
    const completed = (Array.isArray(first.processSteps) ? first.processSteps : [])
      .filter((step) => step.status === "completed")
      .map((step) => step.label);
    return {
      key,
      pageId: "exchangeDemo",
      stage: "okx_demo",
      stageLabel: runtimeBlocked ? "Demo 模拟 · 运行前检查" : "Demo 模拟 · 证据闸门",
      priority: runtimeBlocked ? 100 : 80,
      blockers,
      title: runtimeBlocked ? "OKX Demo Runtime 未就绪" : (group.length > 1 ? `${group.length} 条策略等待 Demo 证据` : `${first.displayName || "策略"} 等待 Demo 证据`),
      summary: runtimeBlocked
        ? "凭据、只读、订单、自动化或风险闸门尚未全部通过。"
        : blockers.map(demoWorkflowReasonLabel).join("；"),
      completed,
      nextAction: runtimeBlocked
        ? (isLocalConsoleHost() ? "点击页面顶部“启动 OKX Demo”，在 PowerShell 中一次输入三项 Demo 凭据。" : "请在控制台电脑上打开 http://127.0.0.1:8766，再点击“启动 OKX Demo”。")
        : (first.nextAction?.description || "完成证据清单中的当前缺项后重新验证。"),
      safety: "凭据只进入本次 OKX Demo 进程；全部合格策略共享账户连接，但订单与盈亏按策略隔离。",
      version: group.length > 1 ? "aggregate-1" : (first.release?.demoReleaseId || first.strategyId || "1"),
    };
  });
}

function collectLiveIssues(payload = {}) {
  const blockers = uniqueIssueCodes(payload?.blockers || []);
  if (!blockers.length) return [];
  return [{
    key: issueGroupKey("liveTradingPage", "live_canary", blockers),
    pageId: "liveTradingPage",
    stage: "live_canary",
    stageLabel: "实盘交易 · Canary 安全闸门",
    priority: 90,
    blockers,
    title: "实盘仍处于安全锁定",
    summary: blockers.map(translateLiveCanaryBlocker).join("；"),
    completed: ["Live 适配器状态已审计", "账户级与策略级风险闸门已分离", "Withdraw 权限保持关闭"],
    nextAction: "先完成只读对账和不可变候选复核；账户凭据输入一次，每条策略仍需逐条批准启用。",
    safety: "本问题说明不会启用实盘连接、创建订单或绕过人工策略批准。",
    version: payload?.version || "1",
  }];
}

function renderDemoProcessSteps(steps) {
  return `<div class="demo-process-steps">${(Array.isArray(steps) ? steps : []).map((step, index) => `
    <div class="demo-process-step ${escapeHtml(step.status || "pending")}">
      <span>${index + 1}</span>
      <div><strong>${escapeHtml(step.label || "等待步骤")}</strong><small>${escapeHtml(demoWorkflowStatusLabel(step.status || "pending"))}</small></div>
    </div>
  `).join("")}</div>`;
}

const demoWorkflowActions = {
  updateSettings: { action: "update_demo_strategy_settings" },
  authorizeOverride: { action: "authorize_demo_override" },
};

function demoEvidenceSourceLabel(sourceType) {
  const labels = {
    automatic: "系统自动",
    manual_runtime: "人工操作",
    controlled_override: "受控放行",
  };
  return labels[sourceType] || "待确认";
}

function demoEvidenceStatusLabel(status) {
  const labels = {
    passed: "已满足",
    bypassed: "Demo 受控放行",
    pending: "待处理",
    missing: "缺失",
  };
  return labels[status] || status || "待处理";
}

function renderDemoEvidence(checklist = {}) {
  const rows = Array.isArray(checklist.items) ? checklist.items : [];
  const summary = checklist.summary || {};
  return `
    <details class="demo-evidence-section">
      <summary class="demo-section-head"><strong>证据清单</strong><small>${Number(summary.passedCount || 0)}/${rows.length || 0} 已满足 · ${Number(summary.blockingCount || 0)} 项阻塞</small></summary>
      <div class="demo-evidence-list">
        ${rows.map((row) => `
          <div class="demo-evidence-row ${escapeHtml(row.status || "pending")}">
            <span class="demo-evidence-state">${escapeHtml(demoEvidenceStatusLabel(row.status))}</span>
            <div><strong>${escapeHtml(row.label || "证据")}</strong><small>${escapeHtml(String(row.current ?? "--"))} / ${escapeHtml(String(row.target ?? "--"))}</small></div>
            <em>${escapeHtml(demoEvidenceSourceLabel(row.sourceType))}</em>
            <p>${escapeHtml(row.nextAction || row.detail || "等待系统复核。")}</p>
          </div>
        `).join("") || '<div class="workflow-empty">证据清单尚未生成。</div>'}
      </div>
    </details>
  `;
}

function renderDemoMarketUniverse(universe = {}) {
  const ranked = Array.isArray(universe.rankedCandidates) ? universe.rankedCandidates : [];
  const progress = universe.progress || {};
  const matched = universe.strategyMatchedCount;
  const matchedText = matched === null || matched === undefined ? "待深扫" : String(matched);
  const scanPercent = Math.max(0, Math.min(100, Number(progress.percent || 0)));
  return `
    <section class="demo-market-universe">
      <div class="demo-section-head"><strong>OKX USDT 永续全市场</strong><small>${escapeHtml(universe.matchStatus || "尚未扫描")}</small></div>
      <div class="demo-market-metrics">
        <div><span>市场合约</span><strong>${Number(universe.liveUsdtLinearSwapCount || universe.totalInstrumentCount || 0)}</strong></div>
        <div><span>流动性合格</span><strong>${Number(universe.liquidityEligibleCount || 0)}</strong></div>
        <div><span>深度扫描</span><strong>${Number(universe.deepScreenedCount || 0)}</strong></div>
        <div><span>策略匹配</span><strong>${escapeHtml(matchedText)}</strong></div>
      </div>
      <div class="workflow-run-progress-track ${escapeHtml(progress.status || "awaiting")}"><i style="width:${scanPercent}%"></i></div>
      <div class="demo-market-candidates">
        ${ranked.slice(0, 5).map((row) => `<span>${escapeHtml(row.instId || row.symbol || "--")}${row.score !== undefined ? ` · ${escapeHtml(formatNumber(row.score))}` : ""}</span>`).join("") || "<span>扫描后显示最匹配候选，不固定单一币种。</span>"}
      </div>
    </section>
  `;
}

function renderCompactExecutionPositions(positions, options = {}) {
  const rows = Array.isArray(positions) ? positions.filter(Boolean) : [];
  const title = options.title || "当前持仓";
  const emptyText = options.emptyText || "当前没有持仓；系统会继续扫描全市场。";
  return `
    <section class="compact-execution-positions">
      <div class="demo-section-head"><strong>${escapeHtml(title)}</strong><small>${rows.length} 个持仓</small></div>
      ${rows.length ? `<div class="compact-position-list">${rows.map((row) => `
        <article class="compact-position-row">
          <div><strong>${escapeHtml(row.instrumentId || row.instId || row.symbol || "--")}</strong><small>${escapeHtml(row.side || row.direction || "方向待定")} · ${escapeHtml(demoWorkflowStatusLabel(row.status || "unknown"))}</small></div>
          <div><span>买入 / 开仓价</span><strong>${escapeHtml(demoWorkflowValue(row.entryPrice, (value) => formatNumber(value, 6)))}</strong></div>
          <div><span>现价</span><strong>${escapeHtml(demoWorkflowValue(row.markPrice, (value) => formatNumber(value, 6)))}</strong></div>
          <div><span>浮动盈亏</span><strong class="${Number(row.unrealizedPnl || 0) > 0 ? "positive" : Number(row.unrealizedPnl || 0) < 0 ? "negative" : ""}">${escapeHtml(demoWorkflowValue(row.unrealizedPnl, (value) => formatUsd(value, 2)))}</strong></div>
          <div><span>目标盈利价</span><strong>${escapeHtml(demoWorkflowValue(row.takeProfitPrice, (value) => formatNumber(value, 6)))}</strong></div>
          <div><span>止损价</span><strong>${escapeHtml(demoWorkflowValue(row.stopLossPrice, (value) => formatNumber(value, 6)))}</strong></div>
        </article>
      `).join("")}</div>` : `<div class="workflow-empty">${escapeHtml(emptyText)}</div>`}
    </section>
  `;
}

function renderDemoWorkflowCard(item) {
  const progress = item.progress || {};
  const market = item.market || {};
  const position = item.position || {};
  const positions = Array.isArray(item.positions) && item.positions.length
    ? item.positions
    : (market.instrumentId ? [{ instrumentId: market.instrumentId, ...position, unrealizedPnl: item.performance?.unrealizedPnl }] : []);
  const performance = item.performance || {};
  const failure = item.failure || {};
  const nextAction = item.nextAction || {};
  const evidenceChecklist = item.evidenceChecklist || {};
  const evidenceById = new Map((evidenceChecklist.items || []).map((row) => [row.evidenceId, row]));
  const executionLimits = item.executionLimits || {};
  const requestedSymbolLimit = Math.max(1, Number(executionLimits.requestedMaxConcurrentSymbols || 1));
  const canDemoOverride = !item.release?.formal
    && ["formal_backtest", "target_reward_risk", "strategy_definition"].every((evidenceId) => evidenceById.get(evidenceId)?.status === "passed");
  const percent = Math.max(0, Math.min(100, Number(progress.percent || 0)));
  const pnlTone = Number(performance.realizedPnl || 0) > 0
    ? "positive"
    : Number(performance.realizedPnl || 0) < 0 ? "negative" : "neutral";
  const blockers = Array.isArray(failure.blockers) ? failure.blockers : [];
  const suggestions = Array.isArray(failure.suggestions) ? failure.suggestions : [];
  const canRun = Boolean(nextAction.enabled);
  const retryVisible = failure.status === "failed" && failure.canRetrySameVersion;
  const optimizeVisible = Boolean(failure.canOptimize);
  const issueKey = demoIssueKey(item);
  return `
    <article class="demo-workflow-card" data-demo-strategy-id="${escapeHtml(item.strategyId || "")}">
      <div class="workflow-card-head">
        <div><h5>${escapeHtml(item.displayName || item.strategyId || "--")}</h5><small>${escapeHtml(item.timeframe || "--")} · ${escapeHtml(item.direction || "方向待定")}</small></div>
        <span class="badge ${item.queue === "passed" ? "ok" : item.queue === "validating" ? "warn" : "neutral"}">${escapeHtml(item.queueLabel || "Demo")}</span>
      </div>
      <div class="demo-workflow-progress-head"><span>当前步骤</span><strong>${escapeHtml(progress.label || "等待处理")}</strong><em>${percent}%</em></div>
      <div class="lifecycle-progress-track"><i style="width:${percent}%"></i></div>
      <small class="demo-workflow-progress-note">${Number(progress.completed ?? 0)}/${Number(progress.required ?? 0)} 个流程步骤</small>
      ${renderDemoProcessSteps(item.processSteps)}
      ${renderDemoMarketUniverse(item.marketUniverse || {})}
      <div class="demo-workflow-trade-grid">
        <div><span>当前首选候选</span><strong>${escapeHtml(demoWorkflowValue(market.currentTopCandidate))}</strong></div>
        <div><span>实际持仓币种</span><strong>${escapeHtml(demoWorkflowValue(market.instrumentId))}</strong></div>
        <div><span>持仓状态</span><strong>${escapeHtml(positions.length ? `${positions.length} 个进行中` : demoWorkflowStatusLabel(position.status || "not_started"))}</strong></div>
        <div><span>已实现盈亏</span><strong class="${pnlTone}">${escapeHtml(demoWorkflowValue(performance.realizedPnl, (value) => formatUsd(value, 2)))}</strong></div>
        <div><span>手续费</span><strong>${escapeHtml(demoWorkflowValue(performance.fees, (value) => formatUsd(value, 2)))}</strong></div>
        <div><span>滑点</span><strong>${escapeHtml(demoWorkflowValue(performance.slippage, (value) => formatUsd(value, 2)))}</strong></div>
        <div><span>闭合交易</span><strong>${Number(performance.closedTradeCount || 0)}</strong></div>
      </div>
      <div class="demo-symbol-limit">
        <label>每策略最多同时开仓
          <select data-demo-symbol-limit>
            ${Array.from({ length: 10 }, (_, index) => index + 1).map((value) => `<option value="${value}" ${value === requestedSymbolLimit ? "selected" : ""}>${value} 个币种</option>`).join("")}
          </select>
        </label>
        <button type="button" class="secondary" data-demo-workflow-action="${demoWorkflowActions.updateSettings.action}" data-strategy-id="${escapeHtml(item.strategyId || "")}">保存上限</button>
        <small>当前风险配置最多 ${Number(executionLimits.profileMaxPositionsPerStrategy || 1)} 个；实际生效 ${Number(executionLimits.effectiveConfiguredMaximum || 1)} 个，剩余 ${Number(executionLimits.availableConfiguredSlots || 0)} 个。</small>
      </div>
      ${renderCompactExecutionPositions(positions, { title: "当前 Demo 持仓", emptyText: "尚未开仓；策略会继续扫描全市场并等待真实条件匹配。" })}
      ${renderDemoEvidence(evidenceChecklist)}
      ${failure.status && failure.status !== "none" ? `
        <div class="demo-workflow-failure">
          <span>失败原因 / 当前阻塞</span>
          <strong>${escapeHtml(demoWorkflowReasonLabel(failure.reason))}</strong>
          <p>${escapeHtml(failure.analysis || "等待失败分析。")}</p>
          ${blockers.length ? `<div>${blockers.slice(0, 5).map((row) => `<em>${escapeHtml(demoWorkflowReasonLabel(row))}</em>`).join("")}</div>` : ""}
          <span>改善建议</span>
          <ul>${suggestions.map((row) => `<li>${escapeHtml(row)}</li>`).join("") || "<li>先完成当前步骤，再重新复核。</li>"}</ul>
        </div>
      ` : ""}
      <div class="lifecycle-next"><span>下一步</span><strong>${escapeHtml(nextAction.description || "等待正式阶段决定。")}</strong></div>
      ${nextAction.command ? `<details class="demo-workflow-command"><summary>备用手动启动命令</summary><code>${escapeHtml(nextAction.command)}</code></details>` : ""}
      <div class="workflow-actions">
        ${canRun ? `<button type="button" data-demo-workflow-action="${escapeHtml(nextAction.actionId || "")}" data-strategy-id="${escapeHtml(item.strategyId || "")}">${escapeHtml(nextAction.label || "执行下一步")}</button>` : ""}
        ${canDemoOverride ? `<button type="button" class="secondary" data-demo-workflow-action="open_demo_override" data-strategy-id="${escapeHtml(item.strategyId || "")}">受控放行到 Demo</button>` : ""}
        ${retryVisible ? `<button type="button" class="secondary" data-demo-workflow-action="retry_demo_cycle" data-strategy-id="${escapeHtml(item.strategyId || "")}">重新验证</button>` : ""}
        ${optimizeVisible ? `<button type="button" class="secondary" data-demo-workflow-action="optimize" data-strategy-id="${escapeHtml(item.strategyId || "")}">改善优化</button>` : ""}
        ${issueKey ? `<button type="button" class="secondary" data-issue-guidance-key="${escapeHtml(issueKey)}">查看处理办法</button>` : ""}
      </div>
      <details class="workflow-details"><summary>高级详情</summary><div><span>策略 ID</span><code>${escapeHtml(item.strategyId || "--")}</code><span>Demo Release</span><code>${escapeHtml(item.release?.demoReleaseId || "尚未生成")}</code><span>对账状态</span><code>${escapeHtml(demoWorkflowStatusLabel(item.reconciliation?.status || "not_started"))}</code></div></details>
    </article>
  `;
}

function renderDemoWorkflowLane(targetId, countId, rows, emptyText) {
  const target = el(targetId);
  const count = el(countId);
  const items = Array.isArray(rows) ? rows : [];
  if (count) count.textContent = String(items.length);
  if (target) target.innerHTML = items.length
    ? items.map(renderDemoWorkflowCard).join("")
    : `<div class="workflow-empty">${escapeHtml(emptyText)}</div>`;
}

function renderDemoWorkflow(payload = { summary: {}, queues: {} }) {
  latestDemoWorkflowPayload = payload || { summary: {}, queues: {} };
  const summary = payload?.summary || {};
  const queues = payload?.queues || {};
  setText("demoWorkflowWaitingCount", String(summary.waitingCount ?? 0));
  setText("demoWorkflowValidatingCount", String(summary.validatingCount ?? 0));
  setText("demoWorkflowPassedCount", String(summary.passedCount ?? 0));
  setText("demoWorkflowLiveCandidateCount", String(summary.liveCandidateCount ?? 0));
  renderDemoWorkflowLane("demoWorkflowWaitingList", "demoWorkflowWaitingLaneCount", queues.waiting, "没有等待进入 Demo 的策略。");
  renderDemoWorkflowLane("demoWorkflowValidatingList", "demoWorkflowValidatingLaneCount", queues.validating, "当前没有策略在 OKX Demo 验证中。");
  renderDemoWorkflowLane("demoWorkflowPassedList", "demoWorkflowPassedLaneCount", queues.passed, "还没有策略通过 Demo 模拟。");
  renderDemoWorkflowLane("demoWorkflowLiveCandidateList", "demoWorkflowLiveCandidateLaneCount", queues.liveCandidate, "还没有形成实盘候选包。");
  const waiting = Number(summary.waitingCount || 0);
  const validating = Number(summary.validatingCount || 0);
  setText(
    "demoWorkflowMeta",
    validating
      ? `${validating} 条策略正在 OKX Demo 验证；${waiting} 条等待前置条件。`
      : `${waiting} 条策略待 Demo；当前没有策略在交易所 Demo 下单或持仓。`,
  );
  if (demoWorkflowPollTimer) window.clearTimeout(demoWorkflowPollTimer);
  if (validating > 0) {
    demoWorkflowPollTimer = window.setTimeout(() => {
      if (window.location.hash === "#exchangeDemo") void loadDemoWorkflow(true);
    }, 15000);
  }
  updateDemoRuntimeLauncher(payload);
  registerPageIssues("exchangeDemo", collectDemoIssues(payload));
}

async function loadDemoWorkflow(force = false) {
  if (demoWorkflowLoading && !force) return demoWorkflowLoading;
  demoWorkflowLoading = getJsonSafe(
    `/api/demo-workflow${force ? "?fresh=1" : ""}`,
    { summary: {}, queues: {}, loadError: "无法读取 Demo 工作流" },
    30000,
  ).then((payload) => {
    renderDemoWorkflow(payload);
    return payload;
  }).finally(() => {
    demoWorkflowLoading = null;
  });
  return demoWorkflowLoading;
}

function demoWorkflowRows(payload = { queues: {} }) {
  const queues = payload?.queues || {};
  return ["waiting", "validating", "passed", "liveCandidate"]
    .flatMap((key) => Array.isArray(queues[key]) ? queues[key] : []);
}

function demoRuntimeIsBlocked(payload = { queues: {} }) {
  return demoWorkflowRows(payload).some((item) => demoIssueCodes(item).includes("okx_demo_runtime"));
}

function updateDemoRuntimeLauncher(payload = { queues: {} }) {
  const button = el("demoRuntimeLauncherButton");
  if (!button) return;
  const blocked = demoRuntimeIsBlocked(payload);
  button.hidden = !blocked;
  if (!blocked) {
    button.disabled = false;
    button.title = "OKX Demo Runtime 已就绪或当前策略尚未进入运行前检查。";
    return;
  }
  const local = isLocalConsoleHost();
  button.disabled = demoRuntimeLaunchInProgress || !local;
  button.textContent = demoRuntimeLaunchInProgress ? "等待启动器" : "启动 OKX Demo";
  button.title = local
    ? "一键打开本机安全启动器；三项凭据只输入一次且不会保存。"
    : "请在运行控制台的电脑上打开 127.0.0.1:8766 完成启动。";
  if (!local) {
    setText("demoWorkflowActionStatus", "请在运行控制台的电脑上打开 http://127.0.0.1:8766；手机或局域网页面不能拉起本机进程。");
  }
}

function waitMilliseconds(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function waitForOkxDemoRuntime() {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    await waitMilliseconds(1000);
    const payload = await getJsonSafe(
      "/api/exchange-demo/simulation?fresh=1",
      { summary: {}, evolutionDemo: {}, loadError: "runtime_restarting" },
      2500,
    );
    if (payload.loadError) continue;
    latestExchangeDemoPayload = payload;
    renderExchangeDemoSimulation(payload);
    const summary = payload.summary || {};
    const runtimeGates = payload.evolutionDemo?.runtimeGates || {};
    const credentialsReady = Boolean(summary.credentialsConfigured);
    const privateReady = Boolean(summary.demoPrivateEnabled);
    const orderReady = Boolean(summary.demoOrderEnabled);
    const automationReady = Boolean(runtimeGates.automationEnabled);
    if (credentialsReady && privateReady && orderReady && automationReady) {
      await loadDemoWorkflow(true);
      const riskReady = Boolean(payload.evolutionDemo?.summary?.ready || summary.strategyAutomationReady);
      setText(
        "demoWorkflowActionStatus",
        riskReady
          ? "OKX Demo Runtime 已就绪；全部合格策略共用本次账户连接，订单和盈亏仍按策略分别记录。"
          : "Demo 凭据、只读、订单和自动化进程门已就绪；策略仍会按不可变 Release 与风险闸门逐条复核。",
      );
      return true;
    }
  }
  throw new Error("等待 Demo Runtime 超时。请查看 PowerShell 窗口中的凭据、白名单或端口提示后重试。");
}

async function launchOkxDemoRuntime() {
  const button = el("demoRuntimeLauncherButton");
  if (!isLocalConsoleHost()) {
    setText("demoWorkflowActionStatus", "请在控制台电脑上打开 http://127.0.0.1:8766，再点击“启动 OKX Demo”。");
    return;
  }
  if (demoRuntimeLaunchInProgress) return;
  demoRuntimeLaunchInProgress = true;
  if (button) button.disabled = true;
  setText("demoWorkflowActionStatus", "Demo 凭据每次运行只输入一次，全部合格策略共用；正在打开本机安全启动器，网页不会读取或保存 API Key。");
  try {
    const response = await postJson("/api/local-control/open-okx-demo-launcher", {});
    setText("demoWorkflowActionStatus", response.message || "启动器已打开，请在 PowerShell 窗口输入三项 Demo 凭据。");
    await waitForOkxDemoRuntime();
  } catch (error) {
    setText("demoWorkflowActionStatus", `启动未完成：${error.message}`);
  } finally {
    demoRuntimeLaunchInProgress = false;
    updateDemoRuntimeLauncher(latestDemoWorkflowPayload);
  }
}

function openDemoOverrideDialog(strategyId) {
  activeDemoOverrideStrategyId = strategyId;
  const dialog = el("demoOverrideDialog");
  if (!dialog) return;
  if (el("demoOverrideReason")) el("demoOverrideReason").value = "";
  if (el("demoOverrideConfirmation")) el("demoOverrideConfirmation").value = "";
  setText("demoOverrideStatus", "该权限只绕过本地前向样本门槛，正式回测、2R 和完整策略定义仍必须通过。");
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function closeDemoOverrideDialog() {
  const dialog = el("demoOverrideDialog");
  activeDemoOverrideStrategyId = null;
  if (!dialog) return;
  if (typeof dialog.close === "function" && dialog.open) dialog.close();
  else dialog.removeAttribute("open");
}

async function submitDemoOverride(event) {
  event.preventDefault();
  if (!activeDemoOverrideStrategyId) return;
  const reason = String(el("demoOverrideReason")?.value || "").trim();
  const confirmation = String(el("demoOverrideConfirmation")?.value || "").trim();
  if (!reason || confirmation !== "仅放行到OKX DEMO") {
    setText("demoOverrideStatus", "请填写放行原因，并完整输入确认语：仅放行到OKX DEMO");
    return;
  }
  const submitButton = el("demoOverrideSubmitButton");
  if (submitButton) submitButton.disabled = true;
  try {
    await runDemoWorkflowAction(
      demoWorkflowActions.authorizeOverride.action,
      activeDemoOverrideStrategyId,
      { reason, confirmation },
    );
    closeDemoOverrideDialog();
  } finally {
    if (submitButton) submitButton.disabled = false;
  }
}

async function runDemoWorkflowAction(action, strategyId, extra = {}) {
  if (action === "optimize") {
    const item = (latestStrategyLifecyclePayload?.items || []).find((row) => row.strategyId === strategyId);
    if (item) openStrategyOptimizationDialog(item);
    return;
  }
  setText("demoWorkflowActionStatus", "正在执行当前合法步骤，请稍候。");
  try {
    const response = await postJson("/api/demo-workflow/action", { action, strategyId, ...extra });
    renderDemoWorkflow(response.workflow || { summary: {}, queues: {} });
    const blockers = Array.isArray(response.blockers) ? response.blockers : [];
    setText(
      "demoWorkflowActionStatus",
      response.ok
        ? (response.message || "当前步骤已完成。")
        : `${response.message || "当前步骤被阻塞。"}${blockers.length ? ` 缺项：${blockers.map(demoWorkflowReasonLabel).join("；")}` : ""}`,
    );
    const exchangeDemo = await getJsonSafe("/api/exchange-demo/simulation?fresh=1", latestExchangeDemoPayload || {}, 12000);
    renderExchangeDemoSimulation(exchangeDemo);
  } catch (error) {
    setText("demoWorkflowActionStatus", `操作失败：${error.message}`);
  }
}

function getSimpleRunnerState(payload) {
  const runner = payload?.autoRunner || {};
  const enabled = Boolean(runner.enabled);
  return {
    enabled,
    status: runner.status || (enabled ? "enabled" : "disabled"),
    intervalMinutes: runner.intervalMinutes ?? 5,
    maxRunsPerDay: runner.maxRunsPerDay ?? 288,
    todayRunCount: runner.todayRunCount ?? 0,
    lastRunAt: runner.lastRunAt || null,
    nextRunAt: runner.nextRunAt || null,
  };
}

function updateSimpleSandboxButton(runnerState) {
  const button = el("simpleRunSandboxButton");
  if (!button) return;
  button.classList.toggle("is-running", Boolean(runnerState.enabled));
  button.dataset.running = runnerState.enabled ? "true" : "false";
  button.textContent = runnerState.enabled ? "沙盒运行中 · 点击停止" : "启动本地沙盒";
  button.title = runnerState.enabled
    ? "本地沙盒正在持续观察。点击后会停止自动观察。"
    : "点击后会开启本地沙盒，并立即运行一轮本地观察。";
}

function renderSimpleStrategyCards(rows) {
  const container = el("simpleStrategyCards");
  if (!container) return;
  const topRows = rows.slice(0, 5);
  container.innerHTML = topRows.map((row, index) => {
    const metrics = row.metrics || {};
    const testMetrics = row.testMetrics || {};
    const pairs = Array.isArray(row.selectedPairs) ? row.selectedPairs : [];
    const bucketLabel = row.frequencyBucket === "short_cycle" ? "短周期" : "低频";
    const badgeTone = row.frequencyBucket === "short_cycle" ? "warn" : "ok";
    return `
      <div class="simple-strategy-card">
        <div class="simple-strategy-card-head">
          <div>
            <small>候选 ${index + 1} · ${escapeHtml(row.timeframe || "--")}</small>
            <strong>${escapeHtml(row.name || row.shortName || row.strategyId || row.candidateId || "--")}</strong>
          </div>
          <span class="badge ${badgeTone}">${escapeHtml(bucketLabel)}</span>
        </div>
        <div class="simple-strategy-metrics">
          <span>目标 ${formatNumber(row.targetR ?? 2, 1)}R</span>
          <span>样本 ${metrics.tradeCount ?? "--"}</span>
          <span>胜率 ${formatPercent(metrics.winRatePct)}</span>
          <span>PF ${formatNumber(metrics.profitFactor)}</span>
          <span>测试PF ${formatNumber(testMetrics.profitFactor)}</span>
          <span>币种 ${pairs.length || "--"}</span>
        </div>
        <small>${escapeHtml(row.nextAction || "继续本地沙盒观察，不触发真实交易。")}</small>
      </div>
    `;
  }).join("") || '<div class="simple-action-item">还没有可观察策略。请先导入量化报告。</div>';
}

function renderSimpleActionChecklist({ runnerState, rows, sandboxRows, dailySummary }) {
  const container = el("simpleActionChecklist");
  if (!container) return;
  const closedSamples = sandboxRows.reduce((sum, row) => sum + Number(row.closedPaperSampleCount || 0), 0);
  const riskReviewCount = sandboxRows.filter((row) => row.status === "needs_review").length;
  const items = [
    {
      title: runnerState.enabled ? "沙盒正在跑" : "先启动沙盒",
      body: runnerState.enabled
        ? `保持控制台打开即可；系统每 ${runnerState.intervalMinutes} 分钟检查一次，本日 ${runnerState.todayRunCount}/${runnerState.maxRunsPerDay}。`
        : "点击左侧黄色按钮，让 10 条候选策略进入本地虚拟观察。",
    },
    {
      title: "今天重点看样本",
      body: `当前闭合样本 ${closedSamples} 个，今日新增 ${dailySummary.dailyClosedSampleCount ?? 0} 个；样本不足时先不要升级。`,
    },
    {
      title: riskReviewCount ? "先处理风险策略" : "风险队列正常",
      body: riskReviewCount
        ? `${riskReviewCount} 条策略需要复盘风险或失效原因。`
        : "暂未发现需要优先处理的沙盒风险策略。",
    },
    {
      title: "安全边界",
      body: "当前只是本地控制台，不接 API Key、不下单、不读取真实账户。",
    },
  ];
  container.innerHTML = items.map((item) => `
    <div class="simple-action-item">
      <strong>${escapeHtml(item.title)}</strong>
      <small>${escapeHtml(item.body)}</small>
    </div>
  `).join("");
}

function renderSimpleSimulationBridge(payload) {
  const summary = payload?.summary || {};
  const learning = payload?.learningStatus || {};
  setText("simpleSimulationStage", summary.stageLabel || "--");
  setText("simpleSimulationNext", summary.nextAction || "等待本地模拟盘桥接状态。");
  setText("simpleSimulationCandidates", String(summary.simulationReviewCandidateCount ?? 0));
  setText(
    "simpleSimulationSamples",
    `闭合样本 ${summary.totalClosedSampleCount ?? 0} · 权益 ${formatUsd(summary.totalVirtualEquity)} / ${formatUsd(summary.totalVirtualCapital)}`,
  );
  setText("simpleLearningStage", learning.statusLabel || "--");
  setText(
    "simpleLearningSamples",
    `学习样本 ${learning.closedSampleCount ?? 0}/${learning.minimumBaselineSamples ?? "--"} · ${learning.nextAction || "继续收集样本"}`,
  );
}

function reviewTone(status, warnings = []) {
  if (status === "promoted_candidate") return "ok";
  if (status === "demoted" || status === "paused" || warnings.includes("demotion_review")) return "danger";
  if (status === "under_review" || status === "watchlist") return "warn";
  return "neutral";
}

function renderSimpleReviewQueue(payload) {
  const summary = payload?.summary || {};
  const rows = Array.isArray(payload?.queue) ? payload.queue : [];
  setText("simpleReviewCollecting", String(summary.collectingStrategies ?? 0));
  setText("simpleReviewReady", String(summary.reviewReadyStrategies ?? 0));
  setText("simpleReviewPromoted", String(summary.promotedCandidates ?? 0));
  setText("simpleReviewDemoted", String(summary.demotedStrategies ?? 0));
  setText(
    "simpleReviewQueueMeta",
    `总闭合样本 ${summary.totalClosedSamples ?? 0} · 复核门槛 ${summary.reviewMinimumClosedSamples ?? 30} / Dry-run 门槛 ${summary.dryRunMinimumClosedSamples ?? 100}`,
  );
  const target = el("simpleReviewQueueList");
  if (!target) return;
  target.innerHTML = rows.slice(0, 3).map((row) => {
    const metrics = row.metrics || {};
    const tone = reviewTone(row.status, row.warnings || []);
    return `
      <div class="simple-review-row">
        <div>
          <strong>${escapeHtml(row.strategyName || row.taskId || "--")}</strong>
          <small>${escapeHtml(row.timeframe || "--")} · ${escapeHtml(simulationReviewStatusLabels[row.status] || row.status || "--")}</small>
        </div>
        <span class="badge ${tone}">${escapeHtml(simulationReviewActionLabels[row.recommendedAction] || row.recommendedAction || "继续观察")}</span>
        <div class="artifact-metrics">
          <span>闭合 ${metrics.closedSamples ?? 0}/${row.sampleGate?.reviewMinimum ?? 30}</span>
          <span>胜率 ${formatPercent(metrics.winRate)}</span>
          <span>PF ${formatNumber(metrics.profitFactor)}</span>
          <span>回撤 ${formatNumber(metrics.maxDrawdownR, 2)}R</span>
        </div>
      </div>
    `;
  }).join("") || '<div class="simple-review-empty">暂无策略复核样本。保持本地沙盒运行。</div>';
}

function qualityTone(status) {
  if (status === "testnet_prep_candidate" || status === "continue_observing") return "ok";
  if (status === "pause_for_risk_review" || status === "pause_observation") return "danger";
  return "warn";
}

function renderQualityStrategyDetail(row, readonlyPrep = {}, concentrationReview = {}, resultReview = {}) {
  const target = el("qualityStrategyDetail");
  if (!target) return;
  if (!row) {
    target.innerHTML = `
      <strong>暂无策略详情</strong>
      <small>先运行本地沙盒，生成闭合样本后再查看。</small>
    `;
    return;
  }
  const latest = row.latestTrigger || {};
  const warnings = Array.isArray(row.warnings) ? row.warnings : [];
  const bullets = Array.isArray(row.detailBullets) ? row.detailBullets : [];
  const concentrationRows = Array.isArray(concentrationReview?.strategies) ? concentrationReview.strategies : [];
  const concentrationRow = concentrationRows.find((item) => item.taskId === row.taskId);
  const concentrationReasons = Array.isArray(concentrationRow?.reviewReasons) ? concentrationRow.reviewReasons : [];
  const pairBreakdown = Array.isArray(concentrationRow?.pairBreakdown) ? concentrationRow.pairBreakdown : [];
  const topPair = pairBreakdown[0] || {};
  const resultRows = Array.isArray(resultReview?.strategies) ? resultReview.strategies : [];
  const resultRow = resultRows.find((item) => item.taskId === row.taskId);
  const resultReasons = Array.isArray(resultRow?.resultReviewReasons) ? resultRow.resultReviewReasons : [];
  const resultQuality = resultRow?.resultQuality || {};
  target.innerHTML = `
    <div class="quality-detail-head">
      <div>
        <strong>${escapeHtml(row.strategyName || row.taskId || "--")}</strong>
        <small>${escapeHtml(row.taskId || "--")} · ${escapeHtml(row.timeframe || "--")}</small>
      </div>
      <span class="badge ${qualityTone(row.promotionStatus)}">${escapeHtml(row.promotionLabel || "--")}</span>
    </div>
    <div class="quality-detail-grid">
      <div>
        <span>这是什么策略</span>
        <strong>${escapeHtml(row.strategyName || "--")}</strong>
        <small>只用于本地沙盘观察，不是交易指令。</small>
      </div>
      <div>
        <span>最近为什么触发</span>
        <strong>${escapeHtml(latest.latestPair || "--")} · ${escapeHtml(latest.latestTimeframe || row.timeframe || "--")}</strong>
        <small>${escapeHtml(latest.latestReason || "暂无触发说明")} · ${escapeHtml(latest.latestReplayWindowId || "无 replay 窗口")}</small>
      </div>
      <div>
        <span>样本表现</span>
        <strong>${row.closedSamples ?? 0}/${row.reviewMinimum ?? 30} 闭合</strong>
        <small>胜率 ${formatPercent(row.winRate)} · PF ${formatNumber(row.profitFactor)} · 总R ${formatNumber(row.totalR, 2)}</small>
      </div>
      <div>
        <span>最大风险</span>
        <strong>连亏 ${row.maxConsecutiveLosses ?? 0} · 回撤 ${formatNumber(row.maxDrawdownR, 2)}R</strong>
        <small>风险 ${row.riskWarningCount ?? 0} · 失效 ${row.invalidatedCount ?? 0} · 数据缺口 ${row.dataGapCount ?? 0}</small>
      </div>
    </div>
    <div class="quality-detail-bullets">
      ${(bullets.length ? bullets : ["继续收集闭合样本"]).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
      ${(warnings.length ? warnings : ["暂无阻塞警告"]).slice(0, 4).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
    </div>
    ${concentrationRow ? `
      <div class="quality-detail-action">
        <strong>集中度复核：${escapeHtml(concentrationRow.decisionLabel || "继续观察")}</strong>
        <small>覆盖币种 ${concentrationRow.uniquePairCount ?? 0} 个；最高集中 ${escapeHtml(topPair.pair || "--")} · ${formatPercent((topPair.sampleShare ?? 0) * 100)}；回放窗口 ${concentrationRow.uniqueReplayWindowCount ?? 0} 个。</small>
        ${concentrationReasons.slice(0, 3).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
      </div>
    ` : ""}
    ${resultRow ? `
      <div class="quality-detail-action">
        <strong>结果质量复核：${escapeHtml(resultRow.resultDecisionLabel || "--")} · ${escapeHtml(resultQuality.grade || "--")}级 · ${formatNumber(resultQuality.totalScore, 1)}分</strong>
        <small>策略族：${escapeHtml(resultRow.familyName || "--")}；代表变体用于下一轮，重复变体只保留为对照样本。</small>
        ${resultReasons.slice(0, 3).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
      </div>
    ` : ""}
    <div class="quality-detail-action">
      <strong>${escapeHtml(row.nextAction || "继续本地沙盘观察。")}</strong>
      <small>${escapeHtml(readonlyPrep.nextAction || "只读准备阶段：不接 API Key、不连接私有交易接口、不创建订单。")}</small>
    </div>
  `;
}

function renderQualityCenter(payload, concentrationReview = {}, resultReview = {}) {
  latestQualityCenterPayload = payload || {};
  latestConcentrationReviewPayload = concentrationReview || {};
  latestResultReviewPayload = resultReview || {};
  if (!el("simpleQualityCenter")) return;
  const summary = payload?.summary || {};
  const concentrationSummary = concentrationReview?.summary || {};
  const resultSummary = resultReview?.summary || {};
  const rows = Array.isArray(payload?.strategies) ? payload.strategies : [];
  const readonlyPrep = payload?.readonlyPreparation || {};
  setText(
    "qualityCenterMeta",
    `共 ${summary.strategyCount ?? rows.length} 条策略 · replay ${summary.replayCursor ?? "--"} · ${summary.nextAction || "继续沙盘观察"}`,
  );
  if (concentrationSummary.strategyCount !== undefined) {
    setText(
      "qualityCenterMeta",
      `共 ${summary.strategyCount ?? rows.length} 条策略 · 集中复核 ${concentrationSummary.reviewReadyCount ?? 0} 条达标 / ${concentrationSummary.needsConcentrationExpansionCount ?? 0} 条需扩币种 · ${concentrationSummary.nextAction || "继续沙盘观察"}`,
    );
  }
  if (resultSummary.strategyCount !== undefined) {
    setText(
      "qualityCenterMeta",
      `共 ${summary.strategyCount ?? rows.length} 条策略 · 代表 ${resultSummary.representativeCount ?? 0} 条 / 合并 ${resultSummary.mergeCandidateCount ?? 0} 条 · ${resultSummary.nextAction || "继续结果质量复核"}`,
    );
  }
  setText("qualityClosedSamples", String(summary.totalClosedSamples ?? 0));
  setText("qualityAverageScore", summary.averageQualityScore !== undefined ? formatNumber(summary.averageQualityScore, 1) : "--");
  setText("qualityContinueCount", String(summary.candidateContinueCount ?? 0));
  setText("qualityTestnetPrepCount", String(summary.testnetPrepCandidateCount ?? 0));
  setText("qualityInsufficientCount", String(summary.insufficientSampleCount ?? 0));
  setText("qualityDataGapCount", String(summary.totalDataGapCount ?? 0));
  setText("qualityRunnerStatus", summary.sandboxRunning ? "运行中" : "已暂停");
  setText(
    "qualityRunnerMeta",
    `最近新增 ${summary.lastRunGenerated ?? "--"} · 闭合 ${summary.lastRunClosed ?? "--"} · 重复 ${summary.lastRunDuplicates ?? "--"} · 下次 ${formatDate(summary.nextRunAt)}`,
  );
  setText("qualityReadonlyStage", readonlyPrep.stageLabel || "--");
  setText(
    "qualityReadonlyMeta",
    readonlyPrep.publicProbeReady
      ? `${readonlyPrep.testnetReadinessStage || "阻塞中"} · public probe 已有`
      : `${readonlyPrep.testnetReadinessStage || "阻塞中"} · public probe 待复核`,
  );

  if (!selectedQualityCenterTaskId || !rows.some((row) => row.taskId === selectedQualityCenterTaskId)) {
    selectedQualityCenterTaskId = rows[0]?.taskId || null;
  }

  const list = el("qualityStrategyList");
  if (list) {
    list.innerHTML = rows.slice(0, 8).map((row) => {
      const selected = row.taskId === selectedQualityCenterTaskId ? " selected" : "";
      const tone = qualityTone(row.promotionStatus);
      return `
        <button class="quality-strategy-row${selected}" data-quality-task-id="${escapeHtml(row.taskId || "")}" type="button">
          <span>
            <strong>${escapeHtml(row.strategyName || row.taskId || "--")}</strong>
            <small>${escapeHtml(row.timeframe || "--")} · ${escapeHtml(row.promotionLabel || "--")}</small>
          </span>
          <em class="${tone}">${row.closedSamples ?? 0}/${row.reviewMinimum ?? 30}</em>
          <small>胜率 ${formatPercent(row.winRate)} · PF ${formatNumber(row.profitFactor)} · 质量 ${formatNumber(row.qualityScore, 1)}</small>
        </button>
      `;
    }).join("") || '<div class="simple-review-empty">暂无沙盘质量策略。先运行本地沙盒。</div>';
    list.querySelectorAll("[data-quality-task-id]").forEach((button) => {
      button.addEventListener("click", () => {
        selectedQualityCenterTaskId = button.getAttribute("data-quality-task-id");
        renderQualityCenter(latestQualityCenterPayload, latestConcentrationReviewPayload, latestResultReviewPayload);
      });
    });
  }

  const selected = rows.find((row) => row.taskId === selectedQualityCenterTaskId) || rows[0];
  renderQualityStrategyDetail(selected, readonlyPrep, concentrationReview, resultReview);
}

function renderStrategyAssetPlaybook(payload) {
  latestStrategyAssetPlaybookPayload = payload || {};
  if (!el("strategyAssetPlaybook")) return;
  const summary = payload?.summary || {};
  const readiness = payload?.executionReadiness || {};
  const rows = Array.isArray(payload?.strategies) ? payload.strategies : [];
  setText(
    "strategyAssetMeta",
    summary.nextAction || "策略资产手册只用于本地研究，不连接交易所，不创建订单。",
  );
  setText("strategyAssetCount", String(summary.strategyCount ?? rows.length));
  setText("strategyAssetClosedSamples", String(summary.totalClosedSamples ?? 0));
  setText("strategyAssetSandboxCandidates", String(summary.sandboxReviewCandidateCount ?? 0));
  setText("strategyAssetTestnetCandidates", String(summary.testnetReadinessCandidateCount ?? summary.testnetPrepCandidateCount ?? 0));
  setText("strategyAssetExecutionGate", summary.blockedFromExecution === false ? "异常开启" : "关闭");
  setText("strategyAssetBlockers", String(summary.testnetBlockerCount ?? (readiness.blockers || []).length ?? 0));
  const target = el("strategyAssetList");
  if (!target) return;
  target.innerHTML = rows.slice(0, 6).map((row, index) => {
    const evidence = row.evidence || {};
    const gate = row.gate || {};
    const tone = gate.canEnterTestnetReadiness ? "ok" : qualityTone(gate.status);
    const blockers = Array.isArray(gate.testnetBlockers) ? gate.testnetBlockers : [];
    const rules = Array.isArray(row.coreRules) ? row.coreRules.slice(0, 2) : [];
    return `
      <div class="strategy-asset-card${index === 0 ? " primary" : ""}">
        <div class="strategy-asset-card-head">
          <div>
            <strong>${escapeHtml(row.plainName || row.readableName || "--")}</strong>
            <small>${escapeHtml(row.readableName || row.taskId || "--")} · ${escapeHtml(row.timeframe || "--")} · ${escapeHtml(row.directionLabel || "研究样本")}</small>
          </div>
          <span class="badge ${tone}">${escapeHtml(gate.label || gate.status || "继续观察")}</span>
        </div>
        <span>${escapeHtml(row.oneLine || "继续本地沙盒观察，补足可复盘样本。")}</span>
        <div class="strategy-asset-metrics">
          <div><span>样本</span><strong>${evidence.closedSamples ?? 0}</strong></div>
          <div><span>胜率</span><strong>${formatPercent(evidence.winRate)}</strong></div>
          <div><span>PF</span><strong>${formatNumber(evidence.profitFactor)}</strong></div>
          <div><span>累计R</span><strong>${formatNumber(evidence.totalR, 1)}</strong></div>
        </div>
        <small>${rules.map((item) => escapeHtml(item)).join(" / ") || "规则说明待补充"}</small>
        <div class="strategy-asset-next">
          <strong>下一步</strong>
          <small>${escapeHtml(row.nextAction || "继续本地沙盒观察。")}</small>
        </div>
        <small>Testnet 阻塞：${escapeHtml(blockers.slice(0, 2).join(" / ") || "仍需安全设计复核")}。不接 API Key，不创建订单。</small>
      </div>
    `;
  }).join("") || '<div class="simple-review-empty">暂无策略资产手册。请先运行本地沙盒质量中心。</div>';
}

function renderTestnetDrill(payload) {
  latestTestnetDrillPayload = payload || {};
  if (!el("testnetDrillPanel")) return;
  const summary = payload?.summary || {};
  const stageCounts = summary.stageCounts || {};
  const rehearsalSummary = payload?.rehearsalSummary || {};
  const strategies = Array.isArray(payload?.strategies) ? payload.strategies : [];
  const lifecycle = Array.isArray(payload?.orderLifecycle) ? payload.orderLifecycle : [];
  const riskTemplate = Array.isArray(payload?.riskTemplate) ? payload.riskTemplate : [];
  const disabledExecution = Array.isArray(payload?.disabledExecution) ? payload.disabledExecution : [];

  setText("testnetDrillMeta", summary.nextAction || "本地 Testnet 演练只保存审计记录，不连接交易所。");
  setText("testnetDrillCapital", formatUsd(summary.virtualAccountUsdt, 0));
  setText("testnetDrillReviewCandidates", String(stageCounts.localReviewCandidate ?? 0));
  setText("testnetDrillCandidates", String(stageCounts.testnetDrillCandidate ?? 0));
  setText("testnetDrillRehearsals", String(summary.rehearsalCount ?? rehearsalSummary.total ?? 0));
  setText("testnetDrillClosure", summary.localPathsComplete ? "本地闭环已补齐" : "待补演练");
  setText("testnetDrillExecution", summary.executionLocked === false ? "异常开启" : "关闭");

  const strategyTarget = el("testnetDrillStrategyList");
  if (strategyTarget) {
    strategyTarget.innerHTML = strategies.slice(0, 5).map((row) => {
      const tone = row.stage === "testnet_drill_candidate" ? "ok" : row.stage === "local_review_candidate" ? "warn" : "neutral";
      return `
        <div class="testnet-drill-row">
          <div class="testnet-drill-row-head">
            <div>
              <strong>${escapeHtml(row.plainName || row.readableName || row.taskId || "--")}</strong>
              <small>${escapeHtml(row.timeframe || "--")} / ${escapeHtml(row.stageLabel || row.stage || "--")}</small>
            </div>
            <span class="badge ${tone}">${escapeHtml(row.stageLabel || "观察")}</span>
          </div>
          <small>样本 ${row.closedSamples ?? 0} / 胜率 ${formatPercent(row.winRate)} / PF ${formatNumber(row.profitFactor)} / 累计R ${formatNumber(row.totalR, 1)}</small>
          <small>${escapeHtml(row.nextAction || "继续本地沙盒观察。")}</small>
        </div>
      `;
    }).join("") || '<div class="testnet-design-empty">暂无可演练策略；先让本地沙盒继续积累样本。</div>';
  }

  const lifecycleTarget = el("testnetDrillLifecycleList");
  if (lifecycleTarget) {
    lifecycleTarget.innerHTML = lifecycle.map((item) => `
      <div class="testnet-drill-row">
        <div class="testnet-drill-row-head">
          <strong>${escapeHtml(item.label || item.stageId || "--")}</strong>
          <span class="badge ${item.state === "required" ? "warn" : "ok"}">${escapeHtml(item.state || "local_only")}</span>
        </div>
        <small>${escapeHtml(item.description || "")}</small>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无生命周期演练步骤。</div>';
  }

  const riskTarget = el("testnetDrillRiskList");
  if (riskTarget) {
    riskTarget.innerHTML = riskTemplate.map((item) => `
      <div class="testnet-drill-row">
        <div class="testnet-drill-row-head">
          <strong>${escapeHtml(item.label || item.itemId || "--")}</strong>
          <span class="badge warn">${escapeHtml(item.status || "required")}</span>
        </div>
        <small>${escapeHtml(item.value || "")}</small>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无风控模板。</div>';
  }

  setText(
    "testnetDrillActionStatus",
    disabledExecution.length
      ? `执行权限关闭：${disabledExecution.slice(0, 3).join(" / ")}`
      : "只保存本地审计记录，不连接交易所。",
  );
}

async function runTestnetDrill() {
  const button = el("runTestnetDrillButton");
  if (!button) return;
  button.disabled = true;
  setText("testnetDrillActionStatus", "正在保存本地 Testnet 生命周期演练...");
  const rehearsal = latestTestnetDrillPayload?.rehearsalSummary || {};
  const needRejectPath = Number(rehearsal.rejected || 0) <= 0;
  const strategy = (latestTestnetDrillPayload?.strategies || [])[0] || {};
  try {
    await postJson("/api/pre-live-order-lifecycle/rehearse", {
      strategyId: strategy.taskId || strategy.strategyId || "local_testnet_drill_strategy",
      symbol: strategy.symbol || "LOCAL/USDT",
      direction: strategy.direction || "research_only",
      notionalValue: 100,
      riskR: needRejectPath ? 2.5 : 1,
      manualDecision: needRejectPath ? "reject_for_rehearsal" : "approve_for_rehearsal",
    });
    const refreshed = await getJsonSafe("/api/testnet-drill", { summary: {}, strategies: [], orderLifecycle: [], riskTemplate: [] }, 30000);
    renderTestnetDrill(refreshed);
    setText("testnetDrillActionStatus", "已保存本地演练记录：没有连接交易所，没有创建订单。");
  } catch (error) {
    setText("testnetDrillActionStatus", `演练保存失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

function renderTestnetAuditPack(payload) {
  latestTestnetAuditPayload = payload || {};
  if (!el("testnetAuditPanel")) return;
  const summary = payload?.summary || {};
  const items = Array.isArray(payload?.auditItems) ? payload.auditItems : [];
  const blockers = Array.isArray(payload?.criticalBlockers) ? payload.criticalBlockers : [];

  setText("testnetAuditMeta", summary.nextAction || "本地审计只用于判断下一步设计任务，不连接交易所。");
  setText("testnetAuditStage", summary.auditStageLabel || "--");
  setText("testnetAuditReviewCandidates", String(summary.reviewCandidateCount ?? 0));
  setText("testnetAuditRehearsals", String(summary.rehearsalCount ?? 0));
  setText("testnetAuditHardBlockers", String(summary.hardBlockerCount ?? blockers.length ?? 0));
  setText("testnetAuditSafetyFailures", String(summary.safetyFailureCount ?? 0));
  setText("testnetAuditConnection", summary.canConnectTestnet ? "异常开启" : "关闭");

  const itemTarget = el("testnetAuditItemList");
  if (itemTarget) {
    itemTarget.innerHTML = items.map((item) => `
      <div class="testnet-drill-row">
        <div class="testnet-drill-row-head">
          <div>
            <strong>${escapeHtml(item.label || "--")}</strong>
            <small>${escapeHtml(item.detail || "")}</small>
          </div>
          <span class="badge ${item.passed ? "ok" : item.severity === "safety" ? "danger" : "warn"}">${item.passed ? "通过" : "阻塞"}</span>
        </div>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无审计门槛。</div>';
  }

  const blockerTarget = el("testnetAuditBlockerList");
  if (blockerTarget) {
    blockerTarget.innerHTML = blockers.slice(0, 10).map((item) => `
      <div class="testnet-drill-row">
        <small>${escapeHtml(item)}</small>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无关键阻塞，但仍不能连接交易所。</div>';
  }
}

function renderTestnetPermissionCheck(payload) {
  latestTestnetPermissionPayload = payload || {};
  if (!el("testnetPermissionPanel")) return;
  const summary = payload?.summary || {};
  const checks = Array.isArray(payload?.checks) ? payload.checks : [];
  const references = Array.isArray(payload?.referenceInputs) ? payload.referenceInputs : [];

  setText("testnetPermissionMeta", summary.nextAction || "只读权限检查不会连接私有 Testnet。");
  setText("testnetPermissionStage", summary.stageLabel || "--");
  setText("testnetPermissionProbe", summary.publicProbeReady ? "已完成" : "待探测");
  setText("testnetPermissionPassed", String(summary.passedCheckCount ?? 0));
  setText("testnetPermissionBlocked", String(summary.blockedCheckCount ?? 0));
  setText("testnetPermissionApiKey", summary.canInputApiKey ? "异常开启" : "关闭");
  setText("testnetPermissionPrivate", summary.canConnectPrivateTestnet ? "异常开启" : "关闭");

  const checkTarget = el("testnetPermissionCheckList");
  if (checkTarget) {
    checkTarget.innerHTML = checks.map((item) => `
      <div class="testnet-drill-row">
        <div class="testnet-drill-row-head">
          <div>
            <strong>${escapeHtml(item.label || item.checkId || "--")}</strong>
            <small>${escapeHtml(item.detail || item.description || "")}</small>
          </div>
          <span class="badge ${item.passed ? "ok" : "warn"}">${item.passed ? "通过" : "阻塞"}</span>
        </div>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无权限检查。</div>';
  }

  const referenceTarget = el("testnetPermissionReferenceList");
  if (referenceTarget) {
    referenceTarget.innerHTML = references.map((item) => `
      <div class="testnet-drill-row">
        <strong>${escapeHtml(item.label || item.sourceId || "--")}</strong>
        <small>${escapeHtml(item.usableIdea || item.storedUse || "")}</small>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无参考资料。</div>';
  }
}

function renderTestnetSmallOrderSimulation(payload) {
  latestTestnetSmallOrderPayload = payload || {};
  if (!el("testnetSmallOrderPanel")) return;
  const summary = payload?.summary || {};
  const ticket = payload?.defaultTicket || {};
  const path = Array.isArray(payload?.orderPath) ? payload.orderPath : [];
  const recent = Array.isArray(payload?.recentSimulations) ? payload.recentSimulations : [];

  setText("testnetSmallOrderMeta", summary.nextAction || "本地模拟票据，不发交易所订单。");
  setText("testnetSmallOrderCapital", `${formatNumber(summary.virtualAccountUsdt, 0)} USDT`);
  setText("testnetSmallOrderDefaultNotional", `${formatNumber(summary.defaultNotionalUsdt, 2)} USDT`);
  setText("testnetSmallOrderMaxNotional", `${formatNumber(summary.maxNotionalUsdt, 2)} USDT`);
  setText("testnetSmallOrderRecentCount", String(summary.recentSimulationCount ?? recent.length));
  setText("testnetSmallOrderExchangeOrder", summary.canCreateExchangeOrder ? "异常开启" : "关闭");
  setText("testnetSmallOrderPrivate", summary.canConnectPrivateTestnet ? "异常开启" : "关闭");
  const notionalInput = el("testnetSmallOrderNotionalInput");
  if (notionalInput) {
    notionalInput.max = String(summary.maxNotionalUsdt || 1000);
    if (!notionalInput.value) {
      notionalInput.value = String(ticket.notionalUsdt || summary.defaultNotionalUsdt || 1000);
    }
  }
  setText(
    "testnetSmallOrderActionStatus",
    `默认：${ticket.symbol || "--"} · 可输入 1-${formatNumber(summary.maxNotionalUsdt || 1000, 0)} USDT · 只保存本地模拟。`,
  );

  const pathTarget = el("testnetSmallOrderPathList");
  if (pathTarget) {
    pathTarget.innerHTML = path.map((item) => `
      <div class="testnet-drill-row">
        <strong>${escapeHtml(item.label || item.stageId || "--")}</strong>
        <small>${escapeHtml(item.description || "")}</small>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无生命周期。</div>';
  }

  const recentTarget = el("testnetSmallOrderRecentList");
  if (recentTarget) {
    recentTarget.innerHTML = recent.slice(0, 8).map((item) => `
      <div class="testnet-drill-row">
        <div class="testnet-drill-row-head">
          <div>
            <strong>${escapeHtml(item.symbol || "--")}</strong>
            <small>${escapeHtml(item.strategyId || "--")} · ${formatNumber(item.notionalUsdt, 2)} USDT</small>
          </div>
          <span class="badge ${item.riskPassed ? "ok" : "warn"}">${item.riskPassed ? "本地通过" : "本地拒绝"}</span>
        </div>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无小额模拟票据。</div>';
  }
}

async function runTestnetSmallOrderSimulation() {
  const button = el("runTestnetSmallOrderButton");
  if (!button) return;
  const ticket = latestTestnetSmallOrderPayload?.defaultTicket || {};
  const summary = latestTestnetSmallOrderPayload?.summary || {};
  const notionalInput = el("testnetSmallOrderNotionalInput");
  const maxNotional = Number(summary.maxNotionalUsdt || 1000);
  const rawNotional = Number(notionalInput?.value || ticket.notionalUsdt || summary.defaultNotionalUsdt || 1000);
  const notionalUsdt = Number.isFinite(rawNotional) ? rawNotional : Number(summary.defaultNotionalUsdt || 1000);
  if (notionalUsdt <= 0 || notionalUsdt > maxNotional) {
    setText("testnetSmallOrderActionStatus", `请输入 1-${formatNumber(maxNotional, 0)} USDT 之间的本地模拟金额。`);
    return;
  }
  button.disabled = true;
  setText("testnetSmallOrderActionStatus", `正在保存 ${formatNumber(notionalUsdt, 2)} USDT Testnet 本地模拟票据...`);
  try {
    const response = await postJson("/api/testnet-small-order-simulation/rehearse", {
      strategyId: ticket.strategyId || "local_testnet_small_order_candidate",
      symbol: ticket.symbol || "BTC/USDT:USDT",
      side: ticket.side || "research_simulated_long",
      notionalUsdt,
      riskR: 0.05,
      manualDecision: "approve_simulation",
    });
    renderTestnetSmallOrderSimulation(response.testnetSmallOrderSimulation || {});
    setText("testnetSmallOrderActionStatus", "已保存本地小额模拟票据：没有连接交易所，没有创建订单。");
  } catch (error) {
    setText("testnetSmallOrderActionStatus", `保存失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

function renderSimpleConsole(strategies, reports, mobile, usableStrategyCatalog, sandboxDailyReport, sandboxAutoRunner, liveReadiness, simulationBridge, simulationReview, qualityCenter, concentrationReview = {}, resultReview = {}, strategyAssetPlaybook = {}) {
  if (!el("simpleConsole")) return;
  const rows = Array.isArray(usableStrategyCatalog?.strategies) ? usableStrategyCatalog.strategies : [];
  const catalogSummary = usableStrategyCatalog?.summary || {};
  const runnerState = getSimpleRunnerState(sandboxAutoRunner);
  const dailyReport = sandboxDailyReport?.latestReport || {};
  const dailySummary = dailyReport.summary || {};
  const allObservationTasks = buildUsableCatalogObservationTasks(usableStrategyCatalog);
  const activeSandboxIds = Array.isArray(simulationBridge?.activeSandboxStrategyIds)
    ? new Set(simulationBridge.activeSandboxStrategyIds)
    : null;
  const sandboxTasks = activeSandboxIds
    ? allObservationTasks.filter((row) => activeSandboxIds.has(row.strategyId))
    : allObservationTasks;
  const sandboxRows = buildSandboxSimulationRows(
    sandboxTasks,
    Array.isArray(dailyReport.strategyHealthRows) ? dailyReport.strategyHealthRows : [],
  );
  const totalCapital = sandboxRows.reduce((sum, row) => sum + Number(row.capital || 0), 0);
  const totalEquity = sandboxRows.reduce((sum, row) => sum + Number(row.equity || 0), 0);
  const totalClosedSamples = sandboxRows.reduce((sum, row) => sum + Number(row.closedPaperSampleCount || 0), 0);
  const lowCount = catalogSummary.lowFrequencyCount ?? rows.filter((row) => row.frequencyBucket !== "short_cycle").length;
  const shortCount = catalogSummary.shortCycleCount ?? rows.filter((row) => row.frequencyBucket === "short_cycle").length;
  const readinessSummary = liveReadiness?.summary || {};
  const executionLocked = !mobile?.safetyBoundary?.orderCreationAllowed;

  setText("simpleCurrentState", executionLocked ? "安全研究模式" : "异常：执行权限开启");
  setText("simpleCurrentMeta", executionLocked ? "实盘关闭 · 只做本地观察" : "请立刻复核权限边界");
  setText("simpleUsableStrategyCount", String(catalogSummary.totalUsableStrategies ?? rows.length));
  setText("simpleUsableStrategyMeta", `低频 ${lowCount} / 短周期 ${shortCount}`);
  setText("simpleSandboxState", runnerState.enabled ? "运行中" : "未开启");
  setText("simpleSandboxMeta", `每 ${runnerState.intervalMinutes} 分钟 · 今日 ${runnerState.todayRunCount}/${runnerState.maxRunsPerDay}`);
  setText("simpleSandboxEquity", sandboxRows.length ? `${formatUsd(totalEquity)} / ${formatUsd(totalCapital)}` : "--");
  setText("simpleSandboxSamples", `闭合样本 ${totalClosedSamples} · 今日 ${dailySummary.dailyClosedSampleCount ?? 0}`);

  const nextAction = !rows.length
    ? "下一步：点击“导入报告”，先把量化仓库里的策略报告同步到控制台。"
    : !runnerState.enabled
      ? "下一步：点击“启动本地沙盒”，让候选策略持续生成可复盘的虚拟观察数据。"
      : totalClosedSamples < 80
        ? "下一步：保持沙盒运行，优先累计闭合样本和失败样本，不急着升级实盘。"
        : readinessSummary.manualTicketReadyCount > 0
          ? "下一步：进入高级研究复核手动工单；仍然不自动下单。"
          : "下一步：复核沙盒样本、风险说明和策略弱点，再决定是否进入下一阶段。";
  setText("simpleNextAction", nextAction);

  updateSimpleSandboxButton(runnerState);
  renderSimpleSimulationBridge(simulationBridge);
  renderSimpleReviewQueue(simulationReview);
  renderQualityCenter(qualityCenter, concentrationReview, resultReview);
  renderStrategyAssetPlaybook(strategyAssetPlaybook);
  renderSimpleStrategyCards(rows);
  renderSimpleActionChecklist({ runnerState, rows, sandboxRows, dailySummary });
  latestSimpleConsolePayload = { strategies, reports, mobile, usableStrategyCatalog, sandboxDailyReport, sandboxAutoRunner, liveReadiness, simulationBridge, simulationReview, qualityCenter, concentrationReview, resultReview, strategyAssetPlaybook };
}

function renderLocalLabPage(usableStrategyCatalog, sandboxDailyReport, sandboxAutoRunner, qualityCenter = {}, resultReview = {}, simulationBridge = {}, simulationReview = {}, strategyLearningLoop = {}) {
  if (!el("localLab")) return;
  const runnerState = getSimpleRunnerState(sandboxAutoRunner);
  const report = sandboxDailyReport?.latestReport || {};
  const dailySummary = report.summary || {};
  const allQualityRows = Array.isArray(report.strategyHealthRows) ? report.strategyHealthRows : [];
  const allObservationTasks = buildUsableCatalogObservationTasks(usableStrategyCatalog);
  const activeSandboxIds = Array.isArray(simulationBridge?.activeSandboxStrategyIds)
    ? new Set(simulationBridge.activeSandboxStrategyIds)
    : null;
  const observationTasks = activeSandboxIds
    ? allObservationTasks.filter((row) => activeSandboxIds.has(row.strategyId))
    : allObservationTasks;
  const activeTaskIds = new Set(observationTasks.map((row) => row.taskId));
  const qualityRows = activeSandboxIds
    ? allQualityRows.filter((row) => activeTaskIds.has(row.taskId))
    : allQualityRows;
  const sandboxRows = buildSandboxSimulationRows(observationTasks, qualityRows);
  const totalCapital = sandboxRows.reduce((sum, row) => sum + Number(row.capital || 0), 0);
  const totalEquity = sandboxRows.reduce((sum, row) => sum + Number(row.equity || 0), 0);
  const totalClosedSamples = sandboxRows.reduce((sum, row) => sum + Number(row.closedPaperSampleCount || 0), 0);
  const qualitySummary = qualityCenter?.summary || {};
  const bridgeSummary = simulationBridge?.summary || {};
  const reviewSummary = simulationReview?.summary || {};
  const reviewQueue = Array.isArray(simulationReview?.queue) ? simulationReview.queue : [];
  const rawReviewRows = reviewQueue.length ? reviewQueue : (Array.isArray(qualityCenter?.strategies) ? qualityCenter.strategies : []);
  const reviewRows = activeSandboxIds
    ? rawReviewRows.filter((row) => activeSandboxIds.has(row.strategyId) || activeTaskIds.has(row.taskId))
    : rawReviewRows;
  const resultSummary = resultReview?.summary || {};
  const learningRoot = strategyLearningLoop?.strategyLearningLoop || strategyLearningLoop || {};
  const learningSummary = learningRoot?.learningLoop?.summary || learningRoot?.summary || {};

  const hasActiveSandboxStrategies = Number(bridgeSummary.strategyCount ?? sandboxRows.length) > 0;
  setText("localLabRunnerState", runnerState.enabled ? (hasActiveSandboxStrategies ? "运行中" : "等待新策略") : "未开启");
  setText("localLabRunnerMeta", `每 ${runnerState.intervalMinutes} 分钟 · 今日 ${runnerState.todayRunCount}/${runnerState.maxRunsPerDay} · 最近 ${formatDate(runnerState.lastRunAt)}`);
  const bridgeEquity = Number(bridgeSummary.totalVirtualEquity || totalEquity || 0);
  const bridgeCapital = Number(bridgeSummary.totalVirtualCapital || totalCapital || 0);
  const bridgeClosedSamples = Number(bridgeSummary.totalClosedSampleCount || reviewSummary.totalClosedSamples || totalClosedSamples || 0);
  setText("localLabEquity", bridgeEquity ? formatUsd(bridgeEquity) : "--");
  setText("localLabCapital", bridgeEquity ? `虚拟本金 ${formatUsd(bridgeCapital)} · 浮动 ${formatUsd(bridgeEquity - bridgeCapital, 2)}` : "等待本地沙盒样本");
  setText("localLabClosedSamples", String(bridgeClosedSamples));
  setText("localLabQuality", `今日闭合 ${dailySummary.dailyClosedSampleCount ?? 0} · 平均健康 ${formatNumber(dailySummary.averageHealthScore ?? qualitySummary.averageHealthScore, 0)}`);
  setText("localLabReviewReady", String(reviewSummary.reviewReadyStrategies ?? qualitySummary.testnetPrepCandidateCount ?? resultSummary.reviewReadyStrategyCount ?? 0));
  setText("localLabTestnetCandidates", `Demo 候选 ${reviewSummary.promotedCandidates ?? qualitySummary.testnetReadinessCandidateCount ?? qualitySummary.testnetPrepCandidateCount ?? 0}`);
  setText("localLabSimulationState", bridgeSummary.stageLabel || (bridgeSummary.localSimulationRunning ? "本地模拟盘运行中" : "等待本地模拟"));
  setText("localLabSimulationMeta", `策略 ${bridgeSummary.strategyCount ?? sandboxRows.length} · 候选 ${bridgeSummary.simulationReviewCandidateCount ?? reviewSummary.promotedCandidates ?? 0}`);
  setText("localLabLearningState", `${learningSummary.learningItemCount ?? 0} 条`);
  setText("localLabLearningMeta", `观察 ${learningSummary.researchWatchlistCount ?? 0} · 暂拒 ${learningSummary.graveyardCount ?? 0} · 因子 ${learningSummary.factorMemoryCount ?? 0}`);
  setText("localLabQueueState", String(reviewSummary.totalStrategies ?? reviewRows.length ?? 0));
  setText("localLabQueueMeta", `晋级 ${reviewSummary.promotedCandidates ?? 0} · 样本门槛 ${reviewSummary.reviewMinimumClosedSamples ?? 30}`);
  setText("localLabStrategyMeta", `${sandboxRows.length} 条策略在本地观察 · 已晋级 Demo ${bridgeSummary.demoTrialStrategyCount ?? 0} 条`);
  setText("localLabReviewMeta", `复核候选 ${reviewSummary.promotedCandidates ?? qualitySummary.testnetPrepCandidateCount ?? 0} · 风险复盘 ${qualitySummary.riskReviewCount ?? 0}`);
  setText("localLabActionStatus", runnerState.enabled
    ? hasActiveSandboxStrategies
      ? `已开启持续观察：每 ${runnerState.intervalMinutes} 分钟检查一次。`
      : `每 ${runnerState.intervalMinutes} 分钟检查一次新候选；当前 10 条已移入 Demo。`
    : "点击运行后，本地沙盒会持续生成本地观察样本。");
  updateLocalSandboxRunButton(runnerState.enabled, runnerState.status);

  const strategyTarget = el("localLabStrategyList");
  if (strategyTarget) {
    strategyTarget.innerHTML = sandboxRows.slice(0, 8).map((row) => {
      const metrics = row.historicalMetrics || {};
      return `
        <div class="sandbox-lane-row">
          <div class="sandbox-lane-row-head">
            <div>
              <strong>${escapeHtml(row.title)}</strong>
              <small>${escapeHtml(row.taskId || "--")} · ${escapeHtml(row.timeframe || "--")} · ${escapeHtml(row.pair || "等待信号")}</small>
            </div>
            <span class="badge ${row.tone}">${escapeHtml(row.statusLabel)}</span>
          </div>
          <div class="artifact-metrics">
            <span>权益 ${formatUsd(row.equity)}</span>
            <span>浮动 ${formatUsd(row.pnl, 2)}</span>
            <span>累计 ${formatNumber(row.realizedR, 2)}R</span>
            <span>闭合 ${row.closedPaperSampleCount}</span>
            <span>规则 ${row.ruleMatchedCount}</span>
          </div>
          <div class="artifact-metrics">
            <span>历史样本 ${metrics.tradeCount ?? "--"}</span>
            <span>历史胜率 ${formatPercent(metrics.winRatePct)}</span>
            <span>历史 PF ${formatNumber(metrics.profitFactor)}</span>
          </div>
          <div class="sandbox-lane-next">${escapeHtml(row.nextAction)}</div>
        </div>
      `;
    }).join("") || `<div class="sandbox-lane-empty">当前没有待跑策略。已有 ${bridgeSummary.demoTrialStrategyCount ?? 0} 条策略晋级 Demo，原有样本仍保留。</div>`;
  }

  const reviewTarget = el("localLabReviewList");
  if (reviewTarget) {
    reviewTarget.innerHTML = reviewRows.slice(0, 8).map((row) => {
      const tone = qualityTone(row.status);
      const metrics = row.metrics || row;
      return `
        <div class="sandbox-lane-row">
          <div class="sandbox-lane-row-head">
            <div>
              <strong>${escapeHtml(row.strategyName || row.title || row.taskId || "--")}</strong>
              <small>${escapeHtml(row.taskId || row.strategyId || "--")} · ${escapeHtml(row.timeframe || "--")} · 最近 ${formatDate(row.latestLogAt)}</small>
            </div>
            <span class="badge ${tone}">${escapeHtml(row.statusLabel || observationQualityLabels[row.status] || row.status || "复核中")}</span>
          </div>
          <div class="artifact-metrics">
            <span>闭合 ${metrics.closedSamples ?? metrics.closedPaperSampleCount ?? 0}</span>
            <span>胜率 ${formatPercent(metrics.winRate)}</span>
            <span>PF ${formatNumber(metrics.profitFactor)}</span>
            <span>健康 ${formatNumber(metrics.healthScore, 0)}</span>
          </div>
          <div class="sandbox-lane-next">${escapeHtml(row.recommendedAction || row.nextAction || "继续补充本地闭合样本和失败样本。")}</div>
        </div>
      `;
    }).join("") || '<div class="sandbox-lane-empty">暂无本地复核队列；已晋级策略请到 Demo 模拟页面查看。</div>';
  }
}

function translateExchangeDemoBlocker(value) {
  const labels = {
    okx_demo_private_gate_disabled: "OKX Demo 私有接口开关未开启",
    okx_demo_private_connection_disabled: "OKX Demo 私有连接开关未开启",
    okx_demo_order_gate_disabled: "OKX Demo 下单开关未开启",
    okx_demo_automation_gate_disabled: "Demo Release 自动执行开关未开启",
    okx_demo_cancel_gate_disabled: "OKX Demo 撤单演练开关未开启",
    okx_demo_credentials_missing: "OKX Demo 环境变量凭据不完整",
    manual_confirm_required: "缺少人工订单确认口令",
    manual_emergency_confirm_required: "缺少紧急演练确认口令",
    explicit_size_required_for_okx_demo_order: "必须手动填写 OKX sz 数量",
    limit_price_required: "限价单必须填写 px",
    ord_id_required_for_real_demo_cancel: "真实 Demo 撤单必须填写 ordId",
    notional_out_of_demo_cap: "名义金额超过 Demo 上限",
    invalid_demo_base_url: "Demo Base URL 不在允许列表",
    no_eligible_demo_release: "暂无通过全部硬门槛的不可变 Demo Release",
    demo_release_not_found: "指定 Demo Release 不存在",
    demo_runtime_paused: "Demo 新开仓已自动暂停",
    demo_kill_switch_active: "Demo kill switch 已启用",
  };
  return labels[value] || value || "--";
}

function translateExchangeDemoStatus(value) {
  const labels = {
    available: "可用",
    locked: "锁定",
    readonly_ready: "只读就绪",
    disabled: "关闭",
    blocked: "已阻塞",
    passed: "通过",
    failed: "失败",
    completed: "已完成",
    submitted: "已提交",
    local_drill_saved: "本地演练已保存",
    not_run: "尚未检查",
    manual_required: "需要人工处理",
    waiting_credentials: "等待凭据",
    waiting: "等待",
    ready: "就绪",
    strategy_loaded: "策略已载入",
    scanned: "已扫描",
    market_ready: "行情可用",
    market_gap: "行情缺口",
    manual_required: "需要人工确认",
  };
  return labels[value] || value || "--";
}

function renderExchangeDemoPipeline(pipeline = {}) {
  const summary = pipeline.summary || {};
  const candidates = Array.isArray(pipeline.candidates) ? pipeline.candidates : [];
  const trialPool = Array.isArray(pipeline.trialPool) ? pipeline.trialPool : [];
  const preferredCandidate = pipeline.preferredCandidate || candidates[0] || null;
  latestExchangeDemoCandidate = preferredCandidate;

  setText("exchangeDemoLoadedStrategies", String(summary.strategyCount ?? 0));
  setText("exchangeDemoLoadedStrategiesMeta", `已晋级 ${summary.demoTrialCount ?? trialPool.length} · 回测 ${summary.historicalTradeCount ?? 0} · 旧沙盒汇总 ${summary.historicalSandboxAggregateClosedSampleCount ?? 0}`);
  setText("exchangeDemoCandidateSymbols", String(summary.candidateCount ?? candidates.length));
  setText("exchangeDemoCandidateSymbolsMeta", preferredCandidate ? `首选 ${preferredCandidate.instId || preferredCandidate.symbol || "--"}` : "等待策略候选");
  setText("exchangeDemoMarketState", summary.publicProbeCount ? `${summary.publicOkCount ?? 0}/${summary.publicProbeCount}` : "未扫描");
  setText("exchangeDemoMarketMeta", summary.publicProbeCount ? "OKX 公共行情探测结果" : "点击扫描后读取 OKX 公共行情");
  setText("exchangeDemoAutomationState", summary.autoOrderAllowed ? "允许" : "手动确认");
  setText("exchangeDemoAutomationMeta", summary.manualOrderRequired ? "只自动筛选和填票据，不自动提交订单" : "订单仍受 Demo 闸门控制");
  setText("exchangeDemoPipelineMeta", summary.nextAction || "加载策略、读取公共行情、筛选候选，再人工确认 Demo 票据。");

  const trialTarget = el("exchangeDemoTrialStrategyList");
  if (trialTarget) {
    trialTarget.innerHTML = trialPool.map((strategy) => `
      <div class="exchange-demo-candidate-row is-selected">
        <div>
          <div class="exchange-demo-candidate-row-head">
            <div>
              <strong>${escapeHtml(strategy.strategyName || strategy.strategyId || "--")}</strong>
              <small>${escapeHtml(strategy.timeframe || "--")} · ${escapeHtml(strategy.direction === "short" ? "空头" : "多头")} · ${escapeHtml(strategy.strategyId || "--")}</small>
            </div>
            <span class="badge ok">Demo 观察中</span>
          </div>
          <div class="artifact-metrics">
            <span>历史样本 ${strategy.historicalTradeCount ?? 0}</span>
            <span>历史胜率 ${formatPercent(strategy.historicalWinRatePct)}</span>
            <span>历史 PF ${formatNumber(strategy.historicalProfitFactor)}</span>
            <span>目标 ${formatNumber(strategy.targetR, 1)}R</span>
            <span>本地闭合 ${strategy.localClosedSampleCount ?? 0}</span>
            <span>评分 ${formatNumber(strategy.score, 1)}</span>
          </div>
          <div class="sandbox-lane-next">${escapeHtml(strategy.nextAction || "等待 Demo 行情观察。")}</div>
        </div>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无已晋级 Demo 的策略。</div>';
  }

  const target = el("exchangeDemoCandidateList");
  if (!target) return;
  target.innerHTML = candidates.slice(0, 8).map((candidate, index) => {
    const isSelected = preferredCandidate && candidate.candidateId === preferredCandidate.candidateId;
    const status = translateExchangeDemoStatus(candidate.screeningStatus || candidate.marketDataStatus);
    return `
      <div class="exchange-demo-candidate-row ${isSelected ? "is-selected" : ""}" data-candidate-index="${index}">
        <div>
          <div class="exchange-demo-candidate-row-head">
            <div>
              <strong>${escapeHtml(candidate.strategyName || "--")}</strong>
              <small>${escapeHtml(candidate.instId || candidate.symbol || "--")} · ${escapeHtml(candidate.timeframe || "--")} · ${escapeHtml(candidate.frequencyLabel || "--")}</small>
            </div>
            <span class="badge ${candidate.screeningStatus === "market_ready" ? "ok" : candidate.screeningStatus === "market_gap" ? "warn" : "neutral"}">${escapeHtml(status)}</span>
          </div>
          <div class="artifact-metrics">
            <span>方向 ${escapeHtml(candidate.side === "sell" ? "做空方向" : "做多方向")}</span>
            <span>评分 ${formatNumber(candidate.score, 1)}</span>
            <span>胜率 ${formatPercent(candidate.winRatePct)}</span>
            <span>PF ${formatNumber(candidate.profitFactor)}</span>
            <span>目标 ${formatNumber(candidate.targetR, 1)}R</span>
          </div>
          <div class="sandbox-lane-next">${escapeHtml(candidate.reason || "候选等待扫描。")}</div>
        </div>
        <div class="exchange-demo-candidate-actions">
          <button class="secondary exchange-demo-use-candidate" type="button" data-candidate-index="${index}">填入</button>
        </div>
      </div>
    `;
  }).join("") || '<div class="testnet-design-empty">暂无 Demo 候选。请先导入或刷新可用策略库。</div>';
  target.querySelectorAll(".exchange-demo-use-candidate").forEach((button) => {
    button.addEventListener("click", () => {
      const idx = Number(button.getAttribute("data-candidate-index") || 0);
      fillExchangeDemoTicketFromCandidate(candidates[idx]);
    });
  });
}

function renderNoKeyMiniRows(targetId, rows = []) {
  const target = el(targetId);
  if (!target) return;
  target.innerHTML = rows.length
    ? rows.map((item) => `<span>${escapeHtml(item)}</span>`).join("")
    : '<span>暂无数据。</span>';
}

function renderNoKeyLayerExplanations(payload = {}) {
  const sample = payload.sampleLayerSummary || payload.summary?.sampleLayer || {};
  const balance = payload.directionBalance || payload.summary?.directionBalance || {};
  const universe = payload.universeScope || payload.summary?.universeScope || {};
  const longLane = payload.longCandidateLane || payload.summary?.longCandidateLane || {};
  const directionRows = Array.isArray(balance.rows) ? balance.rows : [];

  renderNoKeyMiniRows("noKeySampleLayer", [
    `旧沙盒闭合样本：${sample.paperObservationLogRows ?? 0} 条`,
    `沙盒运行 / 日报：${sample.localSandboxRunCount ?? 0} / ${sample.localSandboxDailyReportCount ?? 0}`,
    `健康快照 / 学习快照：${sample.localSandboxHealthSnapshotCount ?? 0} / ${sample.localSandboxLearningSnapshotCount ?? 0}`,
    sample.note || "旧样本和新的候选票据是两层数据。",
  ]);

  renderNoKeyMiniRows("noKeyDirectionBalance", [
    ...directionRows.map((row) => `${row.label || row.direction}: 策略 ${row.strategyCount ?? 0} / 当前候选 ${row.candidateCount ?? 0}`),
    balance.note || "策略库会同时保留多头和空头研究方向。",
  ]);

  renderNoKeyMiniRows("noKeyUniverseScope", [
    `${universe.currentModeLabel || "当前 selectedPairs 公共行情探测"}`,
    `已选币种池：${universe.selectedPairCount ?? 0}；当前候选币种：${universe.candidatePairCount ?? 0}`,
    universe.marketWideScanEnabled ? "全市场扫描：已开启" : "全市场扫描：未开启，下一步进入流动性过滤扫描",
    universe.note || "当前不是单一固定币种，也还不是全市场实时扫描。",
  ]);

  setText("noKeyLongLaneStatus", longLane.nextAction || "等待多头候选池扫描。");
  renderNoKeyMiniRows("noKeyLongLaneItems", [
    `多头研究策略：${longLane.strategyCount ?? 0} 条；当前多头公共候选：${longLane.publicCandidateCount ?? 0} 条`,
    ...(Array.isArray(longLane.watchItems) ? longLane.watchItems : []),
    longLane.note || "多头候选必须通过和空头一样的复核门槛。",
  ]);
}

function renderNoKeyPreLiveWorkbench(payload = {}) {
  if (!el("noKeyPreLivePanel")) return;
  latestNoKeyPreLivePayload = payload || {};
  const summary = payload.summary || {};
  const cards = Array.isArray(payload.strategyCards) ? payload.strategyCards : [];
  const candidates = Array.isArray(payload.publicCandidates) ? payload.publicCandidates : [];
  const tickets = Array.isArray(payload.recentTickets) ? payload.recentTickets : [];
  const preferred = payload.preferredCandidate || candidates.find((row) => row.screeningStatus === "market_ready") || candidates[0] || null;
  latestNoKeyPreLiveCandidate = preferred;

  setText("noKeyStrategyCount", String(summary.strategyCardCount ?? cards.length ?? 0));
  setText("noKeyMarketReady", String(summary.marketReadyCount ?? candidates.filter((row) => row.screeningStatus === "market_ready").length));
  setText("noKeyTicketCount", String(summary.ticketCount ?? tickets.length ?? 0));
  setText("noKeyLatestScan", summary.latestScanAt ? formatDate(summary.latestScanAt) : "尚未扫描");
  setText("noKeyActionStatus", summary.nextAction || "先用公共行情扫描候选，不需要 API Key。");
  renderNoKeyLayerExplanations(payload);

  const cardsTarget = el("noKeyStrategyCards");
  if (cardsTarget) {
    cardsTarget.innerHTML = cards.slice(0, 10).map((card) => {
      const metrics = card.metrics || {};
      const riskNotes = Array.isArray(card.riskNotes) ? card.riskNotes : [];
      const entryContext = Array.isArray(card.entryContext) ? card.entryContext : [];
      return `
        <div class="no-key-strategy-card">
          <div class="no-key-card-head">
            <div>
              <strong>${escapeHtml(card.plainName || card.name || "--")}</strong>
              <small>${escapeHtml(card.frequencyLabel || card.timeframe || "--")} · ${escapeHtml(card.direction || "--")} · 目标 ${formatNumber(card.targetR, 1)}R</small>
            </div>
            <span class="badge neutral">${escapeHtml(card.family || "strategy")}</span>
          </div>
          <p>${escapeHtml(card.explanation || "本地候选策略，等待更多观察样本。")}</p>
          <div class="artifact-metrics">
            <span>样本 ${metrics.tradeCount ?? "--"}</span>
            <span>胜率 ${formatPercent(metrics.winRatePct)}</span>
            <span>PF ${formatNumber(metrics.profitFactor)}</span>
            <span>回撤 ${formatNumber(metrics.maxDrawdownR, 1)}R</span>
          </div>
          <div class="no-key-mini-list">
            ${entryContext.slice(0, 2).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
            ${riskNotes.slice(0, 1).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
          </div>
        </div>
      `;
    }).join("") || '<div class="testnet-design-empty">暂无可解释策略。请先刷新策略目录。</div>';
  }

  const candidateTarget = el("noKeyCandidateList");
  if (candidateTarget) {
    candidateTarget.innerHTML = candidates.slice(0, 10).map((candidate, index) => {
      const selected = preferred && candidate.candidateId === preferred.candidateId;
      const ready = candidate.screeningStatus === "market_ready";
      return `
        <div class="exchange-demo-candidate-row ${selected ? "is-selected" : ""}" data-no-key-index="${index}">
          <div>
            <div class="exchange-demo-candidate-row-head">
              <div>
                <strong>${escapeHtml(candidate.strategyName || "--")}</strong>
                <small>${escapeHtml(candidate.instId || candidate.symbol || "--")} · ${escapeHtml(candidate.timeframe || "--")} · ${escapeHtml(candidate.frequencyLabel || "--")}</small>
              </div>
              <span class="badge ${ready ? "ok" : candidate.screeningStatus === "market_gap" ? "warn" : "neutral"}">${ready ? "公共行情可用" : translateExchangeDemoStatus(candidate.screeningStatus || candidate.marketDataStatus)}</span>
            </div>
            <div class="artifact-metrics">
              <span>方向 ${escapeHtml(candidate.side === "sell" ? "空头观察" : "多头观察")}</span>
              <span>评分 ${formatNumber(candidate.score, 1)}</span>
              <span>胜率 ${formatPercent(candidate.winRatePct)}</span>
              <span>PF ${formatNumber(candidate.profitFactor)}</span>
              <span>目标 ${formatNumber(candidate.targetR, 1)}R</span>
            </div>
            <div class="sandbox-lane-next">${escapeHtml(candidate.reason || "等待公共行情扫描。")}</div>
          </div>
          <div class="exchange-demo-candidate-actions">
            <button class="secondary no-key-use-candidate" type="button" data-no-key-index="${index}">选中</button>
          </div>
        </div>
      `;
    }).join("") || '<div class="testnet-design-empty">暂无候选。点击公共行情扫描后会显示可观察币种。</div>';
    candidateTarget.querySelectorAll(".no-key-use-candidate").forEach((button) => {
      button.addEventListener("click", () => {
        const idx = Number(button.getAttribute("data-no-key-index") || 0);
        latestNoKeyPreLiveCandidate = candidates[idx];
        setText("noKeyActionStatus", `已选中 ${latestNoKeyPreLiveCandidate.instId || latestNoKeyPreLiveCandidate.symbol || "--"}，可以运行自动执行引擎生成本地生命周期记录。`);
        renderNoKeyPreLiveWorkbench({ ...latestNoKeyPreLivePayload, preferredCandidate: latestNoKeyPreLiveCandidate });
      });
    });
  }

  const ticketTarget = el("noKeyRecentTickets");
  if (ticketTarget) {
    ticketTarget.innerHTML = tickets.slice(0, 6).map((ticket) => `
      <div class="testnet-drill-row">
        <div class="testnet-drill-row-head">
          <div>
            <strong>${escapeHtml(ticket.strategyName || ticket.strategyId || "--")}</strong>
            <small>${escapeHtml(ticket.instId || ticket.symbol || "--")} · ${formatDate(ticket.createdAt)}</small>
          </div>
          <span class="badge ${ticket.ticketStatus === "local_observation" ? "ok" : "warn"}">${escapeHtml(ticket.ticketStatus || "--")}</span>
        </div>
        <div class="artifact-metrics">
          <span>方向 ${escapeHtml(ticket.side === "sell" ? "空头观察" : "多头观察")}</span>
          <span>名义 ${formatNumber(ticket.notionalUsdt, 0)} USDT</span>
          <span>不下单</span>
        </div>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无本地观察票据。</div>';
  }
}

const autoExecutionCodeLabels = {
  completed: "已完成",
  ready: "已就绪",
  waiting: "等待中",
  selected: "已选中",
  passed: "已通过",
  blocked: "已阻塞",
  local_tp_sl_watch: "本地模拟持有",
  local_simulated_open: "本地模拟持有",
  blocked_before_local_execution: "本地执行前已阻塞",
  take_profit_2r: "达到 2R",
  target_2r_hit: "达到 2R",
  stop_loss_1r: "触发 -1R",
  stop_loss_hit: "触发 -1R",
  expired_exit: "过期退出",
  timeout_exit: "过期退出",
  public_market_not_ready: "公共行情筛选未就绪",
  target_r_below_2: "目标收益风险比低于 2R",
  score_below_gate: "候选评分未达门槛",
  trade_count_below_gate: "回测样本数未达门槛",
  profit_factor_below_gate: "盈亏因子未达门槛",
  notional_above_local_cap: "本地名义金额超过上限",
  cooldown_duplicate_open_record: "已有同类活跃记录，当前处于冷却中",
  max_executions_per_run_reached: "本轮本地观察名额已满",
};

function translateAutoExecutionCode(value) {
  const code = String(value || "").trim();
  if (!code) return "--";
  if (autoExecutionCodeLabels[code]) return autoExecutionCodeLabels[code];
  if (code.startsWith("higher_rank_candidate_selected_for_")) {
    return "同币种已有更高排名候选入选";
  }
  return /[a-z][a-z0-9_]+/i.test(code) ? "未标准化原因" : code;
}

function formatReviewR(value) {
  if (value === null || value === undefined || value === "") return "--";
  return `${formatNumber(value, 2)}R`;
}

function renderAutoExecutionEngine(payload = {}) {
  latestAutoExecutionEnginePayload = payload || {};
  const summary = payload.summary || {};
  const records = Array.isArray(payload.records) ? payload.records : [];
  const runs = Array.isArray(payload.recentRuns) ? payload.recentRuns : [];
  setText("noKeyTicketCount", String(summary.openLifecycleRecords ?? records.filter((row) => row.executionStatus === "local_tp_sl_watch").length));
  setText("autoExecutionStatus", summary.nextAction || "无票据流程：策略→仲裁→风控→本地生命周期记录。");

  const target = el("autoExecutionRecordList");
  if (!target) return;
  target.innerHTML = records.slice(0, 10).map((record) => {
    const selected = record.routeStatus === "selected" && record.riskStatus === "passed";
    const blockers = Array.isArray(record.riskBlockers) ? record.riskBlockers : [];
    const routerBlockers = Array.isArray(record.routerBlockers) ? record.routerBlockers : [];
    const lifecycle = Array.isArray(record.lifecycle) ? record.lifecycle : [];
    return `
      <div class="testnet-drill-row auto-execution-row ${selected ? "is-open" : "is-blocked"}">
        <div class="testnet-drill-row-head">
          <div>
            <strong>${escapeHtml(record.strategyName || record.strategyId || "--")}</strong>
            <small>${escapeHtml(record.instId || record.symbol || "--")} · ${escapeHtml(record.timeframe || "--")} · ${formatDate(record.createdAt)}</small>
          </div>
          <span class="badge ${selected ? "ok" : "warn"}">${selected ? "本地观察中" : "已阻塞"}</span>
        </div>
        <div class="artifact-metrics">
          <span>方向 ${escapeHtml(record.directionLabel || (record.side === "sell" ? "空头观察" : "多头观察"))}</span>
          <span>名义 ${formatNumber(record.notionalUsdt, 0)} USDT</span>
          <span>目标 ${formatNumber(record.targetR, 1)}R / 止损 1R</span>
          <span>胜率 ${formatPercent(record.winRatePct)}</span>
          <span>PF ${formatNumber(record.profitFactor)}</span>
          <span>样本 ${record.tradeCount ?? "--"}</span>
        </div>
        <div class="no-key-mini-list">
          ${lifecycle.slice(0, 4).map((step) => `<span>${escapeHtml(step.label || "生命周期步骤")}：${escapeHtml(translateAutoExecutionCode(step.status))}</span>`).join("")}
          ${(routerBlockers.length || blockers.length) ? `<span>阻塞：${escapeHtml([...routerBlockers, ...blockers].map(translateAutoExecutionCode).join(" / "))}</span>` : "<span>实盘订单：锁定；仅保存本地模拟执行记录。</span>"}
        </div>
      </div>
    `;
  }).join("") || `
    <div class="testnet-design-empty">
      暂无自动执行生命周期记录。先扫描公共行情，再点击“运行自动执行引擎”。
      ${runs.length ? `最近运行：${escapeHtml(runs[0].runId || "--")}` : ""}
    </div>
  `;
}

function renderAutoExecutionLifecycle(payload = {}) {
  latestAutoExecutionLifecyclePayload = payload || {};
  const summary = payload.summary || {};
  const lanes = Array.isArray(payload.lanes) ? payload.lanes : [];
  setText("autoLifecycleStatus", summary.nextAction || "读取本地自动执行记录，按生命周期状态分组。");
  setText("autoLifecycleActive", String(summary.activeRecords ?? 0));
  setText("autoLifecycleBlocked", String(summary.blockedRecords ?? 0));
  setText("autoLifecycleTp", String(summary.takeProfitCount ?? 0));
  setText("autoLifecycleSl", String(summary.stopLossCount ?? 0));
  setText("autoLifecycleExpired", String(summary.expiredCount ?? 0));

  const target = el("autoLifecycleLanes");
  if (!target) return;
  target.innerHTML = lanes.map((lane) => {
    const records = Array.isArray(lane.records) ? lane.records : [];
    return `
      <div class="auto-lifecycle-lane auto-lifecycle-lane-${escapeHtml(lane.laneId || "unknown")}">
        <div class="auto-lifecycle-lane-head">
          <strong>${escapeHtml(lane.label || lane.laneId || "--")}</strong>
          <span>${formatNumber(lane.count, 0)}</span>
        </div>
        <div class="auto-lifecycle-cards">
          ${records.slice(0, 6).map((record) => {
            const blockers = Array.isArray(record.blockers) ? record.blockers : [];
            const isBlocked = record.laneId === "blocked";
            return `
              <div class="auto-lifecycle-card ${isBlocked ? "is-blocked" : "is-active"}">
                <div class="auto-lifecycle-card-head">
                  <strong>${escapeHtml(record.strategyName || record.strategyId || "--")}</strong>
                  <span>${escapeHtml(record.timeframe || "--")}</span>
                </div>
                <small>${escapeHtml(record.instId || record.symbol || "--")} · ${escapeHtml(record.directionLabel || "--")} · ${formatDate(record.createdAt)}</small>
                <div class="artifact-metrics">
                  <span>${formatNumber(record.notionalUsdt, 0)} USDT</span>
                  <span>${formatNumber(record.targetR, 1)}R / 1R</span>
                  <span>PF ${formatNumber(record.profitFactor)}</span>
                  <span>样本 ${record.tradeCount ?? "--"}</span>
                </div>
                <p>${escapeHtml(record.lifecycleNote || "本地模拟生命周期记录。")}</p>
                ${blockers.length ? `<div class="auto-lifecycle-blockers">${escapeHtml(blockers.slice(0, 3).map(translateAutoExecutionCode).join(" / "))}</div>` : ""}
              </div>
            `;
          }).join("") || '<div class="testnet-design-empty">暂无记录</div>'}
        </div>
      </div>
    `;
  }).join("") || '<div class="testnet-design-empty">暂无生命周期数据。先运行自动执行引擎。</div>';
}

function renderAutoExecutionReview(payload = {}) {
  latestAutoExecutionReviewPayload = payload || {};
  const summary = payload.summary || {};
  const reasons = Array.isArray(payload.blockedReasonBreakdown) ? payload.blockedReasonBreakdown : [];
  const activeRows = Array.isArray(payload.activeHoldingQueue) ? payload.activeHoldingQueue : [];
  const closedRows = Array.isArray(payload.closedResultsQueue) ? payload.closedResultsQueue : [];
  const blockedRows = Array.isArray(payload.blockedReviewQueue) ? payload.blockedReviewQueue : [];
  const strategyRows = Array.isArray(payload.strategyLifecycleSummary) ? payload.strategyLifecycleSummary : [];
  const symbolRows = Array.isArray(payload.symbolBreakdown) ? payload.symbolBreakdown : [];
  const directionRows = Array.isArray(payload.directionBreakdown) ? payload.directionBreakdown : [];
  const recommendations = Array.isArray(payload.systemRecommendations) ? payload.systemRecommendations : [];

  setText("autoReviewStatus", summary.stageConclusion || "当前是执行链路观察阶段，不是策略晋级阶段。");
  setText("autoReviewTotal", String(summary.totalRecords ?? 0));
  setText("autoReviewActive", String(summary.activeHoldingRecords ?? 0));
  setText("autoReviewBlocked", String(summary.blockedRecords ?? 0));
  setText("autoReviewClosed", String(summary.closedResults ?? 0));
  setText("autoReviewWaiting", String(summary.waitingTriggerRecords ?? 0));
  setText("autoReviewCoverage", `${formatNumber(summary.reasonStandardizationCoveragePct ?? 0, 0)}%`);

  const recommendationTarget = el("autoReviewRecommendations");
  if (recommendationTarget) {
    recommendationTarget.innerHTML = recommendations.map((item) => `
      <div class="auto-review-advice auto-review-priority-${item.priority === "高" ? "high" : item.priority === "中" ? "medium" : "low"}">
        <span>${escapeHtml(item.priority || "中")}优先级</span>
        <strong>${escapeHtml(item.title || "系统建议")}</strong>
        <p>${escapeHtml(item.detail || "继续收集本地复核样本。")}</p>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无系统建议。</div>';
  }

  const reasonTarget = el("autoReviewBlockReasons");
  if (reasonTarget) {
    reasonTarget.innerHTML = reasons.map((row) => `
      <div class="auto-review-row">
        <div><strong>${escapeHtml(row.blockReason || "未知原因")}</strong><small>${escapeHtml(row.reviewPriority || "低")}优先级</small></div>
        <span>${formatNumber(row.count, 0)} 条</span>
        <span>${formatPercent(row.percentage)}</span>
        <span>${formatNumber(row.strategyCount, 0)} 个策略</span>
        <span>${formatNumber(row.symbolCount, 0)} 个币种</span>
        <em>${escapeHtml(row.recommendation || "检查阻塞原因")}</em>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无阻塞记录。</div>';
  }

  const activeTarget = el("autoReviewActiveQueue");
  if (activeTarget) {
    activeTarget.innerHTML = activeRows.map((row) => `
      <div class="auto-review-card is-active">
        <div class="auto-lifecycle-card-head"><strong>${escapeHtml(row.strategyName || "--")}</strong><span>${escapeHtml(row.status || "本地模拟持有")}</span></div>
        <small>${escapeHtml(row.symbol || "--")} · ${escapeHtml(row.direction || "未知方向")} · ${escapeHtml(row.timeframe || "--")}</small>
        <div class="artifact-metrics">
          <span>当前 ${formatReviewR(row.currentR)}</span>
          <span>距目标 ${formatReviewR(row.distanceToTargetR)}</span>
          <span>距止损 ${formatReviewR(row.distanceToStopR)}</span>
          <span>持有 ${escapeHtml(row.holdDuration || "时间未知")}</span>
        </div>
        <p>${escapeHtml(row.warning || "本地观察字段完整")}</p>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无本地模拟持有记录。</div>';
  }

  const closedTarget = el("autoReviewClosedQueue");
  if (closedTarget) {
    closedTarget.innerHTML = closedRows.map((row) => `
      <div class="auto-review-card is-closed">
        <div class="auto-lifecycle-card-head"><strong>${escapeHtml(row.strategyName || "--")}</strong><span>${escapeHtml(row.exitReason || "已结束")}</span></div>
        <small>${escapeHtml(row.symbol || "--")} · ${escapeHtml(row.direction || "未知方向")} · ${escapeHtml(row.holdDuration || "时间未知")}</small>
        <div class="artifact-metrics">
          <span>结果 ${formatReviewR(row.resultR)}</span>
          <span>最大浮盈 ${formatReviewR(row.maxFavorableR)}</span>
          <span>最大浮亏 ${formatReviewR(row.maxAdverseR)}</span>
        </div>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无闭合执行结果，请继续收集样本。</div>';
  }

  const blockedTarget = el("autoReviewBlockedQueue");
  if (blockedTarget) {
    blockedTarget.innerHTML = blockedRows.slice(0, 16).map((row) => `
      <div class="auto-review-card is-blocked">
        <div class="auto-lifecycle-card-head"><strong>${escapeHtml(row.strategyName || "--")}</strong><span>${escapeHtml(row.reviewPriority || "低")}优先级</span></div>
        <small>${escapeHtml(row.symbol || "--")} · ${escapeHtml(row.direction || "未知方向")} · ${escapeHtml(row.timeframe || "--")}</small>
        <div class="auto-review-reason"><b>${escapeHtml(row.blockReason || "未知原因")}</b><span>${escapeHtml(row.blockDetail || "现有记录未提供详细说明")}</span></div>
        <p>建议：${escapeHtml(row.recommendation || "检查阻塞原因")}</p>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无阻塞复核记录。</div>';
  }

  const strategyTarget = el("autoReviewStrategySummary");
  if (strategyTarget) {
    strategyTarget.innerHTML = strategyRows.map((row) => `
      <div class="auto-review-row strategy-row">
        <div><strong>${escapeHtml(row.strategyName || row.strategyId || "--")}</strong><small>${escapeHtml(row.suggestedStatus || "闭合样本不足")}</small></div>
        <span>总记录 ${formatNumber(row.totalRecords, 0)}</span>
        <span>活跃 ${formatNumber(row.activeHoldingCount, 0)}</span>
        <span>闭合 ${formatNumber(row.closedResultCount, 0)}</span>
        <span>阻塞 ${formatNumber(row.blockedCount, 0)} / ${formatPercent(row.blockedRatePct)}</span>
        <em>${escapeHtml(row.recommendation || "继续收集样本")}</em>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无策略生命周期汇总。</div>';
  }

  const splitTarget = el("autoReviewSplitSummary");
  if (splitTarget) {
    splitTarget.innerHTML = `
      <div class="auto-review-split-column">
        <strong>按币种</strong>
        ${symbolRows.slice(0, 8).map((row) => `<span>${escapeHtml(row.symbol || "--")}：${formatNumber(row.totalRecords, 0)} 条，阻塞 ${formatPercent(row.blockedRatePct)}</span>`).join("") || "<span>暂无币种记录</span>"}
      </div>
      <div class="auto-review-split-column">
        <strong>按方向</strong>
        ${directionRows.map((row) => `<span>${escapeHtml(row.direction || "未知方向")}：${formatNumber(row.totalRecords, 0)} 条，活跃 ${formatNumber(row.activeHoldingCount, 0)}，阻塞 ${formatPercent(row.blockedRatePct)}</span>`).join("") || "<span>暂无方向记录</span>"}
      </div>
    `;
  }
}

function renderAutoExecutionLearning(payload = {}) {
  latestAutoExecutionLearningPayload = payload || {};
  const summary = payload.summary || {};
  const strategyRows = Array.isArray(payload.byStrategy) ? payload.byStrategy : [];
  setText("autoLearningClosed", String(summary.closedSamples ?? 0));
  setText("autoLearningTp", String(summary.takeProfitCount ?? 0));
  setText("autoLearningSl", String(summary.stopLossCount ?? 0));
  setText("autoLearningExpired", String(summary.expiredCount ?? 0));
  setText("autoLearningAverageR", formatReviewR(summary.averageR));
  setText("autoLearningStage", summary.sampleStage || "等待闭合样本");
  setText("autoLearningStatus", summary.nextAction || "样本不足时只做描述性统计，不训练模型。");

  const target = el("autoLearningStrategyRows");
  if (!target) return;
  target.innerHTML = strategyRows.slice(0, 12).map((row) => `
    <div class="auto-review-row strategy-row">
      <div><strong>${escapeHtml(row.label || row.key || "--")}</strong><small>${escapeHtml(row.sampleStage || "闭合样本不足")}</small></div>
      <span>闭合 ${formatNumber(row.closedSamples, 0)}</span>
      <span>胜率 ${row.winRatePct === null || row.winRatePct === undefined ? "--" : formatPercent(row.winRatePct)}</span>
      <span>平均 ${formatReviewR(row.averageR)}</span>
      <span>PF(R) ${row.profitFactorR === null || row.profitFactorR === undefined ? "--" : formatNumber(row.profitFactorR, 2)}</span>
      <em>${escapeHtml(row.nextAction || "继续收集独立闭合样本")}</em>
    </div>
  `).join("") || '<div class="testnet-design-empty">暂无闭合样本。点击“推进本地生命周期”后开始积累。</div>';
}

function renderEvolutionDemoStatus(payload = {}) {
  const summary = payload.summary || {};
  const stages = Array.isArray(payload.stages) ? payload.stages : [];
  const blockers = Array.isArray(payload.blockers) ? payload.blockers : [];
  const records = Array.isArray(payload.recentRecords) ? payload.recentRecords : [];
  setText("evolutionDemoStatusText", summary.ready
    ? "不可变 release、运行时凭据和自动执行闸门均已就绪。"
    : "当前保持阻塞；补齐下方条件后才会自动运行 OKX Demo。",
  );
  setText("evolutionDemoReleaseCount", String(summary.eligibleReleaseCount ?? 0));
  setText("evolutionDemoRecordCount", String(summary.executionRecordCount ?? 0));
  setText("evolutionDemoEquity", `${formatNumber(summary.initialEquityUsdt, 0)} USDT`);
  setText("evolutionDemoNotional", `${formatNumber(summary.maxOrderNotionalUsdt, 0)} USDT`);
  setText("evolutionDemoRuntime", summary.killSwitch ? "Kill Switch" : summary.paused ? "已暂停" : summary.ready ? "已就绪" : "锁定");

  const stageTarget = el("evolutionDemoStages");
  if (stageTarget) {
    stageTarget.innerHTML = stages.map((stage, index) => `
      <div class="mode-flow-card ${stage.status === "available" || stage.status === "ready" ? "active" : stage.status === "locked" ? "locked" : "disabled"}">
        <span>${index + 1}</span>
        <strong>${escapeHtml(stage.label || stage.stageId || "--")}</strong>
        <small>${escapeHtml(stage.description || "--")}</small>
      </div>
    `).join("");
  }
  const blockerTarget = el("evolutionDemoBlockers");
  if (blockerTarget) {
    blockerTarget.innerHTML = blockers.map((item) => `<span>${escapeHtml(translateExchangeDemoBlocker(item))}</span>`).join("")
      || '<span class="ok">全部 Demo Release 闸门已满足；Live 仍锁定。</span>';
  }
  const recordTarget = el("evolutionDemoRecords");
  if (recordTarget) {
    recordTarget.innerHTML = records.map((record) => `
      <div class="testnet-drill-row">
        <div class="testnet-drill-row-head">
          <div><strong>${escapeHtml(record.signal?.candidateId || record.recordId || "--")}</strong><small>${escapeHtml(record.signal?.instId || "--")} · ${formatDate(record.updatedAt)}</small></div>
          <span class="badge ${record.status === "filled" ? "ok" : record.status === "unknown" || record.status === "rejected" ? "danger" : "warn"}">${escapeHtml(translateExchangeDemoStatus(record.status))}</span>
        </div>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无 OKX Demo 生命周期。只有合格 release 才会生成记录。</div>';
  }
}

function renderExchangeDemoSimulation(payload = {}) {
  if (!el("exchangeDemo")) return;
  latestExchangeDemoPayload = payload || {};
  const summary = payload.summary || {};
  const credentialStatus = payload.credentialStatus || {};
  const privateBlockers = Array.isArray(payload.privateBlockers) ? payload.privateBlockers : [];
  const orderBlockers = Array.isArray(payload.orderBlockers) ? payload.orderBlockers : [];
  const recentEvents = Array.isArray(payload.recentEvents) ? payload.recentEvents : [];
  const defaultTicket = payload.defaultTicket || {};
  const readonlySummary = payload.readonlySummary || {};
  const launcher = payload.launcher || {};
  const runbook = Array.isArray(payload.runbook) ? payload.runbook : [];
  const pipeline = payload.automationPipeline || {};
  const evolutionDemo = payload.evolutionDemo || {};
  renderEvolutionDemoStatus(evolutionDemo);

  const modeBadge = el("exchangeDemoModeBadge");
  if (modeBadge) {
    const demoEnabled = Boolean(evolutionDemo?.summary?.ready);
    modeBadge.className = `status-pill ${demoEnabled ? "warn" : "danger"}`;
    modeBadge.textContent = demoEnabled ? "Release 已就绪" : "等待 Release";
  }
  const orderGate = el("exchangeDemoOrderGate");
  if (orderGate) {
    const canSubmit = Boolean(summary.canSubmitDemoOrder);
    orderGate.className = `badge ${canSubmit ? "ok" : "warn"}`;
    orderGate.textContent = canSubmit ? "烟测可用" : "烟测关闭";
  }

  setText("exchangeDemoConnectionState", summary.demoPrivateEnabled ? "Demo 开关已开" : "默认锁定");
  setText("exchangeDemoConnectionMeta", `${summary.exchange || "OKX Demo Trading"} · ${summary.site || "global"} · ${summary.baseUrl || "--"}`);
  setText("exchangeDemoCredentialState", credentialStatus.allConfigured ? "环境变量已配置" : "凭据未完整");
  setText("exchangeDemoReadOnlyState", readonlySummary.statusLabel || (summary.canRunReadOnlyCheck ? "可检查" : "阻塞"));
  setText("exchangeDemoReadOnlyMeta", readonlySummary.nextAction || summary.nextAction || "先配置 OKX Demo 环境变量。");
  setText("exchangeDemoSmokeState", summary.connectivitySmokeReady ? "可执行" : "锁定");
  setText("exchangeDemoAutomationGateState", summary.strategyAutomationReady ? "Release 已就绪" : "等待 Release");
  setText(
    "exchangeDemoAutomationGateMeta",
    summary.strategyAutomationReady
      ? `${summary.eligibleDemoReleaseCount ?? 0} 个不可变 Release 已通过全部闸门。`
      : `当前 ${summary.eligibleDemoReleaseCount ?? 0} 个合格 Release；连接烟测不会改变该数量。`,
  );
  setText("exchangeDemoRecentMeta", `${recentEvents.length} 条事件 · 最近 ${formatDate(recentEvents[0]?.createdAt)}`);
  setText("exchangeDemoLauncherCommand", launcher.readOnlyCommand || "powershell -ExecutionPolicy Bypass -File scripts\\start_okx_demo_console.ps1");

  const blockerTarget = el("exchangeDemoBlockers");
  if (blockerTarget) {
    const blockers = Array.from(new Set([...privateBlockers, ...orderBlockers]));
    blockerTarget.innerHTML = blockers.map((item) => `<span>${escapeHtml(translateExchangeDemoBlocker(item))}</span>`).join("")
      || '<span class="ok">当前无 Demo 阻塞项；仍需人工确认才能提交订单。</span>';
  }

  const modeTarget = el("exchangeDemoModeCards");
  if (modeTarget) {
    modeTarget.innerHTML = (payload.modeCards || []).map((card, index) => `
      <div class="mode-flow-card ${card.status === "available" || card.status === "readonly_ready" ? "active" : card.status === "locked" ? "locked" : "disabled"}">
        <span>${index + 1}</span>
        <strong>${escapeHtml(card.label)}</strong>
        <small>${escapeHtml(translateExchangeDemoStatus(card.status))} · ${escapeHtml(card.description)}</small>
      </div>
    `).join("");
  }

  const runbookTarget = el("exchangeDemoRunbookList");
  if (runbookTarget) {
    runbookTarget.innerHTML = runbook.map((step) => `
      <div class="exchange-demo-runbook-step ${step.status === "ready" ? "ok" : step.status === "disabled" ? "disabled" : step.status === "blocked" ? "blocked" : "warn"}">
        <span>${escapeHtml(translateExchangeDemoStatus(step.status))}</span>
        <strong>${escapeHtml(step.label || step.stepId || "--")}</strong>
        <small>${escapeHtml(step.description || "--")}</small>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无 Demo 运行手册。</div>';
  }

  const readonlyTarget = el("exchangeDemoReadOnlyDetails");
  if (readonlyTarget) {
    const blockers = Array.isArray(readonlySummary.blockers) ? readonlySummary.blockers : [];
    readonlyTarget.innerHTML = `
      <div><span>检查时间</span><strong>${formatDate(readonlySummary.lastCheckedAt)}</strong></div>
      <div><span>账户配置接口</span><strong>${escapeHtml(readonlySummary.accountConfigStatus ?? "--")} / ${escapeHtml(readonlySummary.accountConfigCode ?? "--")}</strong></div>
      <div><span>余额接口</span><strong>${escapeHtml(readonlySummary.balanceStatus ?? "--")} / ${escapeHtml(readonlySummary.balanceCode ?? "--")}</strong></div>
      <div><span>持仓接口</span><strong>${escapeHtml(readonlySummary.positionStatus ?? "--")} / ${escapeHtml(readonlySummary.positionCode ?? "--")}</strong></div>
      <div><span>阻塞</span><strong>${blockers.length ? blockers.map(translateExchangeDemoBlocker).join(" · ") : "无"}</strong></div>
    `;
  }

  renderExchangeDemoPipeline(pipeline);

  const instInput = el("exchangeDemoInstIdInput");
  const sideInput = el("exchangeDemoSideInput");
  const tdInput = el("exchangeDemoTdModeInput");
  const ordInput = el("exchangeDemoOrdTypeInput");
  const sizeInput = el("exchangeDemoSizeInput");
  const notionalInput = el("exchangeDemoNotionalInput");
  if (instInput && !instInput.value) instInput.value = defaultTicket.instId || "BTC-USDT-SWAP";
  if (sideInput && defaultTicket.side) sideInput.value = defaultTicket.side;
  if (tdInput && defaultTicket.tdMode) tdInput.value = defaultTicket.tdMode;
  if (ordInput && defaultTicket.ordType) ordInput.value = defaultTicket.ordType;
  if (sizeInput && !sizeInput.placeholder) sizeInput.placeholder = "必须手动填写 OKX sz";
  if (notionalInput && !notionalInput.value) notionalInput.value = String(defaultTicket.notionalUsdt || summary.maxNotionalUsdt || 250);

  const eventsTarget = el("exchangeDemoRecentEvents");
  if (eventsTarget) {
    eventsTarget.innerHTML = recentEvents.map((event) => {
      const blockers = Array.isArray(event.blockers) ? event.blockers : [];
      return `
        <div class="testnet-drill-row">
          <div class="testnet-drill-row-head">
            <div>
              <strong>${escapeHtml(event.eventType || "--")}</strong>
              <small>${escapeHtml(event.instId || "OKX Demo")} · ${formatDate(event.createdAt)}</small>
            </div>
            <span class="badge ${event.status === "passed" || event.status === "submitted" || event.status === "local_drill_saved" ? "ok" : event.status === "blocked" ? "warn" : "danger"}">${escapeHtml(translateExchangeDemoStatus(event.status))}</span>
          </div>
          <div class="artifact-metrics">
            <span>方向 ${escapeHtml(event.side || "--")}</span>
            <span>金额 ${formatNumber(event.notionalUsdt, 2)} USDT</span>
            <span>订单 ${escapeHtml(event.clientOrderId || event.ordId || "--")}</span>
            ${event.executionPurpose === "connectivity_smoke_only" ? "<span>用途 连接烟测（非策略证据）</span>" : ""}
          </div>
          ${blockers.length ? `<div class="sandbox-lane-next">${blockers.map((item) => escapeHtml(translateExchangeDemoBlocker(item))).join(" · ")}</div>` : ""}
        </div>
      `;
    }).join("") || '<div class="testnet-design-empty">暂无 OKX Demo 事件。先做只读检查或本地紧急停止演练。</div>';
  }
}

function renderSandboxSimulationLane(observationTasks, qualityRows) {
  if (!el("learningSandboxLaneList")) return;
  const rows = buildSandboxSimulationRows(observationTasks, qualityRows);
  const totalCapital = rows.reduce((sum, row) => sum + row.capital, 0);
  const totalEquity = rows.reduce((sum, row) => sum + row.equity, 0);
  const closedSamples = rows.reduce((sum, row) => sum + row.closedPaperSampleCount, 0);
  const signalCount = rows.reduce((sum, row) => sum + row.signalObservedCount, 0);
  el("learningSandboxStatus").textContent = "本地虚拟运行";
  el("learningSandboxStrategyCount").textContent = String(rows.length);
  el("learningSandboxActiveCount").textContent = String(rows.length);
  el("learningSandboxCapitalTotal").textContent = formatUsd(totalCapital);
  el("learningSandboxEquityTotal").textContent = formatUsd(totalEquity);
  el("learningSandboxClosedSamples").textContent = String(closedSamples);
  el("learningSandboxSignalCount").textContent = String(signalCount);
  el("learningSandboxNextAction").textContent =
    `全部候选策略先进入本地沙盒；每条策略虚拟本金 ${formatUsd(sandboxSimulationSettings.virtualCapitalPerStrategy)}，继续补信号、闭合样本和结果 R。`;

  el("learningSandboxLaneList").innerHTML = rows.map((row) => {
    const metrics = row.historicalMetrics || {};
    return `
      <div class="sandbox-lane-row">
        <div class="sandbox-lane-row-head">
          <div>
            <strong>${escapeHtml(row.title)}</strong>
            <small>${escapeHtml(row.taskId || "--")} · 最近 ${formatDate(row.latestLogAt)}</small>
          </div>
          <span class="badge ${row.tone}">${escapeHtml(row.statusLabel)}</span>
        </div>
        <div class="artifact-metrics">
          <span>本金 ${formatUsd(row.capital)}</span>
          <span>权益 ${formatUsd(row.equity)}</span>
          <span>浮动 ${formatUsd(row.pnl, 2)}</span>
          <span>累计 ${formatNumber(row.realizedR, 2)}R</span>
          <span>闭合 ${row.closedPaperSampleCount}</span>
          <span>规则 ${row.ruleMatchedCount}</span>
        </div>
        <div class="artifact-metrics">
          <span>观察币种 ${escapeHtml(row.pair || "--")}</span>
          <span>周期 ${escapeHtml(row.timeframe || "--")}</span>
          <span>数据状态 ${escapeHtml(row.dataStatus || "等待")}</span>
          <span>数据模式 ${escapeHtml(row.dataMode || "本地沙盒")}</span>
        </div>
        <div class="artifact-metrics">
          <span>历史样本 ${metrics.tradeCount ?? "--"}</span>
          <span>历史胜率 ${formatPercent(metrics.winRatePct)}</span>
          <span>历史 PF ${formatNumber(metrics.profitFactor)}</span>
          <span>历史回撤 ${formatPercent(metrics.maxDrawdownPct)}</span>
        </div>
        <div class="sandbox-lane-next">${escapeHtml(row.nextAction)}</div>
      </div>
    `;
  }).join("") || '<div class="sandbox-lane-empty">暂无可运行的本地沙盒策略。</div>';
}

function updateLocalSandboxRunButton(enabled, runnerStatus = "") {
  ["runLocalSandboxButton", "localLabRunSandboxButton"].forEach((buttonId) => {
    const button = el(buttonId);
    if (!button) return;
    button.classList.toggle("is-running", Boolean(enabled));
    button.dataset.running = enabled ? "true" : "false";
    button.textContent = enabled ? "沙盒运行中 · 点击停止" : "运行本地沙盒";
    button.title = enabled
      ? `本地沙盒正在持续观察，当前状态：${runnerStatus || "waiting"}。点击后停止自动观察。`
      : "点击后开启本地沙盒持续观察，并立即运行一轮。";
  });
}

async function runLocalSandboxNow() {
  const button = el("runLocalSandboxButton");
  const status = el("learningSandboxRunStatus");
  if (!button || !status) return;
  const isRunning = button.dataset.running === "true" || Boolean(el("sandboxAutoEnabledInput")?.checked);
  button.disabled = true;
  try {
    if (isRunning) {
      status.textContent = "正在停止本地沙盒持续观察...";
      await postJson("/api/local-sandbox/auto-runner", {
        enabled: false,
        intervalMinutes: Number(el("sandboxAutoIntervalInput")?.value || 5),
        maxRunsPerDay: Number(el("sandboxAutoMaxRunsInput")?.value || 288),
      });
      if (el("sandboxAutoEnabledInput")) el("sandboxAutoEnabledInput").checked = false;
      updateLocalSandboxRunButton(false, "disabled");
      await refreshAll();
      status.textContent = "已停止本地沙盒持续观察。再次点击按钮会重新开启并立即运行一轮。";
      return;
    }

    status.textContent = "正在开启 5 分钟本地沙盒持续观察，并立即运行一轮...";
    await postJson("/api/local-sandbox/auto-runner", {
      enabled: true,
      intervalMinutes: 5,
      maxRunsPerDay: 288,
    });
    if (el("sandboxAutoEnabledInput")) el("sandboxAutoEnabledInput").checked = true;
    if (el("sandboxAutoIntervalInput")) el("sandboxAutoIntervalInput").value = "5";
    if (el("sandboxAutoMaxRunsInput")) el("sandboxAutoMaxRunsInput").value = "288";
    updateLocalSandboxRunButton(true, "running");
    const response = await postJson("/api/local-sandbox/auto-runner/run-now", {});
    const run = response.localSandboxRun || {};
    await refreshAll();
    status.textContent =
      `已开启持续观察：每 5 分钟检查一次。本次新增 ${run.generatedLogCount ?? 0} 条观察，闭合 ${run.closedSampleCount ?? 0} 个样本，跳过重复 ${run.skippedDuplicateCount ?? 0} 个，数据缺口 ${run.dataGapCount ?? 0}。`;
  } catch (error) {
    status.textContent = `本地沙盒操作失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
}
function renderSandboxDailyReport(payload) {
  if (!el("learningSandboxDailyList")) return;
  const report = payload?.latestReport || payload?.localSandboxDailyReport || {};
  const summary = report.summary || {};
  const rows = Array.isArray(report.strategyHealthRows) ? report.strategyHealthRows : [];
  el("learningSandboxDailyDate").textContent = report.dateKey || "--";
  el("learningSandboxDailyLogs").textContent = String(summary.dailyLogCount ?? "--");
  el("learningSandboxDailyClosed").textContent = String(summary.dailyClosedSampleCount ?? "--");
  el("learningSandboxAverageHealth").textContent = summary.averageHealthScore !== undefined
    ? formatNumber(summary.averageHealthScore, 0)
    : "--";
  el("learningSandboxImprovingCount").textContent = String(summary.improvingCount ?? "--");
  el("learningSandboxDecliningCount").textContent = String(summary.decliningCount ?? "--");
  el("learningSandboxDailyStatus").textContent = rows.length ? "本地复盘" : "等待日报";
  el("learningSandboxDailyRunStatus").textContent = rows.length
    ? `最近日报：${formatDate(report.generatedAt)} · ${summary.nextAction || "继续观察。"}`
    : "还没有沙盒日报，点击生成后会读取本地虚拟观察日志。";

  el("learningSandboxDailyList").innerHTML = rows.map((row) => {
    const trend = row.trend || {};
    const trendTone = trend.direction === "up" ? "ok" : trend.direction === "down" ? "danger" : "warn";
    return `
      <div class="sandbox-daily-row">
        <div class="sandbox-lane-row-head">
          <div>
            <strong>${escapeHtml(row.title || row.taskId || "--")}</strong>
            <small>${escapeHtml(row.taskId || "--")} · 最近 ${formatDate(row.latestLogAt)}</small>
          </div>
          <span class="badge ${row.healthTone || "warn"}">${escapeHtml(row.healthStatusLabel || "--")} · ${formatNumber(row.healthScore, 0)}分</span>
        </div>
        <div class="artifact-metrics">
          <span>趋势 <b class="text-${trendTone}">${escapeHtml(trend.label || "--")} ${formatNumber(trend.delta || 0, 1)}</b></span>
          <span>累计 ${formatNumber(row.totalR, 2)}R</span>
          <span>今日 ${formatNumber(row.dailyR, 2)}R</span>
          <span>闭合 ${row.closedPaperSampleCount ?? 0}</span>
          <span>胜/负 ${row.winCount ?? 0}/${row.lossCount ?? 0}</span>
          <span>权益 ${formatUsd(row.virtualEquity || row.virtualCapital || 0)}</span>
        </div>
        <div class="sandbox-lane-next">${escapeHtml(row.nextAction || "继续本地沙盒观察。")}</div>
      </div>
    `;
  }).join("") || '<div class="sandbox-lane-empty">暂无沙盒日报。点击“生成沙盒日报”后会汇总本地虚拟观察日志。</div>';
}

async function buildSandboxDailyReportNow() {
  const button = el("buildSandboxDailyReportButton");
  const status = el("learningSandboxDailyRunStatus");
  if (!button || !status) return;
  button.disabled = true;
  status.textContent = "正在汇总本地沙盒日报...";
  try {
    const response = await postJson("/api/local-sandbox/build-daily-report", {});
    await refreshAll();
    status.textContent = `已生成沙盒日报：${response.localSandboxDailyReport?.summary?.dailyLogCount ?? 0} 条今日日志。`;
  } catch (error) {
    status.textContent = `日报生成失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function renderSandboxAutoRunner(payload) {
  if (!el("learningSandboxAutoStatus")) return;
  const runner = payload?.autoRunner || {};
  const events = Array.isArray(payload?.events) ? payload.events : [];
  const learningSnapshots = Array.isArray(payload?.learningSnapshots) ? payload.learningSnapshots : [];
  const latestLearning = learningSnapshots[0] || {};
  const enabled = Boolean(runner.enabled);
  const statusText = enabled
    ? runner.status === "running"
      ? "运行中"
      : runner.status === "waiting_for_candidates"
        ? "等待新策略"
      : runner.status === "daily_limit_reached"
        ? "今日上限"
        : "已开启"
    : "未开启";
  el("learningSandboxAutoStatus").textContent = statusText;
  el("learningSandboxAutoStatus").className = `status-pill ${enabled ? "ok" : "warn"}`;
  updateLocalSandboxRunButton(enabled, runner.status || "");
  el("learningSandboxAutoEnabled").textContent = enabled ? "开启" : "关闭";
  el("learningSandboxAutoInterval").textContent = `${runner.intervalMinutes ?? "--"} 分钟`;
  el("learningSandboxAutoToday").textContent = `${runner.todayRunCount ?? 0}/${runner.maxRunsPerDay ?? "--"}`;
  el("learningSandboxAutoNext").textContent = runner.nextRunAt ? formatDate(runner.nextRunAt) : "--";
  el("learningSandboxAutoFailures").textContent = String(runner.consecutiveFailures ?? 0);
  if (el("learningSandboxReplayCursor")) {
    const replayCursor = runner.replayCursor ?? runner.lastReplayCursor;
    const replayWindowCount = runner.lastReplayWindowCount ?? 0;
    el("learningSandboxReplayCursor").textContent = replayCursor !== undefined && replayCursor !== null
      ? `${replayCursor} / ${replayWindowCount || "--"}窗`
      : "--";
  }
  el("learningSandboxMlStatus").textContent = latestLearning.mlReadiness === "ready_for_baseline_model"
    ? "可做基线模型"
    : "继续收集";
  el("sandboxAutoEnabledInput").checked = enabled;
  el("sandboxAutoIntervalInput").value = String(runner.intervalMinutes || 5);
  el("sandboxAutoMaxRunsInput").value = String(runner.maxRunsPerDay || 288);
  const learningText = latestLearning.closedSampleCount !== undefined
    ? `学习样本：${latestLearning.closedSampleCount}/${latestLearning.minimumBaselineModelSamples || 100} 个闭合样本；${latestLearning.nextAction || "继续收集本地观察数据。"}`
    : "学习样本：等待自动沙盒生成。";
  el("learningSandboxAutoAction").textContent = runner.lastError
    ? `最近错误：${runner.lastError}`
    : `${enabled ? "自动沙盒已开启" : "自动沙盒未开启"}；上次运行 ${runner.lastRunAt ? formatDate(runner.lastRunAt) : "--"}。${learningText}`;
  el("learningSandboxAutoEvents").innerHTML = events.slice(0, 8).map((event) => `
    <div class="sandbox-daily-row compact">
      <div class="sandbox-lane-row-head">
        <div>
          <strong>${escapeHtml(event.eventType || "--")}</strong>
          <small>${formatDate(event.createdAt)} · ${escapeHtml(event.reason || event.status || "")}</small>
        </div>
        <span class="badge ${event.error ? "danger" : "ok"}">${event.generatedLogCount ?? event.closedSampleCount ?? "local"}</span>
      </div>
      <div class="artifact-metrics">
        <span>run ${escapeHtml(event.runId || "--")}</span>
        <span>report ${escapeHtml(event.reportId || "--")}</span>
        <span>learning ${escapeHtml(event.learningSnapshotId || "--")}</span>
        <span>replay ${escapeHtml(event.replayCursor || "--")} / ${escapeHtml(event.replayWindowCount || "--")}窗</span>
      </div>
    </div>
  `).join("") || '<div class="sandbox-lane-empty">暂无自动沙盒运行记录。</div>';
}

function liveReadinessBadge(row) {
  const tone = row?.tone || "warn";
  return `<span class="badge ${tone}">${escapeHtml(row?.statusLabel || "--")} · ${formatNumber(row?.readinessScore, 0)}分</span>`;
}

function renderLiveReadiness(payload) {
  if (!el("liveReadinessList")) return;
  const summary = payload?.summary || {};
  const rows = Array.isArray(payload?.rows) ? payload.rows : [];
  const tickets = Array.isArray(payload?.tickets) ? payload.tickets : [];
  const thresholds = payload?.thresholds || {};
  el("liveCandidateCount").textContent = String(summary.candidateCount ?? rows.length ?? 0);
  el("liveManualReadyCount").textContent = String(summary.manualTicketReadyCount ?? 0);
  el("liveShadowCount").textContent = String(summary.shadowObservationCount ?? 0);
  el("liveBlockedCount").textContent = String(summary.blockedForReviewCount ?? 0);
  el("liveTicketCount").textContent = String(summary.ticketCount ?? tickets.length ?? 0);
  el("liveReviewDate").textContent = payload?.reviewDateLabel || "--";
  el("liveReadinessStatus").textContent = summary.manualTicketReadyCount > 0 ? "可人工复核" : "继续观察";
  el("liveReadinessStatus").className = `status-pill ${summary.manualTicketReadyCount > 0 ? "warn" : "danger"}`;
  el("liveReadinessNextAction").textContent = summary.nextAction || "等待前向观察和本地样本闭合；未通过前不进入实盘。";

  el("liveReadinessList").innerHTML = rows.map((row) => {
    const metrics = row.metrics || {};
    const quality = row.quality || {};
    const blockers = Array.isArray(row.blockers) ? row.blockers : [];
    const passed = Array.isArray(row.passedChecks) ? row.passedChecks : [];
    const buttonDisabled = row.manualTicketAllowed ? "" : "disabled";
    const buttonLabel = row.manualTicketAllowed ? "生成复核票据" : "未达门槛";
    return `
      <div class="live-readiness-row">
        <div class="live-readiness-row-head">
          <div>
            <strong>${escapeHtml(row.title || row.taskId || "--")}</strong>
            <small>${escapeHtml(row.taskId || "--")} · ${escapeHtml(row.timeframe || "--")} · 最近 ${formatDate(quality.latestLogAt)}</small>
          </div>
          ${liveReadinessBadge(row)}
        </div>
        <div class="artifact-metrics">
          <span>样本 ${metrics.tradeCount ?? metrics.filledSignalCount ?? "--"}/${thresholds.minHistoricalTrades ?? "--"}</span>
          <span>胜率 ${formatPercent(metrics.winRatePct)}</span>
          <span>PF ${formatNumber(metrics.profitFactor)}</span>
          <span>盈亏比 ${formatNumber(metrics.rewardRiskRatio || metrics.targetRewardRiskRatio)}</span>
          <span>回撤 ${formatPercent(metrics.maxDrawdownPct)}</span>
          <span>质量 ${formatNumber(quality.qualityScore, 0)}</span>
          <span>日志 ${quality.logCount ?? 0}</span>
          <span>规则 ${quality.ruleMatchedCount ?? 0}</span>
          <span>闭合 ${quality.closedPaperSampleCount ?? 0}</span>
        </div>
        <div class="live-readiness-blockers">
          ${(blockers.length ? blockers : ["暂无阻塞项，但仍需人工复核"])
            .slice(0, 8)
            .map((item) => `<small>${escapeHtml(item)}</small>`)
            .join("")}
        </div>
        <details class="live-readiness-checks">
          <summary>门槛检查详情</summary>
          <div>
            <strong>已通过</strong>
            ${(passed.length ? passed : ["暂无通过项"])
              .map((item) => `<small>${escapeHtml(item)}</small>`)
              .join("")}
          </div>
          <div>
            <strong>硬阻塞</strong>
            ${(row.hardExecutionBlockers || [])
              .map((item) => `<small>${escapeHtml(item)}</small>`)
              .join("")}
          </div>
        </details>
        <div class="live-readiness-ticket-line">
          <span>${escapeHtml(row.nextAction || "继续观察，不自动进入实盘。")}</span>
          <button type="button" data-live-ticket="${escapeHtml(row.taskId || "")}" ${buttonDisabled}>${buttonLabel}</button>
        </div>
      </div>
    `;
  }).join("") || '<div class="live-readiness-empty">暂无可复核策略；请先导入 Quant Engine 报告并运行本地沙盒。</div>';

  el("liveTicketList").innerHTML = tickets.slice(0, 10).map((ticket) => `
    <div class="live-ticket-row">
      <strong>${escapeHtml(ticket.title || ticket.taskId || "--")}</strong>
      <small>${formatDate(ticket.createdAt)} · ${escapeHtml(ticket.status || "draft_manual_review")}</small>
      <div class="artifact-metrics">
        <span>分数 ${formatNumber(ticket.readinessScore, 0)}</span>
        <span>周期 ${escapeHtml(ticket.timeframe || "--")}</span>
        <span>币种 ${escapeHtml(ticket.selectedPair || "待选择")}</span>
      </div>
      <div>这只是人工复核票据，不会自动连接交易所或创建订单。</div>
    </div>
  `).join("") || '<div class="live-readiness-empty">暂无人工复核票据。</div>';

  el("liveReadinessList").querySelectorAll("[data-live-ticket]").forEach((button) => {
    button.addEventListener("click", async () => {
      const taskId = button.getAttribute("data-live-ticket") || "";
      button.disabled = true;
      try {
        await postJson("/api/manual-execution-ticket", {
          taskId,
          note: "人工复核票据，仅用于记录，不自动下单。",
        });
        await refreshAll();
      } catch (error) {
        el("liveReadinessNextAction").textContent = `票据保存失败：${error.message}。请稍后重试。`;
      } finally {
        button.disabled = false;
      }
    });
  });
}

function liveCandidateApprovalLabel(status) {
  const labels = {
    awaiting_manual_approval: "等待人工批准",
    approved_for_future_release_review: "已批准未来发布复核",
    revoked: "已撤销",
    checksum_changed_approval_invalid: "checksum 已变化，原批准失效",
  };
  return labels[status] || status || "等待人工批准";
}

function getSelectedLiveCandidate(payload = latestLiveCandidatePayload) {
  const packages = Array.isArray(payload?.packages) ? payload.packages : [];
  return packages.find((item) => item.liveCandidatePackageId === selectedLiveCandidatePackageId) || packages[0] || null;
}

function renderLiveCandidateStatus(payload) {
  if (!el("liveCandidateList")) return;
  latestLiveCandidatePayload = payload || {};
  const summary = latestLiveCandidatePayload.summary || {};
  const packages = Array.isArray(latestLiveCandidatePayload.packages) ? latestLiveCandidatePayload.packages : [];
  if (!packages.some((item) => item.liveCandidatePackageId === selectedLiveCandidatePackageId)) {
    selectedLiveCandidatePackageId = packages[0]?.liveCandidatePackageId || null;
  }
  const selected = getSelectedLiveCandidate(latestLiveCandidatePayload);
  setText("liveCandidatePackageCount", String(summary.packageCount ?? packages.length));
  setText("liveCandidateAwaitingCount", String(summary.awaitingApprovalCount ?? 0));
  setText("liveCandidateApprovedCount", String(summary.approvedForFutureReviewCount ?? 0));
  setText(
    "liveCandidateStatusText",
    packages.length
      ? `已读取 ${packages.length} 个不可变候选包；批准不会开启执行。`
      : "暂无通过 Demo 硬门槛的 Live Candidate，实盘保持锁定。",
  );
  el("liveCandidateList").innerHTML = packages.map((item) => {
    const packageData = item.package || {};
    const evidence = packageData.demoEvidence || {};
    const risk = packageData.proposedRiskBudget || {};
    const approval = item.approval || {};
    const selectedClass = item.liveCandidatePackageId === selectedLiveCandidatePackageId ? " is-selected" : "";
    return `
      <button class="live-candidate-row${selectedClass}" type="button" data-live-package="${escapeHtml(item.liveCandidatePackageId)}">
        <div class="live-readiness-row-head">
          <div>
            <strong>${escapeHtml(packageData.strategy?.name || packageData.strategyCandidateId || item.liveCandidatePackageId)}</strong>
            <small>${escapeHtml(item.demoReleaseId || "--")} · checksum ${escapeHtml(String(item.packageHash || "").slice(0, 12))}</small>
          </div>
          <span class="badge ${approval.status === "approved_for_future_release_review" ? "ok" : approval.status === "revoked" ? "danger" : "warn"}">${escapeHtml(liveCandidateApprovalLabel(approval.status))}</span>
        </div>
        <div class="artifact-metrics">
          <span>Demo 平仓 ${evidence.demoClosedTrades ?? "--"}</span>
          <span>观察 ${evidence.demoCalendarDays ?? "--"} 天</span>
          <span>PF ${formatNumber(evidence.netProfitFactor)}</span>
          <span>回撤 ${formatPercent(evidence.maxDrawdownPercent)}</span>
          <span>资金上限 ${formatUsd(risk.capitalLimitUsdt)}</span>
          <span>单笔风险 ${formatPercent(risk.riskPerTradePercent)}</span>
        </div>
        <small>最多 ${risk.maxConcurrentPositions ?? "--"} 个持仓 · 最大 ${risk.maxLeverage ?? "--"}x · 单笔名义 ${formatUsd(risk.maxOrderNotionalUsdt)} · 执行仍为关闭</small>
      </button>
    `;
  }).join("") || '<div class="sandbox-lane-empty">暂无候选包。需要先完成真实 Demo 样本、漂移复核、账本与 checksum 硬门槛，不能人工绕过。</div>';
  el("approveLiveCandidateButton").disabled = !selected || selected.approval?.status === "approved_for_future_release_review";
  el("revokeLiveCandidateButton").disabled = !selected || selected.approval?.status !== "approved_for_future_release_review";
  document.querySelectorAll("[data-live-package]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedLiveCandidatePackageId = button.getAttribute("data-live-package");
      renderLiveCandidateStatus(latestLiveCandidatePayload);
    });
  });
}

function selectedRiskProfile() {
  const profiles = Array.isArray(latestRiskProfilePayload?.profiles) ? latestRiskProfilePayload.profiles : [];
  return profiles.find((item) => item.riskProfileId === selectedRiskProfileId) || null;
}

function fillRiskProfileForm(record) {
  const profile = record?.profile || {};
  const values = {
    riskProfileName: profile.name || record?.name || "",
    riskCapitalLimit: profile.capitalLimitUsdt,
    riskMaxStrategies: profile.maxActiveStrategies,
    riskMaxPositions: profile.maxConcurrentPositions,
    riskMaxPositionsPerStrategy: profile.maxPositionsPerStrategy,
    riskMaxPositionsPerSymbol: profile.maxPositionsPerSymbol,
    riskMaxNotional: profile.maxOrderNotionalUsdt,
    riskMaxLeverage: profile.maxLeverage,
    riskPerTrade: profile.riskPerTradePercent,
    riskMaxOpen: profile.maxOpenRiskPercent,
    riskDailyStop: profile.dailyLossStopPercent,
    riskDrawdownStop: profile.maxDrawdownStopPercent,
    riskCanaryStop: profile.canaryLossStopUsdt,
  };
  Object.entries(values).forEach(([id, value]) => {
    if (el(id)) el(id).value = value ?? "";
  });
  if (el("riskAllowEntries")) el("riskAllowEntries").checked = profile.allowNewEntries === true;
}

function renderRiskProfiles(payload = {}) {
  if (!el("riskProfileSelector")) return;
  latestRiskProfilePayload = payload || {};
  const environment = el("riskProfileEnvironment")?.value || "live_canary";
  const profiles = (Array.isArray(payload.profiles) ? payload.profiles : [])
    .filter((item) => item.environment === environment);
  const active = payload.activeProfiles?.[environment] || null;
  if (!profiles.some((item) => item.riskProfileId === selectedRiskProfileId)) {
    selectedRiskProfileId = active?.riskProfileId || profiles[profiles.length - 1]?.riskProfileId || null;
  }
  el("riskProfileSelector").innerHTML = profiles.map((item) => `
    <option value="${escapeHtml(item.riskProfileId)}" ${item.riskProfileId === selectedRiskProfileId ? "selected" : ""}>
      ${escapeHtml(item.name)} · v${item.version}${item.riskProfileId === active?.riskProfileId ? " · 当前" : ""}
    </option>
  `).join("");
  const selected = selectedRiskProfile();
  fillRiskProfileForm(selected);
  const isActive = Boolean(selected && selected.riskProfileId === active?.riskProfileId);
  setText(
    "riskProfileMeta",
    active
      ? `当前 ${active.name} v${active.version} · hash ${String(active.contentHash || "").slice(0, 12)} · 修改不直接开启交易。`
      : "当前环境没有已启用配置，运行保持失败关闭。",
  );
  setText("riskProfileVersionBadge", selected ? `v${selected.version}${isActive ? " · 当前" : " · 草稿"}` : "无配置");
  el("riskProfileVersionBadge").className = `badge ${isActive ? "ok" : "neutral"}`;
  el("activateRiskProfileButton").disabled = !selected || isActive;
  el("saveRiskProfileButton").disabled = !selected;
}

function translateLiveCanaryBlocker(value) {
  const labels = {
    live_master_gate_disabled: "Live 主开关关闭",
    live_read_gate_disabled: "只读门关闭",
    live_canary_gate_disabled: "Canary 门关闭",
    live_order_gate_disabled: "订单门关闭",
    live_runtime_credentials_missing: "本次进程凭据缺失",
    no_approved_live_release: "没有人工批准的 LiveRelease",
    no_active_live_canary_risk_profile: "没有启用 Live Canary 风险配置",
    live_release_risk_profile_mismatch: "Release 与风险配置 hash 不匹配",
    live_kill_switch_active: "紧急停止已激活",
    live_entries_paused: "新开仓已暂停",
    live_reconciliation_not_confirmed: "账户对账未确认",
  };
  return labels[value] || value || "未知阻塞项";
}

function renderLiveCanary(payload = {}) {
  if (!el("liveCanaryHeaderBadge")) return;
  latestLiveCanaryPayload = payload || {};
  const summary = payload.summary || {};
  const gates = payload.runtimeGates || {};
  const runtime = payload.runtime || {};
  const releases = payload.liveReleases?.summary || {};
  const blockers = Array.isArray(payload.blockers) ? payload.blockers : [];
  const livePositions = Array.isArray(payload?.portfolioSnapshot?.positions)
    ? payload.portfolioSnapshot.positions
    : (Array.isArray(payload.positions) ? payload.positions : (Array.isArray(runtime.positions) ? runtime.positions : []));
  const processGateCount = [gates.masterEnabled, gates.readEnabled, gates.canaryEnabled, gates.orderEnabled].filter(Boolean).length;
  const ready = Boolean(summary.canaryOrderReady);
  setText("liveCanaryHeaderBadge", ready ? "Canary 已就绪" : "Canary 未就绪");
  el("liveCanaryHeaderBadge").className = `status-pill ${ready ? "ok" : "danger"}`;
  setText("topLiveStatus", ready ? "Canary 已就绪" : "实盘默认关闭");
  el("topLiveStatus").className = `status-pill ${ready ? "ok" : "danger"}`;
  setText("railModeStatus", ready ? "研究 + Demo 执行 · Canary 已就绪" : "研究 + Demo 执行 · 实盘默认关闭");
  setText("liveCanaryAdapterBadge", ready ? "适配器可执行" : "适配器已锁定");
  el("liveCanaryAdapterBadge").className = `badge ${ready ? "ok" : "warn"}`;
  setText("liveCanaryHeadline", ready
    ? "Live Canary 的 release、RiskProfile、对账、进程门和人工 ARM 已通过。"
    : `Live 适配器已安装但仍有 ${blockers.length} 项阻塞；当前不会创建实盘订单。`);
  setText("liveCanaryProcessGate", `${processGateCount}/4`);
  setText("liveCanaryReleaseCount", releases.approvedLiveReleaseCount ?? 0);
  setText("liveCanaryProfileState", summary.activeRiskProfileMatched ? "匹配" : "未匹配");
  setText("liveCanaryReconcileState", runtime.lastReconciliationMatched ? "已匹配" : "未确认");
  setText("liveCanaryKillState", runtime.killSwitchActive ? "已停止" : (runtime.paused ? "已暂停" : "未激活"));
  setText("liveCanaryOrderReady", ready ? "是" : "否");
  setText("liveAdapterCount", payload.safetyBoundary?.liveAdapterPresent ? 1 : 0);
  const liveIssues = collectLiveIssues(payload);
  const liveIssueKey = liveIssues[0]?.key || "";
  el("liveCanaryBlockers").innerHTML = blockers.length
    ? `${blockers.map((item) => `<span>${escapeHtml(translateLiveCanaryBlocker(item))}</span>`).join("")}${liveIssueKey ? `<button type="button" class="secondary" data-issue-guidance-key="${escapeHtml(liveIssueKey)}">查看处理办法</button>` : ""}`
    : '<span class="ok">全部运行门已通过</span>';
  if (el("liveCompactExecutionPositions")) {
    el("liveCompactExecutionPositions").innerHTML = renderCompactExecutionPositions(livePositions, {
      title: "当前实盘持仓",
      emptyText: "当前没有实盘持仓；实盘执行仍由 Canary 闸门控制。",
    });
  }
  registerPageIssues("liveTradingPage", liveIssues);
}

function translateExecutionOutcomeQuarantine(reason) {
  const labels = {
    position_close_evidence_missing: "开仓已成交，但缺少平仓证据",
    execution_did_not_create_trade_outcome: "执行未形成完整交易结果",
    execution_not_terminal: "执行尚未进入终态",
  };
  return labels[reason] || reason || "结果证据不完整";
}

function renderExecutionOutcomes(payload = {}) {
  if (!el("executionOutcomeFormalCount")) return;
  const summary = payload.summary || {};
  const formalCount = Number(summary.formalClosedOutcomeCount || 0);
  const quarantined = Array.isArray(payload.quarantinedExecutionRecords)
    ? payload.quarantinedExecutionRecords
    : [];
  setText("executionOutcomeFormalCount", formalCount);
  setText("executionOutcomeDemoCount", summary.okxDemoOutcomeCount ?? 0);
  setText("executionOutcomeLiveCount", summary.liveOutcomeCount ?? 0);
  setText("executionOutcomeQuarantineCount", summary.quarantinedExecutionCount ?? quarantined.length);
  setText("executionOutcomeBadge", formalCount > 0 ? "已有正式闭环证据" : "暂无正式结果");
  el("executionOutcomeBadge").className = `badge ${formalCount > 0 ? "ok" : "neutral"}`;
  const exportPath = payload.latestExportPath || payload.exportPath || latestExecutionOutcomeExportPath;
  if (exportPath) latestExecutionOutcomeExportPath = exportPath;
  setText(
    "executionOutcomeExportPath",
    exportPath ? `最新导出：${exportPath}` : "尚未生成导出文件。",
  );
  el("executionOutcomeQuarantineList").innerHTML = quarantined.length
    ? quarantined.slice(0, 6).map((item) => `
        <span>${escapeHtml(item.environment || "--")} · ${escapeHtml(item.sourceRecordId || "--")} · ${escapeHtml(translateExecutionOutcomeQuarantine(item.reason))}</span>
      `).join("")
    : '<span class="ok">当前没有待隔离的执行记录</span>';
}

async function exportExecutionOutcomes() {
  const button = el("exportExecutionOutcomesButton");
  if (!button) return;
  button.disabled = true;
  setText("executionOutcomeActionStatus", "正在导出已闭合且可对账的本地执行证据；未平仓记录会继续隔离。");
  try {
    const response = await postJson("/api/execution-outcomes/export", {});
    latestCoreConsolePayload = {
      ...latestCoreConsolePayload,
      executionOutcomes: response.executionOutcomes || {},
    };
    renderExecutionOutcomes(response.executionOutcomes || {});
    setText("executionOutcomeActionStatus", "闭环证据已导出。此操作不会触发模型在线更新、策略晋级或订单。");
  } catch (error) {
    setText("executionOutcomeActionStatus", `闭环证据导出失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

function riskProfileFormPayload() {
  const selected = selectedRiskProfile();
  if (!selected) throw new Error("请先选择一个风险配置版本");
  const base = selected.profile || {};
  const number = (id) => Number(el(id)?.value);
  const maxOpenRisk = number("riskMaxOpen");
  return {
    baseRiskProfileId: selected.riskProfileId,
    profile: {
      ...base,
      profileKey: base.profileKey || selected.profileKey,
      name: el("riskProfileName")?.value?.trim() || selected.name,
      environment: el("riskProfileEnvironment")?.value || selected.environment,
      capitalLimitUsdt: number("riskCapitalLimit"),
      maxActiveStrategies: number("riskMaxStrategies"),
      maxConcurrentPositions: number("riskMaxPositions"),
      maxPositionsPerStrategy: number("riskMaxPositionsPerStrategy"),
      maxPositionsPerSymbol: number("riskMaxPositionsPerSymbol"),
      maxOrderNotionalUsdt: number("riskMaxNotional"),
      maxLeverage: number("riskMaxLeverage"),
      riskPerTradePercent: number("riskPerTrade"),
      maxOpenRiskPercent: maxOpenRisk,
      maxStrategyOpenRiskPercent: Math.min(Number(base.maxStrategyOpenRiskPercent || maxOpenRisk), maxOpenRisk),
      maxSymbolOpenRiskPercent: Math.min(Number(base.maxSymbolOpenRiskPercent || maxOpenRisk), maxOpenRisk),
      maxDirectionOpenRiskPercent: Math.min(Number(base.maxDirectionOpenRiskPercent || maxOpenRisk), maxOpenRisk),
      maxCorrelatedOpenRiskPercent: Math.min(Number(base.maxCorrelatedOpenRiskPercent || maxOpenRisk), maxOpenRisk),
      dailyLossStopPercent: number("riskDailyStop"),
      maxDrawdownStopPercent: number("riskDrawdownStop"),
      canaryLossStopUsdt: number("riskCanaryStop"),
      allowNewEntries: Boolean(el("riskAllowEntries")?.checked),
    },
  };
}

async function saveRiskProfileVersion() {
  const button = el("saveRiskProfileButton");
  button.disabled = true;
  setText("riskProfileActionStatus", "正在校验并保存不可变新版本；不会开启交易。");
  try {
    const response = await postJson("/api/risk-profiles/create", riskProfileFormPayload());
    selectedRiskProfileId = response.createdProfile?.riskProfileId || null;
    renderRiskProfiles(response.riskProfiles || {});
    setText("riskProfileActionStatus", "新版本已保存。启用前仍不会影响运行配置。");
  } catch (error) {
    setText("riskProfileActionStatus", `保存失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function activateRiskProfileVersion() {
  const selected = selectedRiskProfile();
  if (!selected) return;
  const button = el("activateRiskProfileButton");
  button.disabled = true;
  setText("riskProfileActionStatus", "正在追加配置启用记录；Live release hash 不匹配时仍会阻止下单。");
  try {
    const response = await postJson("/api/risk-profiles/activate", {
      riskProfileId: selected.riskProfileId,
      actor: "user_manual",
      confirmation: el("riskProfileConfirmation")?.value || "",
      reason: "console_manual_activation",
    });
    if (el("riskProfileConfirmation")) el("riskProfileConfirmation").value = "";
    renderRiskProfiles(response.riskProfiles || {});
    setText("riskProfileActionStatus", "配置版本已启用；修改本身不授予交易权限。");
  } catch (error) {
    setText("riskProfileActionStatus", `启用失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function rollbackRiskProfileVersion() {
  const environment = el("riskProfileEnvironment")?.value || "live_canary";
  const button = el("rollbackRiskProfileButton");
  button.disabled = true;
  setText("riskProfileActionStatus", "正在回滚到上一份不同的不可变配置。");
  try {
    const response = await postJson("/api/risk-profiles/rollback", {
      environment,
      actor: "user_manual",
      confirmation: el("riskProfileConfirmation")?.value || "",
    });
    selectedRiskProfileId = response.activeProfile?.riskProfileId || null;
    if (el("riskProfileConfirmation")) el("riskProfileConfirmation").value = "";
    renderRiskProfiles(response.riskProfiles || {});
    setText("riskProfileActionStatus", "已回滚上一版本；已有持仓仍使用开仓时版本。");
  } catch (error) {
    setText("riskProfileActionStatus", `回滚失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function reconcileLiveCanary() {
  const button = el("liveCanaryReconcileButton");
  button.disabled = true;
  setText("liveCanaryActionStatus", "正在读取 OKX Live 账户配置、余额状态、持仓和挂单并做本地对账；不会下单。 ");
  try {
    const response = await postJson("/api/live-canary/reconcile", {});
    renderLiveCanary(response.liveCanary || {});
    setText("liveCanaryActionStatus", response.reconciliationMatched
      ? "只读对账已匹配；账户金额和持仓明细未写入本地。"
      : "只读对账存在未归属持仓或挂单，Canary 已暂停。");
  } catch (error) {
    setText("liveCanaryActionStatus", `只读对账失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function armLiveCanary() {
  const button = el("liveCanaryArmButton");
  button.disabled = true;
  setText("liveCanaryActionStatus", "正在校验 release、配置 hash、对账和四层进程门。 ");
  try {
    const response = await postJson("/api/live-canary/arm", {
      actor: "user_manual",
      confirmation: el("liveCanaryArmConfirmation")?.value || "",
    });
    if (el("liveCanaryArmConfirmation")) el("liveCanaryArmConfirmation").value = "";
    renderLiveCanary(response.liveCanary || {});
    setText("liveCanaryActionStatus", "固定 Canary 已 ARM；只有匹配 release 的内部信号才可进入机械执行。 ");
  } catch (error) {
    setText("liveCanaryActionStatus", `Canary ARM 失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function stopLiveCanary() {
  const button = el("liveCanaryKillButton");
  button.disabled = true;
  setText("liveCanaryActionStatus", "正在先激活本地紧急停止，再尝试发送 OKX cancel-all-after。 ");
  try {
    const response = await postJson("/api/live-canary/kill-switch", { reason: "console_operator_emergency_stop" });
    renderLiveCanary(response.liveCanary || {});
    setText("liveCanaryActionStatus", response.exchangeCancelSent
      ? "本地已停止，OKX cancel-all-after 已接受。"
      : "本地已停止；未发送或未确认 OKX cancel-all-after，请人工复核账户。 ");
  } catch (error) {
    setText("liveCanaryActionStatus", `紧急停止请求失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

function forwardReviewBadge(row) {
  const tone = row?.tone || "warn";
  return `<span class="badge ${tone}">${escapeHtml(row?.reviewLabel || "--")} · ${formatNumber(row?.readinessScore, 0)}分</span>`;
}

function renderForwardReview(payload) {
  if (!el("forwardReviewList")) return;
  const summary = payload?.summary || {};
  const rows = Array.isArray(payload?.rows) ? payload.rows : [];
  const expansion = payload?.candidateExpansion || {};
  const expansionSummary = expansion.summary || {};
  const expansionRows = Array.isArray(expansion.topCandidates) ? expansion.topCandidates : [];
  const readyCount = Number(summary.readyForManualReviewCount || 0);

  el("forwardReviewCandidateCount").textContent = String(summary.candidateCount ?? rows.length ?? 0);
  el("forwardReviewReadyCount").textContent = String(readyCount);
  el("forwardReviewManualLogs").textContent = String(summary.manualForwardLogCount ?? 0);
  el("forwardReviewClosedSamples").textContent = String(summary.manualClosedSampleCount ?? 0);
  el("forwardReviewVirtualLogs").textContent = String(summary.virtualReplayLogCount ?? 0);
  el("forwardReviewExpandableCount").textContent = String(expansionSummary.expandableCandidateCount ?? expansionRows.length ?? 0);
  el("forwardReviewNextAction").textContent = summary.nextAction || "继续收集真实前向观察日志。";
  el("forwardReviewStatus").textContent = readyCount > 0 ? "可人工复核" : "等待前向数据";
  el("forwardReviewStatus").className = `status-pill ${readyCount > 0 ? "warn" : "danger"}`;

  el("forwardReviewList").innerHTML = rows.map((row) => {
    const logSummary = row.logSummary || {};
    const blockers = Array.isArray(row.blockers) ? row.blockers : [];
    const latestLogs = Array.isArray(row.latestLogs) ? row.latestLogs : [];
    const recommendedPairs = Array.isArray(row.recommendedPairs) ? row.recommendedPairs : [];
    return `
      <div class="forward-review-row">
        <div class="forward-review-row-head">
          <div>
            <strong>${escapeHtml(row.title || row.taskId || "--")}</strong>
            <small>${escapeHtml(row.taskId || "--")} · ${escapeHtml(row.timeframe || "--")} · ${recommendedPairs.length ? recommendedPairs.map(escapeHtml).join(" / ") : "等待推荐币种"}</small>
          </div>
          ${forwardReviewBadge(row)}
        </div>
        <div class="artifact-metrics">
          <span>真实日志 ${logSummary.manualForwardLogCount ?? 0}</span>
          <span>真实闭合 ${logSummary.manualClosedSampleCount ?? 0}</span>
          <span>虚拟样本 ${logSummary.virtualReplayLogCount ?? 0}</span>
          <span>规则匹配 ${logSummary.ruleMatchedCount ?? 0}</span>
          <span>风险 ${logSummary.riskWarningCount ?? 0}</span>
          <span>失效 ${logSummary.invalidatedCount ?? 0}</span>
          <span>R合计 ${formatNumber(logSummary.outcomeRTotal, 2)}</span>
          <span>最近 ${formatDate(logSummary.latestLogAt)}</span>
        </div>
        <div class="forward-review-blockers">
          ${(blockers.length ? blockers : ["前向复核材料已满足本地检查；仍需人工确认。"])
            .slice(0, 8)
            .map((item) => `<small>${escapeHtml(item)}</small>`)
            .join("")}
        </div>
        <div class="forward-review-action">${escapeHtml(row.nextAction || "继续观察，不自动执行。")}</div>
        <details class="forward-review-latest">
          <summary>最近观察日志</summary>
          ${latestLogs.length ? latestLogs.map((log) => `
            <div class="forward-review-log-line">
              <span>${formatDate(log.createdAt)} · ${escapeHtml(log.pair || "--")} · ${escapeHtml(log.logType || "--")}</span>
              <strong>${escapeHtml(log.outcome || log.outcomeR || "未闭合")}</strong>
            </div>
          `).join("") : '<div class="forward-review-log-line"><span>暂无真实前向日志。</span><strong>--</strong></div>'}
        </details>
      </div>
    `;
  }).join("") || '<div class="forward-review-empty">暂无可复核策略。请先导入 Quant Engine 报告。</div>';

  el("forwardReviewExpansionAnswer").textContent = expansion.answer || "等待候选扩展池。";
  el("forwardReviewExpansionList").innerHTML = expansionRows.map((item) => `
    <div class="forward-review-expansion-row">
      <div class="forward-review-row-head">
        <div>
          <strong>${escapeHtml(item.title || item.artifactId || "--")}</strong>
          <small>${escapeHtml(item.queueLabel || item.queueType || "研究候选")} · ${escapeHtml(item.strategyId || "--")}</small>
        </div>
        <span class="badge warn">${formatNumber(item.priorityScore, 0)}分</span>
      </div>
      <div class="artifact-metrics">
        <span>样本 ${item.sampleCount ?? "--"}</span>
        <span>胜率 ${formatPercent(item.winRatePct)}</span>
        <span>PF ${formatNumber(item.profitFactor)}</span>
        <span>盈亏比 ${formatNumber(item.rewardRiskRatio)}</span>
        <span>回撤 ${formatPercent(item.maxDrawdownPct)}</span>
      </div>
      <div class="forward-review-action">${escapeHtml(item.nextAction || "先补研究材料，再决定是否进入前向观察。")}</div>
      <small>${escapeHtml(item.safetyNote || "候选扩展不创建订单。")}</small>
    </div>
  `).join("") || '<div class="forward-review-empty">当前没有新的高优先级候选。</div>';
}

async function refreshForwardReview() {
  const button = el("refreshForwardReviewButton");
  const status = el("forwardReviewRefreshStatus");
  if (!button) return;
  button.disabled = true;
  if (status) status.textContent = "正在刷新本地前向复核材料...";
  try {
    await postJson("/api/forward-review/refresh", {});
    await refreshAll();
    if (status) status.textContent = "已刷新前向复核；未请求交易权限。";
  } catch (error) {
    if (status) status.textContent = `前向复核刷新失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function saveSandboxAutoRunnerSettings() {
  const button = el("saveSandboxAutoRunnerButton");
  if (!button) return;
  button.disabled = true;
  try {
    await postJson("/api/local-sandbox/auto-runner", {
      enabled: Boolean(el("sandboxAutoEnabledInput")?.checked),
      intervalMinutes: Number(el("sandboxAutoIntervalInput")?.value || 5),
      maxRunsPerDay: Number(el("sandboxAutoMaxRunsInput")?.value || 288),
    });
    await refreshAll();
  } finally {
    button.disabled = false;
  }
}

async function runSandboxAutoRunnerOnce() {
  const button = el("runSandboxAutoOnceButton");
  if (!button) return;
  button.disabled = true;
  el("learningSandboxAutoAction").textContent = "正在执行一轮自动沙盒观察...";
  try {
    await postJson("/api/local-sandbox/auto-runner/run-now", {});
    await refreshAll();
  } finally {
    button.disabled = false;
  }
}

function renderSimulationAdmissionGate(observationTasks, qualityRows) {
  if (!el("learningSimulationGateList")) return;
  const rows = buildSimulationGateRows(observationTasks, qualityRows);
  const readyCount = rows.filter((row) => row.status === "simulation_review_ready").length;
  const watchCount = rows.filter((row) => row.status === "continue_observing").length;
  const pauseCount = rows.filter((row) => row.status === "pause_review").length;
  el("learningSimulationReadyCount").textContent = String(readyCount);
  el("learningSimulationWatchCount").textContent = String(watchCount);
  el("learningSimulationPauseCount").textContent = String(pauseCount);
  el("learningSimulationMinLogs").textContent = String(simulationAdmissionThresholds.minLogCount);
  el("learningSimulationMinRules").textContent = String(simulationAdmissionThresholds.minRuleMatchedCount);
  el("learningSimulationMinClosed").textContent = String(simulationAdmissionThresholds.minClosedPaperSamples);
  el("learningSimulationGateStatus").textContent = "执行关闭";

  let nextAction = "当前没有策略达到 testnet 升级门槛：本地沙盒可以继续跑，先补无信号日、规则匹配、闭合结果和失效原因。";
  if (readyCount > 0) {
    nextAction = `已有 ${readyCount} 条策略达到 testnet 升级复核门槛，但当前仍不连接交易所、不创建订单。`;
  } else if (pauseCount > 0) {
    nextAction = `有 ${pauseCount} 条策略需要暂停复核：先解释风险或失效记录，再继续观察。`;
  }
  el("learningSimulationNextAction").textContent = nextAction;

  el("learningSimulationGateList").innerHTML = rows.map((row) => `
    <div class="simulation-gate-row">
      <div class="simulation-gate-row-head">
        <div>
          <strong>${escapeHtml(row.title)}</strong>
          <small>${escapeHtml(row.taskId || "--")} · ${escapeHtml(row.qualityLabel)} · 最近 ${formatDate(row.latestLogAt)}</small>
        </div>
        <span class="badge ${row.tone}">${escapeHtml(row.statusLabel)} · ${formatNumber(row.gateScore, 0)}分</span>
      </div>
      <div class="artifact-metrics">
        <span>质量 ${formatNumber(row.qualityScore, 0)}</span>
        <span>日志 ${row.logCount}/${simulationAdmissionThresholds.minLogCount}</span>
        <span>规则 ${row.ruleMatchedCount}/${simulationAdmissionThresholds.minRuleMatchedCount}</span>
        <span>闭合 ${row.closedPaperSampleCount}/${simulationAdmissionThresholds.minClosedPaperSamples}</span>
        <span>目标 ${row.targetClosedSamples || "--"}</span>
        <span>风险 ${row.riskWarningCount}</span>
        <span>失效 ${row.invalidatedCount}</span>
      </div>
      <div class="simulation-gate-missing">
        ${(row.missing.length ? row.missing : ["testnet 升级门槛已满足"]).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
      </div>
      <div class="simulation-gate-next">${escapeHtml(row.nextAction)}</div>
    </div>
  `).join("") || '<div class="simulation-gate-empty">暂无可做 testnet 升级复核的策略观察任务。</div>';
}

function renderSimulationReview(payload) {
  if (!el("simulationReviewQueueList")) return;
  const summary = payload?.summary || {};
  const rows = Array.isArray(payload?.queue) ? payload.queue : [];
  setText("simulationReviewTotal", String(summary.totalStrategies ?? rows.length));
  setText("simulationReviewClosed", String(summary.totalClosedSamples ?? 0));
  setText("simulationReviewReady", String(summary.reviewReadyStrategies ?? 0));
  setText("simulationReviewPromoted", String(summary.promotedCandidates ?? 0));
  setText("simulationReviewDemoted", String(summary.demotedStrategies ?? 0));
  setText("simulationReviewThreshold", `${summary.reviewMinimumClosedSamples ?? 30}/${summary.dryRunMinimumClosedSamples ?? 100}`);
  setText("simulationReviewStatus", payload?.dryRunApproved ? "异常：Dry-run 开启" : "Dry-run 关闭");
  setText("simulationReviewNextAction", summary.nextAction || "继续收集本地模拟盘闭合样本。");

  el("simulationReviewQueueList").innerHTML = rows.map((row) => {
    const metrics = row.metrics || {};
    const sampleGate = row.sampleGate || {};
    const breakdowns = row.breakdowns || {};
    const pairRows = Array.isArray(breakdowns.byPair) ? breakdowns.byPair.slice(0, 3) : [];
    const directionRows = Array.isArray(breakdowns.byDirection) ? breakdowns.byDirection : [];
    const regimeRows = Array.isArray(breakdowns.byMarketRegime) ? breakdowns.byMarketRegime : [];
    const warnings = Array.isArray(row.warnings) ? row.warnings : [];
    const tone = reviewTone(row.status, warnings);
    const directionText = directionRows.length
      ? directionRows.map((item) => `${item.direction || "unknown"} ${item.sampleCount}`).join(" / ")
      : "待补方向字段";
    const regimeText = regimeRows.length
      ? regimeRows.map((item) => `${item.marketRegime || "unknown"} ${item.sampleCount}`).join(" / ")
      : "待补 regime 字段";
    return `
      <div class="simulation-review-row">
        <div class="simulation-review-row-head">
          <div>
            <strong>${escapeHtml(row.strategyName || row.taskId || "--")}</strong>
            <small>${escapeHtml(row.taskId || "--")} · ${escapeHtml(row.timeframe || "--")} · 最近 ${formatDate(row.latestLogAt)}</small>
          </div>
          <span class="badge ${tone}">${escapeHtml(row.statusLabel || simulationReviewStatusLabels[row.status] || row.status || "--")}</span>
        </div>
        <div class="artifact-metrics">
          <span>闭合 ${metrics.closedSamples ?? 0}/${sampleGate.reviewMinimum ?? 30}</span>
          <span>胜率 ${formatPercent(metrics.winRate)}</span>
          <span>PF ${formatNumber(metrics.profitFactor)}</span>
          <span>均盈 ${formatNumber(metrics.averageWinR, 2)}R</span>
          <span>均亏 ${formatNumber(metrics.averageLossR, 2)}R</span>
          <span>回撤 ${formatNumber(metrics.maxDrawdownR, 2)}R</span>
          <span>连亏 ${metrics.maxConsecutiveLosses ?? 0}</span>
          <span>权益 ${formatUsd(metrics.virtualEquity)}</span>
        </div>
        <div class="artifact-metrics">
          <span>Pair ${pairRows.map((item) => `${item.pair || "unknown"} ${item.sampleCount}`).join(" / ") || "待补"}</span>
          <span>方向 ${directionText}</span>
          <span>Regime ${regimeText}</span>
        </div>
        <div class="simulation-review-flags">
          ${(warnings.length ? warnings : ["no_blocking_warning"]).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
        </div>
        <div class="simulation-review-next">
          <strong>${escapeHtml(simulationReviewActionLabels[row.recommendedAction] || row.recommendedAction || "继续观察")}</strong>
          <span>${escapeHtml(row.costAndSlippage?.note || "成本和滑点字段作为后续复核提示，不代表交易批准。")}</span>
        </div>
      </div>
    `;
  }).join("") || '<div class="simulation-review-empty">暂无本地模拟盘复核队列。请先启动本地沙盒并生成日报。</div>';
}

function closedSampleQualityLabel(value) {
  const labels = {
    full_path_ready: "完整路径",
    estimated_path_ready: "估算路径",
    partial_path_ready: "部分路径",
    representative_sample_without_full_trade_path: "代表样本",
  };
  return labels[value] || value || "待补";
}

function weaknessTone(value) {
  if (value === "danger") return "danger";
  if (value === "warning") return "warn";
  if (value === "positive") return "ok";
  return "";
}

function renderClosedSampleReplay(payload) {
  if (!el("closedSampleReplayStrategyList")) return;
  latestClosedSampleReplayPayload = payload || {};
  const summary = payload?.summary || {};
  const rows = Array.isArray(payload?.strategies) ? payload.strategies : [];
  setText("closedSampleReplayStrategies", String(summary.totalStrategies ?? rows.length));
  setText("closedSampleReplayDeduped", String(summary.totalDedupedClosedSamples ?? 0));
  setText("closedSampleReplayRepresentatives", String(summary.totalRepresentativeSamples ?? 0));
  setText("closedSampleReplayAvgScore", summary.averageReviewScore !== undefined ? formatNumber(summary.averageReviewScore, 1) : "--");
  const topWeakness = Array.isArray(summary.topWeaknessLabels) && summary.topWeaknessLabels.length
    ? summary.topWeaknessLabels[0]
    : null;
  setText("closedSampleReplayTopWeakness", topWeakness ? `${topWeakness.label || topWeakness.code} x${topWeakness.count}` : "--");
  setText("closedSampleReplayMissingPath", String(summary.nonActualPathSampleCount ?? summary.missingFullPathSampleCount ?? 0));
  setText("closedSampleReplayDryRun", payload?.dryRunApproved ? "开启" : "关闭");
  setText("closedSampleReplayLive", payload?.liveTradingApproved ? "开启" : "关闭");
  setText("closedSampleReplayStatus", payload?.liveTradingApproved ? "异常：实盘开启" : "实盘关闭");
  setText("closedSampleReplayNextAction", summary.nextAction || "继续用估算路径复盘样本；真实成交路径仍然保持关闭。");

  if (!rows.length) {
    el("closedSampleReplayStrategyList").innerHTML = '<div class="closed-sample-empty">暂无闭合样本复盘数据。</div>';
    el("closedSampleReplayDetail").innerHTML = '<div class="closed-sample-empty">先运行本地沙盒，生成闭合样本后再复盘。</div>';
    return;
  }

  if (!selectedClosedSampleReplayTaskId || !rows.some((row) => row.taskId === selectedClosedSampleReplayTaskId)) {
    selectedClosedSampleReplayTaskId = rows.slice().sort((a, b) => (b.dedupedClosedSampleCount || 0) - (a.dedupedClosedSampleCount || 0))[0]?.taskId || rows[0].taskId;
  }

  el("closedSampleReplayStrategyList").innerHTML = rows.map((row) => {
    const selected = row.taskId === selectedClosedSampleReplayTaskId ? " selected" : "";
    const quality = row.quality || {};
    return `
      <button class="closed-sample-strategy${selected}" data-closed-sample-task-id="${escapeHtml(row.taskId || "")}" type="button">
        <strong>${escapeHtml(row.strategyName || row.taskId || "--")}</strong>
        <small>${escapeHtml(row.timeframe || "--")} · ${escapeHtml(row.statusLabel || row.status || "--")}</small>
        <span>去重 ${row.dedupedClosedSampleCount ?? 0} · 均分 ${formatNumber(row.scoreSummary?.averageReviewScore, 1)} · 估算 ${quality.estimatedPathSampleCount ?? 0} · 真实 ${quality.actualFillSampleCount ?? 0}</span>
      </button>
    `;
  }).join("");

  el("closedSampleReplayStrategyList").querySelectorAll("[data-closed-sample-task-id]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedClosedSampleReplayTaskId = button.getAttribute("data-closed-sample-task-id");
      renderClosedSampleReplay(latestClosedSampleReplayPayload);
    });
  });

  const selected = rows.find((row) => row.taskId === selectedClosedSampleReplayTaskId) || rows[0];
  renderClosedSampleReplayDetail(selected);
}

function renderClosedSampleReplayDetail(row) {
  if (!el("closedSampleReplayDetail")) return;
  if (!row) {
    el("closedSampleReplayDetail").innerHTML = '<div class="closed-sample-empty">请选择一条策略。</div>';
    return;
  }
  const metrics = row.metrics || {};
  const quality = row.quality || {};
  const scoreSummary = row.scoreSummary || {};
  const samples = Array.isArray(row.samples) ? row.samples : [];
  const reviewable = Array.isArray(row.whatCanBeReviewed) ? row.whatCanBeReviewed : [];
  const needs = Array.isArray(row.whatNeedsInstrumentation) ? row.whatNeedsInstrumentation : [];
  el("closedSampleReplayDetail").innerHTML = `
    <div class="closed-sample-detail-head">
      <div>
        <p class="panel-eyebrow">REPLAY DETAIL</p>
        <h4>${escapeHtml(row.strategyName || row.taskId || "--")}</h4>
        <small>${escapeHtml(row.taskId || "--")} · ${escapeHtml(row.timeframe || "--")} · 最近 ${formatDate(row.latestSampleAt)}</small>
      </div>
      <span class="badge ${row.status === "promoted_candidate" ? "success" : "warn"}">${escapeHtml(row.statusLabel || row.status || "--")}</span>
    </div>
    <div class="closed-sample-metrics">
      <span>去重闭合 ${row.dedupedClosedSampleCount ?? 0}</span>
      <span>代表样本 ${row.representativeSampleCount ?? 0}</span>
      <span>总R ${formatNumber(metrics.totalR, 2)}R</span>
      <span>胜率 ${formatPercent(metrics.winRate)}</span>
      <span>PF ${formatNumber(metrics.profitFactor)}</span>
      <span>权益 ${formatUsd(metrics.virtualEquity)}</span>
      <span>估算路径 ${quality.estimatedPathSampleCount ?? 0}</span>
      <span>真实成交 ${quality.actualFillSampleCount ?? 0}</span>
      <span>平均复盘分 ${formatNumber(scoreSummary.averageReviewScore, 1)}</span>
      <span>强样本 ${scoreSummary.strongReviewSampleCount ?? 0}</span>
      <span>弱样本 ${scoreSummary.weakReviewSampleCount ?? 0}</span>
    </div>
    <div class="closed-sample-flags">
      ${(Array.isArray(scoreSummary.topWeaknessLabels) && scoreSummary.topWeaknessLabels.length
        ? scoreSummary.topWeaknessLabels.slice(0, 6)
        : [{ label: "暂无高频弱点", severity: "info", count: 0 }]
      ).map((item) => `<small class="${weaknessTone(item.severity)}">${escapeHtml(item.label || item.code || "--")} x${item.count ?? 0}</small>`).join("")}
    </div>
    <div class="closed-sample-note">${escapeHtml(row.sampleSelectionNote || "代表样本按去重闭合样本生成。")}</div>
    <div class="closed-sample-quality">
      <span>唯一 sampleKey：${quality.hasUniqueSampleId ? "有" : "待补"}</span>
      <span>入场/出场价格：${quality.hasEntryExitPrices ? "有" : "待补"}</span>
      <span>MFE/MAE：${quality.hasPathMetrics ? "有" : "待补"}</span>
      <span>费用/滑点：${quality.hasCostMetrics ? "有" : "待补"}</span>
    </div>
    <div class="closed-sample-two-col">
      <div>
        <strong>当前可复盘</strong>
        ${(reviewable.length ? reviewable : ["本地 R 结果"]).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
      </div>
      <div>
        <strong>后续需要补齐</strong>
        ${(needs.length ? needs : ["完整成交路径字段"]).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
      </div>
    </div>
    <div class="closed-sample-samples">
      ${samples.map((sample) => renderClosedSampleCard(sample)).join("") || '<div class="closed-sample-empty">该策略暂无代表样本。</div>'}
    </div>
  `;
}

function renderClosedSampleCard(sample) {
  const missing = Array.isArray(sample.missingFields) ? sample.missingFields : [];
  const weaknessLabels = Array.isArray(sample.weaknessLabels) ? sample.weaknessLabels : [];
  const pathMode = sample.actualExchangeFill
    ? "真实成交路径"
    : sample.instrumentationStatus === "estimated"
      ? "本地OHLCV估算"
      : "路径待补";
  const pathTone = sample.actualExchangeFill ? "success" : sample.instrumentationStatus === "estimated" ? "warn" : "danger";
  return `
    <div class="closed-sample-card">
      <div class="closed-sample-card-head">
        <div>
          <strong>${escapeHtml(sample.pair || "--")} · ${escapeHtml(sample.timeframe || "--")}</strong>
          <small>${formatDate(sample.createdAt)} · ${escapeHtml(sample.runId || "--")}</small>
        </div>
        <span class="badge ${Number(sample.outcomeR || 0) >= 0 ? "success" : "danger"}">${formatNumber(sample.outcomeR, 2)}R</span>
      </div>
      <p>${escapeHtml(sample.replayNarrative || "暂无复盘说明。")}</p>
      <div class="closed-sample-flags">
        <small class="${Number(sample.reviewScore || 0) >= 60 ? "ok" : Number(sample.reviewScore || 0) >= 40 ? "warn" : "danger"}">复盘分 ${formatNumber(sample.reviewScore, 0)} · ${escapeHtml(sample.reviewRatingLabel || "--")}</small>
        <small>${escapeHtml(sample.primaryWeaknessLabel || "暂无主要弱点")}</small>
        <small>${escapeHtml(sample.reviewSummary || "")}</small>
      </div>
      <div class="closed-sample-metrics">
        <span>结果 ${escapeHtml(sample.outcomeReason || sample.outcome || "--")}</span>
        <span>数据 ${escapeHtml(sample.dataStatus || "--")}</span>
        <span>方向 ${escapeHtml(sample.direction || "待补")}</span>
        <span>Regime ${escapeHtml(sample.marketRegime || "待补")}</span>
        <span>MFE ${sample.mfeR ?? "待补"}</span>
        <span>MAE ${sample.maeR ?? "待补"}</span>
        <span>路径R ${sample.pathOutcomeR ?? "待补"}</span>
        <span>费用R ${sample.feeEstimateR ?? "待补"}</span>
        <span>滑点R ${sample.slippageEstimateR ?? "待补"}</span>
        <span>持有 ${sample.holdingTimeMinutes ?? "待补"} 分钟</span>
        <span>入场 ${sample.entryPrice ?? "待补"}</span>
        <span>出场 ${sample.exitPrice ?? "待补"}</span>
      </div>
      <div class="closed-sample-flags">
        <small class="${pathTone}">路径模式：${escapeHtml(pathMode)}</small>
        <small>真实成交：${sample.actualExchangeFill ? "是" : "否"}</small>
        <small>${escapeHtml(sample.exitPriceSource || "出场来源待补")}</small>
        <small>${escapeHtml(sample.costEstimateMode || "成本模式待补")}</small>
      </div>
      <div class="closed-sample-source">${escapeHtml(sample.dataSourcePathHint || "数据来源待补")}</div>
      <div class="closed-sample-flags">
        ${(weaknessLabels.length ? weaknessLabels.slice(0, 8) : [{ label: "暂无弱点标签", severity: "info" }]).map((item) => `<small class="${weaknessTone(item.severity)}">${escapeHtml(item.label || item.code || "--")}</small>`).join("")}
        <small>${escapeHtml(closedSampleQualityLabel(sample.sampleQuality))}</small>
        ${(missing.length ? missing.slice(0, 8) : [{ label: "路径字段完整" }]).map((item) => `<small>${escapeHtml(item.label || item.field || item)}</small>`).join("")}
      </div>
    </div>
  `;
}

function renderWeaknessActionBoard(payload) {
  if (!el("weaknessActionList")) return;
  latestWeaknessActionBoardPayload = payload || {};
  const summary = payload?.summary || {};
  const actions = Array.isArray(payload?.actions) ? payload.actions : [];
  setText("weaknessActionTotal", String(summary.totalActions ?? actions.length));
  setText("weaknessActionCritical", String(summary.criticalActionCount ?? 0));
  setText("weaknessActionWarning", String(summary.warningActionCount ?? 0));
  setText("weaknessActionBlocked", String(summary.blockedUpgradeCount ?? 0));
  setText("weaknessActionTodo", String(summary.todoCount ?? 0));
  setText("weaknessActionInProgress", String(summary.inProgressCount ?? 0));
  setText("weaknessActionNeedsSamples", String(summary.needsMoreSamplesCount ?? 0));
  setText("weaknessActionResolved", String(summary.resolvedCount ?? 0));
  setText("weaknessActionDryRun", payload?.dryRunApproved ? "开启" : "关闭");
  setText("weaknessActionLive", payload?.liveTradingApproved ? "开启" : "关闭");
  setText("weaknessActionStatus", payload?.liveTradingApproved ? "异常：实盘开启" : "执行关闭");
  setText("weaknessActionNextAction", summary.nextAction || "先等待闭合样本复盘产生弱点标签。");

  const visibleActions = actions.filter((action) => {
    const status = action.taskStatus || "todo";
    const statusMatch =
      weaknessActionFilters.status === "all"
      || (weaknessActionFilters.status === "active" && !["resolved", "archived"].includes(status))
      || weaknessActionFilters.status === status;
    const priorityMatch = weaknessActionFilters.priority === "all" || weaknessActionFilters.priority === action.priorityTone;
    return statusMatch && priorityMatch;
  });

  if (!visibleActions.length) {
    el("weaknessActionList").innerHTML = '<div class="weakness-action-empty">暂无弱点行动项。先运行本地沙盒并完成闭合样本复盘。</div>';
    return;
  }

  el("weaknessActionList").innerHTML = visibleActions.slice(0, 20).map((action) => {
    const tasks = Array.isArray(action.researchTasks) ? action.researchTasks : [];
    const tone = action.priorityTone || weaknessTone(action.severity);
    const status = action.taskStatus || "todo";
    return `
      <article class="weakness-action-row">
        <div class="weakness-action-row-head">
          <div>
            <p class="panel-eyebrow">${escapeHtml(action.weaknessCode || "--")}</p>
            <strong>${escapeHtml(action.strategyName || "--")}</strong>
            <small>${escapeHtml(action.timeframe || "--")} · ${escapeHtml(action.weaknessLabel || "--")} x${action.weaknessCount ?? 0}</small>
          </div>
          <span class="badge ${tone === "danger" ? "danger" : tone === "warn" ? "warn" : "success"}">${escapeHtml(action.priorityLabel || "--")} · ${formatNumber(action.priorityScore, 0)}</span>
        </div>
        <div class="weakness-action-body">
          <strong>${escapeHtml(action.recommendedAction || "等待人工复盘。")}</strong>
          <p>${escapeHtml(action.blockedUpgradeReason || "保持研究观察。")}</p>
        </div>
        <div class="weakness-action-tasks">
          ${tasks.slice(0, 4).map((task, index) => `<small>${index + 1}. ${escapeHtml(task)}</small>`).join("")}
        </div>
        <div class="weakness-action-flags">
          <small class="${weaknessTone(action.severity)}">${escapeHtml(action.severity || "warning")}</small>
          <small>${escapeHtml(weaknessActionStatusLabels[status] || status)}</small>
          <small>样本 ${action.sampleCount ?? 0}</small>
          <small>均分 ${formatNumber(action.averageReviewScore, 1)}</small>
          <small>${action.blockedUpgrade ? "禁止升级" : "继续观察"}</small>
          <small>更新 ${formatDate(action.taskUpdatedAt)}</small>
        </div>
        <div class="weakness-action-note">${escapeHtml(action.taskNote || action.safetyNote || "仅用于本地研究。")}</div>
        <div class="weakness-action-controls">
          <button type="button" data-weakness-action-id="${escapeHtml(action.actionId || "")}" data-weakness-action-status="in_progress">开始处理</button>
          <button type="button" data-weakness-action-id="${escapeHtml(action.actionId || "")}" data-weakness-action-status="needs_more_samples">待更多样本</button>
          <button type="button" data-weakness-action-id="${escapeHtml(action.actionId || "")}" data-weakness-action-status="resolved">标记已处理</button>
          <button type="button" data-weakness-action-id="${escapeHtml(action.actionId || "")}" data-weakness-action-status="archived">归档</button>
        </div>
      </article>
    `;
  }).join("");

  el("weaknessActionList").querySelectorAll("[data-weakness-action-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const actionId = button.getAttribute("data-weakness-action-id") || "";
      const taskStatus = button.getAttribute("data-weakness-action-status") || "todo";
      const currentAction = actions.find((action) => action.actionId === actionId) || {};
      const defaultNote = currentAction.recommendedAction || "本地研究任务状态更新。";
      const note = window.prompt("备注（只保存到本地研究任务，不会创建订单）：", defaultNote) || defaultNote;
      button.disabled = true;
      try {
        await postJson("/api/weakness-action-task", {
          actionId,
          taskStatus,
          note,
          owner: "local_research",
        });
        await refreshAll();
      } finally {
        button.disabled = false;
      }
    });
  });
}

function renderResearchExecutionPipeline(payload) {
  if (!el("pipelineExecutionList")) return;
  latestResearchPipelinePayload = payload || {};
  const summary = payload?.summary || {};
  const executor = payload?.researchActionExecutor || {};
  const promotion = payload?.candidatePromotionGate || {};
  const testnet = payload?.testnetReadinessPack || {};
  const executions = Array.isArray(executor.executions) ? executor.executions.slice(0, 8) : [];
  const promotionRows = Array.isArray(promotion.rows) ? promotion.rows.slice(0, 6) : [];
  const blockers = Array.isArray(testnet.blockers) ? testnet.blockers.slice(0, 8) : [];
  setText("pipelineActionCount", String(summary.researchActionCount ?? 0));
  setText("pipelineUpdatedTasks", String(summary.researchUpdatedTaskCount ?? 0));
  setText("pipelineSandboxCandidates", String(summary.sandboxReviewCandidateCount ?? 0));
  setText("pipelineTestnetCandidates", String(summary.testnetReadinessCandidateCount ?? 0));
  setText("pipelineTestnetBlockers", String(summary.testnetBlockerCount ?? blockers.length));
  setText("pipelineSimulationStage", summary.simulationStageLabel || "--");
  setText("researchPipelineStatus", "执行关闭");
  setText("researchPipelineNextAction", summary.nextAction || "继续本地研究执行，暂不进入交易执行。");

  el("pipelineExecutionList").innerHTML = executions.map((row) => {
    const checks = Array.isArray(row.checks) ? row.checks : [];
    const failed = checks.filter((item) => item.status !== "passed");
    const tone = row.targetTaskStatus === "resolved" ? "ok" : row.targetTaskStatus === "needs_more_samples" ? "warn" : "danger";
    return `
      <div class="research-pipeline-row">
        <div class="research-pipeline-row-head">
          <div>
            <strong>${escapeHtml(row.strategyName || row.taskId || "--")}</strong>
            <small>${escapeHtml(row.weaknessLabel || row.weaknessCode || "--")} · ${escapeHtml(row.actionId || "--")}</small>
          </div>
          <span class="badge ${tone}">${escapeHtml(row.targetTaskStatusLabel || row.targetTaskStatus || "--")}</span>
        </div>
        <div class="artifact-metrics">
          <span>优先 ${formatNumber(row.priorityScore, 0)}</span>
          <span>检查 ${checks.length}</span>
          <span>缺口 ${failed.length}</span>
          <span>当前 ${escapeHtml(weaknessActionStatusLabels[row.currentTaskStatus] || row.currentTaskStatus || "--")}</span>
        </div>
        <div class="research-pipeline-action">${escapeHtml(row.conclusion || "等待执行结论。")}</div>
        <div class="research-pipeline-flags">
          ${(failed.length ? failed : checks.slice(0, 2)).map((item) => `<small>${escapeHtml(item.label || item.checkId)}：${escapeHtml(item.status || "--")}</small>`).join("")}
        </div>
      </div>
    `;
  }).join("") || '<div class="research-pipeline-empty">暂无研究行动执行结果。</div>';

  el("pipelineGateList").innerHTML = [
    ...promotionRows.map((row) => `
      <div class="research-pipeline-row">
        <div class="research-pipeline-row-head">
          <div>
            <strong>${escapeHtml(row.strategyName || row.taskId || "--")}</strong>
            <small>闭合 ${row.closedSamples ?? 0} · PF ${formatNumber(row.profitFactor)} · 弱点 ${row.unresolvedActionCount ?? 0}</small>
          </div>
          <span class="badge ${row.tone || "warn"}">${escapeHtml(row.promotionLabel || "--")}</span>
        </div>
        <div class="research-pipeline-action">${escapeHtml(row.nextAction || "继续本地复核。")}</div>
        <div class="research-pipeline-flags">
          ${(Array.isArray(row.missingChecks) && row.missingChecks.length ? row.missingChecks : ["暂无阻塞说明"]).slice(0, 4).map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
        </div>
      </div>
    `),
    blockers.length ? `
      <div class="research-pipeline-row danger-line">
        <div class="research-pipeline-row-head">
          <div>
            <strong>Testnet 准备仍阻塞</strong>
            <small>${escapeHtml(testnet.summary?.nextAction || "等待 testnet readiness pack。")}</small>
          </div>
          <span class="badge danger">不开启</span>
        </div>
        <div class="research-pipeline-flags">
          ${blockers.map((item) => `<small>${escapeHtml(item)}</small>`).join("")}
        </div>
      </div>
    ` : "",
  ].join("") || '<div class="research-pipeline-empty">暂无晋级检查结果。</div>';
}

function renderTestnetDesignBoundary(payload) {
  if (!el("testnetDesignChecklistList")) return;
  latestTestnetDesignBoundaryPayload = payload || {};
  const summary = payload?.summary || {};
  const missingControls = Array.isArray(payload?.missingControls) ? payload.missingControls : [];
  const futureSequence = Array.isArray(payload?.futureSequence) ? payload.futureSequence : [];
  const disabledActions = Array.isArray(payload?.disabledActions) ? payload.disabledActions : [];

  setText("testnetDesignStatus", summary.stageLabel || "仅设计准备");
  setText("testnetDesignStage", summary.stageLabel || "--");
  setText("testnetDesignImplemented", String(summary.implementedControlCount ?? 0));
  setText("testnetDesignMissing", String(summary.missingRequiredControlCount ?? missingControls.length));
  setText("testnetDesignCandidates", String(summary.testnetCandidateCount ?? 0));
  setText("testnetDesignBlockers", String(summary.blockerCount ?? missingControls.length));
  setText("testnetDesignOrders", summary.orderCreationEnabled ? "开启" : "禁用");
  setText("testnetDesignNextAction", summary.nextAction || "先完成 Testnet 安全设计，不连接交易所。");

  el("testnetDesignChecklistList").innerHTML = missingControls.map((item) => `
    <div class="testnet-design-row">
      <div class="testnet-design-row-head">
        <div>
          <strong>${escapeHtml(item.label || item.controlId || "--")}</strong>
          <small>${escapeHtml(item.reason || "等待补齐设计。")}</small>
        </div>
        <span class="badge danger">未完成</span>
      </div>
    </div>
  `).join("") || '<div class="testnet-design-empty">当前没有缺失控制，但仍未开放交易连接。</div>';

  const actionRows = disabledActions.map((item) => `
    <div class="testnet-design-row muted-row">
      <div class="testnet-design-row-head">
        <div>
          <strong>${escapeHtml(item.label || item.actionId || "--")}</strong>
          <small>${escapeHtml(item.reason || "当前禁用。")}</small>
        </div>
        <span class="badge danger">灰显</span>
      </div>
    </div>
  `).join("");

  el("testnetDesignSequenceList").innerHTML = futureSequence.map((item) => {
    const tone = item.status === "available_now" ? "warn" : item.status === "future_only" ? "neutral" : "danger";
    return `
      <div class="testnet-design-row">
        <div class="testnet-design-row-head">
          <div>
            <strong>${escapeHtml(item.label || item.stepId || "--")}</strong>
            <small>${escapeHtml(item.description || "--")}</small>
          </div>
          <span class="badge ${tone}">${escapeHtml(item.status || "blocked")}</span>
        </div>
      </div>
    `;
  }).join("") + actionRows;
}

function renderPreLivePreparationPack(payload) {
  if (!el("preLiveLifecycleList")) return;
  latestPreLivePreparationPayload = payload || {};
  const summary = payload?.summary || {};
  const lifecycle = Array.isArray(payload?.orderLifecycleStages) ? payload.orderLifecycleStages : [];
  const riskLimits = Array.isArray(payload?.riskLimits) ? payload.riskLimits : [];
  const killSwitchControls = Array.isArray(payload?.killSwitchControls) ? payload.killSwitchControls : [];
  const credentialItems = Array.isArray(payload?.credentialVaultDesign) ? payload.credentialVaultDesign : [];
  const referenceInputs = Array.isArray(payload?.referenceInputs) ? payload.referenceInputs : [];
  const rehearsalSummary = payload?.rehearsalSummary || {};
  const closureRows = Array.isArray(payload?.preLiveClosureReport) ? payload.preLiveClosureReport : [];
  const runbookRows = Array.isArray(payload?.operationalRunbook) ? payload.operationalRunbook : [];
  const recentRehearsals = Array.isArray(payload?.recentRehearsals) ? payload.recentRehearsals : [];

  setText("preLiveStage", summary.stageLabel || "实盘前本地演练");
  setText("preLiveLifecycleReady", summary.orderLifecycleSimulatorReady ? "已设计" : "未完成");
  setText("preLiveManualConfirm", summary.manualConfirmationRequired ? "强制" : "未设置");
  setText("preLiveKillSwitch", summary.killSwitchDesigned ? "已设计" : "未完成");
  setText("preLiveVaultStatus", summary.credentialVaultImplemented ? "已实现" : "未实现");
  setText("preLiveOrderStatus", summary.orderCreationEnabled ? "开启" : "禁用");
  setText("preLiveDryRunStatus", summary.exchangeDryRunEnabled ? "开启" : "禁用");
  setText("preLiveNextAction", summary.nextAction || "先做本地生命周期预演，不连接交易所。");
  setText("preLiveRehearsalTotal", rehearsalSummary.totalRehearsals ?? 0);
  setText("preLiveRehearsalPassed", rehearsalSummary.passedRehearsals ?? 0);
  setText("preLiveRehearsalRejected", rehearsalSummary.rejectedRehearsals ?? 0);
  setText("preLiveLatestState", rehearsalSummary.latestFinalState || "--");
  setText("preLiveClosureVerdict", rehearsalSummary.localLifecyclePathsComplete ? "本地闭环已补齐" : "待补演练");
  setText("preLiveBlockerCount", rehearsalSummary.blockerCount ?? "--");

  if (el("preLiveClosureList")) {
    const toneForStatus = (status) => {
      if (status === "passed") return "ok";
      if (status === "disabled" || status === "future_required") return "danger";
      return "warn";
    };
    el("preLiveClosureList").innerHTML = closureRows.map((item) => `
      <div class="pre-live-row">
        <div class="pre-live-row-head">
          <div>
            <strong>${escapeHtml(item.label || item.checkId || "--")}</strong>
            <small>${escapeHtml(item.description || "--")}</small>
          </div>
          <span class="badge ${toneForStatus(item.status)}">${escapeHtml(item.status || "--")}</span>
        </div>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无闭环检查。</div>';
  }

  if (el("preLiveRunbookList")) {
    el("preLiveRunbookList").innerHTML = runbookRows.map((item) => `
      <div class="pre-live-row">
        <div class="pre-live-row-head">
          <div>
            <strong>${escapeHtml(item.label || item.stepId || "--")}</strong>
            <small>${escapeHtml(item.description || "--")}</small>
          </div>
          <span class="badge warn">${escapeHtml(item.status || "--")}</span>
        </div>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无运行手册。</div>';
  }

  if (el("preLiveRecentList")) {
    el("preLiveRecentList").innerHTML = recentRehearsals.map((item) => `
      <div class="pre-live-row">
        <div class="pre-live-row-head">
          <div>
            <strong>${escapeHtml(item.symbol || "--")} · ${escapeHtml(item.finalState || "--")}</strong>
            <small>${formatDate(item.createdAt || item.generatedAt)} · ${escapeHtml(item.strategyId || "--")} · ${formatNumber(item.notional, 2)} notional</small>
          </div>
          <span class="badge ${item.riskPassed ? "ok" : "danger"}">${item.riskPassed ? "通过" : "拒绝"}</span>
        </div>
      </div>
    `).join("") || '<div class="testnet-design-empty">暂无本地演练记录。</div>';
  }

  el("preLiveLifecycleList").innerHTML = lifecycle.map((item) => `
    <div class="pre-live-row">
      <div class="pre-live-row-head">
        <div>
          <strong>${escapeHtml(item.label || item.stageId || "--")}</strong>
          <small>${escapeHtml(item.description || "--")}</small>
        </div>
        <span class="badge warn">${escapeHtml(item.status || "local_preview")}</span>
      </div>
    </div>
  `).join("") || '<div class="testnet-design-empty">暂无生命周期步骤。</div>';

  const combinedRiskRows = [
    ...riskLimits.map((item) => ({
      title: item.label || item.limitId,
      subtitle: item.value || item.description || "--",
      badge: item.severity || "required",
      description: item.description,
    })),
    ...killSwitchControls.map((item) => ({
      title: item.label || item.controlId,
      subtitle: item.state || "--",
      badge: item.state || "designed",
      description: item.description,
    })),
  ];
  el("preLiveRiskList").innerHTML = combinedRiskRows.map((item) => `
    <div class="pre-live-row">
      <div class="pre-live-row-head">
        <div>
          <strong>${escapeHtml(item.title || "--")}</strong>
          <small>${escapeHtml(item.description || item.subtitle || "--")}</small>
        </div>
        <span class="badge danger">${escapeHtml(item.badge || "--")}</span>
      </div>
    </div>
  `).join("") || '<div class="testnet-design-empty">暂无风控和熔断设计。</div>';

  el("preLiveCredentialList").innerHTML = credentialItems.map((item) => `
    <div class="pre-live-row">
      <div class="pre-live-row-head">
        <div>
          <strong>${escapeHtml(item.label || item.itemId || "--")}</strong>
          <small>${escapeHtml(item.description || "--")}</small>
        </div>
        <span class="badge danger">${escapeHtml(item.status || "required_future")}</span>
      </div>
    </div>
  `).join("") || '<div class="testnet-design-empty">暂无凭据边界设计。</div>';

  el("preLiveReferenceList").innerHTML = referenceInputs.map((item) => `
    <div class="pre-live-row">
      <div class="pre-live-row-head">
        <div>
          <strong>${escapeHtml(item.label || item.sourceId || "--")}</strong>
          <small>${escapeHtml(item.usableIdea || "--")}</small>
        </div>
        <span class="badge warn">${escapeHtml(item.storedUse || "reference")}</span>
      </div>
      <small>${escapeHtml(item.boundary || "仅作为参考，不复制执行代码。")}</small>
    </div>
  `).join("") || '<div class="testnet-design-empty">暂无参考资料记录。</div>';
}

function renderPreLiveLifecyclePreview(payload) {
  if (!el("preLivePreviewPath")) return;
  const path = Array.isArray(payload?.lifecyclePath) ? payload.lifecyclePath : [];
  const tone = payload?.riskPassed ? "ok" : "danger";
  el("preLivePreviewPath").innerHTML = `
    <div class="pre-live-preview-head">
      <div>
        <strong>本地预演结果：${escapeHtml(payload?.finalState || "--")}</strong>
        <small>${escapeHtml(payload?.symbol || "--")} · ${formatNumber(payload?.notional, 2)} notional · ${formatNumber(payload?.riskR, 2)}R</small>
      </div>
      <span class="badge ${tone}">${payload?.riskPassed ? "通过本地检查" : "本地拒绝"}</span>
    </div>
    <div class="pre-live-preview-path">
      ${path.map((item) => `
        <div>
          <strong>${escapeHtml(item.label || item.stageId || "--")}</strong>
          <small>${escapeHtml(item.state || "--")}</small>
        </div>
      `).join("")}
    </div>
    <div class="pre-live-preview-notes">
      ${(payload?.riskNotes || []).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
    </div>
    <small>${escapeHtml(payload?.safetyNote || "本地预演不创建订单。")}</small>
  `;
}

async function runPreLiveLifecyclePreview() {
  const button = el("runPreLiveLifecyclePreviewButton");
  if (!button) return;
  button.disabled = true;
  setText("preLivePreviewStatus", "正在保存本地生命周期演练记录...");
  try {
    const result = await postJson("/api/pre-live-order-lifecycle/rehearse", {
      strategyId: latestStrategyPlaybookTask?.taskId || "manual_rehearsal_strategy",
      symbol: "BTC/USDT:USDT",
      notional: 100,
      riskR: 1,
      manualDecision: "approve_for_rehearsal",
    });
    renderPreLiveLifecyclePreview(result.rehearsal || {});
    if (result.preLivePreparationPack) renderPreLivePreparationPack(result.preLivePreparationPack);
    setText("preLivePreviewStatus", "已保存本地演练记录：没有连接交易所，没有创建订单。");
  } catch (error) {
    setText("preLivePreviewStatus", `演练保存失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function runResearchPipeline() {
  const button = el("runResearchPipelineButton");
  if (!button) return;
  button.disabled = true;
  setText("researchPipelineRunStatus", "正在执行本地研究流水线...");
  try {
    await postJson("/api/research-execution-pipeline/run", { applyUpdates: true });
    await refreshAll();
    setText("researchPipelineRunStatus", "已执行：只回写本地研究任务状态，没有连接交易所。");
  } catch (error) {
    setText("researchPipelineRunStatus", `执行失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

function pickPrimaryObservationTask(loopPayload) {
  const tasks = getObservationTasksFromLoop(loopPayload);
  if (selectedStrategyPlaybookTaskId) {
    const selected = tasks.find((task) => task.taskId === selectedStrategyPlaybookTaskId);
    if (selected) return selected;
  }
  return tasks.find((task) => task.rank === 1) || tasks[0] || null;
}

function getStrategyPlainTemplate(task) {
  const title = task?.title || "";
  if (title.includes("横盘超卖修复")) {
    return {
      name: "横盘超卖修复策略",
      what: "等待日线横盘后的过度下跌修复，不追涨，只记录修复样本。",
      when: "适合震荡或修复状态；重点观察 RSI/波动率修复后是否能走出 2R。",
    };
  }
  if (title.includes("趋势低波突破")) {
    return {
      name: "趋势低波突破策略",
      what: "等待趋势中波动收缩后的突破延续，用低波动过滤假突破。",
      when: "适合趋势已经存在、波动暂时收敛、再度放量突破的环境。",
    };
  }
  if (title.includes("广谱低波突破")) {
    return {
      name: "广谱低波突破策略",
      what: "在更多币种里寻找低波动突破样本，先看覆盖面，再看稳定性。",
      when: "适合做资产池筛选，不适合直接当作单币种执行指令。",
    };
  }
  if (title.includes("趋势突破确认")) {
    return {
      name: "趋势突破确认策略",
      what: "等待日线趋势突破后再次确认，只观察趋势延续是否能达到固定 2R。",
      when: "适合 BTC 处于 bull/recovery 且主流币趋势结构较清楚的阶段。",
    };
  }
  return {
    name: title || "策略说明书",
    what: "读取本地策略研究报告，按纸面观察标准记录信号和结果。",
    when: "适合继续收集样本，不代表交易建议。",
  };
}

function translateLogField(field) {
  const labels = {
    date: "日期",
    pair: "币种",
    timeframe: "周期",
    signalObserved: "是否看到信号",
    ruleMatched: "是否规则匹配",
    entryContext: "入场上下文",
    btcRegime: "BTC 状态",
    paperOutcomeR: "纸面结果 R",
    invalidatedReason: "失效原因",
    riskNote: "风险备注",
    screenshotOrChartNote: "截图或图表备注",
  };
  return labels[field] || field;
}

function formatPairList(pairs, limit = 5) {
  if (!Array.isArray(pairs) || !pairs.length) return [];
  return pairs.slice(0, limit).map((item) => {
    const pieces = [item.pair || "--"];
    if (item.tradeCount !== undefined) pieces.push(`样本 ${item.tradeCount}`);
    if (item.profitFactor !== undefined && item.profitFactor !== null) pieces.push(`PF ${formatNumber(item.profitFactor)}`);
    if (item.totalReturnPct !== undefined && item.totalReturnPct !== null) pieces.push(`收益 ${formatPercent(item.totalReturnPct)}`);
    return pieces.join(" · ");
  });
}

function renderStrategyDetailDrawer(primary, template, metrics, recommendedPairs, weakPoints, btcRegimes) {
  if (!primary) {
    el("strategyDetailHeadline").textContent = "等待选择策略";
    setList("strategyDetailFit", []);
    setList("strategyDetailAvoid", []);
    setList("strategyDetailEntry", []);
    setList("strategyDetailExit", []);
    setList("strategyDetailWeakness", []);
    setList("strategyDetailLogFields", []);
    renderStrategyQuickLog(null);
    return;
  }

  const avoidPairs = Array.isArray(primary?.avoidUntilReviewedPairs) ? primary.avoidUntilReviewedPairs : [];
  const promotionCriteria = Array.isArray(primary?.promotionCriteria) ? primary.promotionCriteria : [];
  const rejectionCriteria = Array.isArray(primary?.rejectionCriteria) ? primary.rejectionCriteria : [];
  const dailyLogFields = Array.isArray(primary?.dailyLogFields) ? primary.dailyLogFields : [];
  const observation = primary?.observationPlan || {};
  const family = primary?.family || "未标注";
  const targetR = formatNumber(primary?.targetRewardRiskRatio || primary?.targetRMultiple || 2, 1);

  el("strategyDetailHeadline").textContent = `${template.name} · ${primary.candidateId || primary.strategyId || "--"}`;
  setList("strategyDetailFit", [
    template.when,
    btcRegimes.length ? `BTC 状态优先：${btcRegimes.join(" / ")}` : "需要继续标注 BTC 状态。",
    `策略家族：${family}；周期：${primary.timeframe || "--"}；目标：${targetR}R。`,
    ...formatPairList(recommendedPairs, 4).map((line) => `优先观察：${line}`),
  ]);
  setList("strategyDetailAvoid", [
    "不适合直接当作买卖指令；当前只做本地纸面观察。",
    ...formatPairList(avoidPairs, 4).map((line) => `暂缓观察：${line}`),
    "如果出现流动性、数据质量或状态漂移，需要先复核再继续。",
  ]);
  setList("strategyDetailEntry", [
    "先确认当天是否真的出现信号，而不是事后挑样本。",
    "记录规则是否完整匹配、BTC 状态、币种、周期和入场上下文。",
    observation.minimumRuleMatchedSignals ? `至少累计 ${observation.minimumRuleMatchedSignals} 次规则匹配记录。` : "需要累计足够规则匹配记录。",
    recommendedPairs.length ? "优先从推荐观察资产中记录，不扩大到历史弱势资产。" : "等待推荐观察资产。",
  ]);
  setList("strategyDetailExit", [
    "记录纸面结果 R、失效原因、错过观察和风险备注。",
    "固定 2R 目标不降低；不要为了胜率改目标。",
    ...rejectionCriteria.slice(0, 4),
  ]);
  setList("strategyDetailWeakness", [
    ...weakPoints.slice(0, 5),
    metrics.maxConsecutiveLosses ? `历史最大连续亏损：${metrics.maxConsecutiveLosses}。` : "",
    ...promotionCriteria.slice(0, 3).map((item) => `晋级条件：${item}`),
  ]);
  setList("strategyDetailLogFields", dailyLogFields.length
    ? dailyLogFields.map((field) => translateLogField(field))
    : ["日期", "币种", "周期", "是否看到信号", "是否规则匹配", "纸面结果 R", "风险备注"]);
  renderStrategyQuickLog(primary);
}

function renderStrategyQuickLog(primary) {
  const taskId = primary?.taskId || "";
  const recentLogs = Array.isArray(primary?.recentLogs) ? primary.recentLogs.slice(0, 4) : [];
  const localObservation = primary?.localObservation || {};
  const canLog = Boolean(taskId);
  const typeSelect = el("strategyQuickLogType");
  if (typeSelect && !typeSelect.innerHTML.trim()) {
    typeSelect.innerHTML = renderPaperLogTypeOptions("no_signal");
  }
  el("strategyQuickTaskLabel").textContent = canLog
    ? `${primary.title || primary.candidateId || taskId} · 已记录 ${localObservation.logCount ?? recentLogs.length} 条`
    : "等待选择策略";
  el("strategyQuickLogButton").disabled = !canLog;
  el("strategyQuickLogStatus").textContent = canLog
    ? "只保存本地纸面观察日志，不会创建订单。"
    : "请先选择一条纸面观察策略。";
  el("strategyQuickRecentLogs").innerHTML = recentLogs.length ? recentLogs.map((log) => `
    <div class="strategy-quick-log-row">
      <strong>${escapeHtml(tPaperLogType(log.logType))}</strong>
      <span>${formatDate(log.createdAt)} · ${escapeHtml(log.outcome || "未写结果")}</span>
      <small>${escapeHtml(log.note || "无备注")}</small>
    </div>
  `).join("") : '<div class="strategy-quick-log-empty">暂无最近观察日志。先记录无信号、看到信号、规则匹配或失效原因。</div>';
}

function renderStrategyPlaybookSelector(tasks, selectedTaskId) {
  const target = el("strategyPlaybookSelector");
  if (!target) return;
  if (!tasks.length) {
    target.innerHTML = '<div class="item">等待纸面观察任务包导入。</div>';
    return;
  }
  target.innerHTML = tasks.slice(0, 8).map((task) => {
    const metrics = task.historicalMetrics || {};
    const quality = task.observationQuality || {};
    const selected = task.taskId === selectedTaskId ? " selected" : "";
    return `
      <button class="strategy-playbook-tab${selected}" data-playbook-task-id="${escapeHtml(task.taskId)}" type="button">
        <span>策略 ${task.rank ?? "--"} · ${escapeHtml(task.timeframe || "--")}</span>
        <strong>${escapeHtml(task.title || task.candidateId || "--")}</strong>
        <small>样本 ${metrics.tradeCount ?? "--"} · 胜率 ${formatPercent(metrics.winRatePct)} · PF ${formatNumber(metrics.profitFactor)} · ${escapeHtml(quality.qualityLabelCn || "未开始")}</small>
      </button>
    `;
  }).join("");
  document.querySelectorAll("[data-playbook-task-id]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedStrategyPlaybookTaskId = button.getAttribute("data-playbook-task-id");
      renderStrategyPlaybook(latestStrategies, {}, latestStrategyLearningLoopPayload);
    });
  });
}

function renderStrategyPlaybook(strategies, mobile, loopPayload) {
  const tasks = getObservationTasksFromLoop(loopPayload);
  const task = pickPrimaryObservationTask(loopPayload);
  const primary = task || pickPrimaryStrategy(strategies);
  latestStrategyPlaybookTask = primary || null;
  const template = getStrategyPlainTemplate(primary);
  const metrics = primary?.historicalMetrics || primary?.metrics || {};
  const observation = primary?.observationPlan || {};
  const quality = primary?.observationQuality || {};
  const recommendedPairs = Array.isArray(primary?.recommendedPairs) ? primary.recommendedPairs : [];
  const weakPoints = Array.isArray(primary?.weakPoints) ? primary.weakPoints : [];
  const blockedActions = Array.isArray(primary?.blockedActions) ? primary.blockedActions : [];
  const btcRegimes = Array.isArray(primary?.btcRegimes) ? primary.btcRegimes : [];
  const targetClosedSamples = observation.targetClosedSamples ?? quality.targetClosedSamples ?? primary?.targetClosedSamples;
  const minRuleMatches = observation.minimumRuleMatchedSignals ?? quality.minimumRuleMatchedSignals;

  if (task?.taskId) {
    selectedStrategyPlaybookTaskId = task.taskId;
  }
  renderStrategyPlaybookSelector(tasks, primary?.taskId || selectedStrategyPlaybookTaskId);

  if (!primary) {
    el("strategyPlainName").textContent = "策略说明书";
    el("strategyPlainPurpose").textContent = "等待本地策略报告导入后显示。";
    el("strategyPlainStage").className = "badge warn";
    el("strategyPlainStage").textContent = "等待导入";
    el("heroStrategyName").textContent = "等待导入策略报告";
    el("heroStrategyOneLine").textContent = "打开后先看这里：它会用一句话说明策略在等什么行情。";
    el("heroStrategyGate").textContent = "交易执行能力关闭";
    el("strategyPlainWhat").textContent = "--";
    el("strategyPlainWhen").textContent = "--";
    el("strategyPlainPairs").textContent = "--";
    el("strategyPlainEvidence").textContent = "--";
    setList("strategyPlainChecklist", []);
    setList("strategyPlainGate", []);
    setList("strategyPlainNext", []);
    renderStrategyDetailDrawer(null, {}, {}, [], [], []);
    return;
  }

  el("strategyPlainName").textContent = `${template.name} · ${primary.title || primary.strategyId || "--"}`;
  el("strategyPlainPurpose").textContent = "把策略编号翻译成可读规则：先说明它等待什么行情，再说明现在为什么只能纸面观察。";
  el("strategyPlainStage").className = `badge ${quality.qualityTone === "ok" ? "ok" : "warn"}`;
  el("strategyPlainStage").textContent = quality.qualityLabelCn || tStatus(primary.status) || "纸面观察";
  el("heroStrategyName").textContent = `${template.name} · ${primary.timeframe || "--"}`;
  el("heroStrategyOneLine").textContent = template.what;
  el("heroStrategyGate").textContent = quality.nextAction || "只做纸面观察，不执行交易";
  el("strategyPlainWhat").textContent = template.what;
  el("strategyPlainWhen").textContent = template.when;
  el("strategyPlainPairs").textContent = recommendedPairs.length
    ? recommendedPairs.slice(0, 6).map((pair) => pair.pair).join(" / ")
    : "--";
  el("strategyPlainEvidence").textContent = [
    `样本 ${metrics.tradeCount ?? "--"}`,
    `胜率 ${formatPercent(metrics.winRatePct)}`,
    `PF ${formatNumber(metrics.profitFactor)}`,
    `最大回撤 ${formatPercent(metrics.maxDrawdownPct)}`,
  ].join(" · ");

  setList("strategyPlainChecklist", [
    `周期：${primary.timeframe || "--"}；策略家族：${primary.family || "未标注"}`,
    `目标盈亏比：${formatNumber(primary.targetRewardRiskRatio || primary.targetRMultiple || 2, 1)}R，不降低 2R 目标`,
    btcRegimes.length ? `优先 BTC 状态：${btcRegimes.join(" / ")}` : "BTC 状态需要继续记录",
    recommendedPairs.length ? `优先观察前 ${Math.min(6, recommendedPairs.length)} 个本地表现较好的币种` : "等待推荐观察币种",
  ]);
  setList("strategyPlainGate", [
    "当前只允许本地纸面观察，不允许下单或自动执行。",
    targetClosedSamples ? `至少需要 ${targetClosedSamples} 个闭合纸面样本。` : "需要补足闭合纸面样本。",
    minRuleMatches ? `至少需要 ${minRuleMatches} 次规则匹配记录。` : "需要补足规则匹配记录。",
    weakPoints.length ? `已知弱点：${weakPoints[0]}` : "还需要继续检查弱点和失效条件。",
    blockedActions.length ? `已锁定：${blockedActions.join(" / ")}` : "交易执行能力保持关闭。",
  ]);
  setList("strategyPlainNext", [
    quality.nextAction || "每天记录无信号日、看到信号、规则匹配和失效原因。",
    "记录 pair、timeframe、BTC 状态、入场上下文、纸面结果 R 和风险备注。",
    "优先记录失败样本和失效原因，不为了胜率跳过坏样本。",
    "只有样本、风险复核和前向表现都合格后，才讨论下一阶段。",
  ]);
  renderStrategyDetailDrawer(primary, template, metrics, recommendedPairs, weakPoints, btcRegimes);
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

function tObservationQuality(value) {
  return observationQualityLabels[value] || value || "--";
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

function renderShortCycleCandidatePool(poolPayload) {
  const summary = poolPayload?.summary || {};
  const candidates = Array.isArray(poolPayload?.candidates) ? poolPayload.candidates : [];
  if (!el("shortCycleSummaryBadge")) return;
  el("shortCycleSummaryBadge").textContent = `短周期 ${formatNumber(summary.selectedShortCycleCount, 0)} 条 · Top ${escapeHtml(summary.topCandidateName || "--")}`;
  el("shortCycleTotal").textContent = formatNumber(summary.totalCandidates, 0);
  el("shortCycleExisting").textContent = formatNumber(summary.existingShortCycleReportCount, 0);
  el("shortCycleDerived").textContent = formatNumber(summary.derivedCandidateCount, 0);
  el("shortCycleTimeframes").textContent = Array.isArray(summary.targetTimeframes) ? summary.targetTimeframes.join(" / ") : "--";
  if (el("shortCycleSafety")) {
    const notes = Array.isArray(poolPayload?.safetyNotes) ? poolPayload.safetyNotes : [];
    el("shortCycleSafety").textContent = notes[0] || "短周期候选池只做研究排序，不是交易信号，不创建订单。";
  }
  el("shortCycleCandidateList").innerHTML = candidates.map((item) => {
    const validationLabel = shortCycleValidationLabels[item.validationStatus] || item.validationLabel || item.validationStatus || "待验证";
    const missing = Array.isArray(item.missingData) ? item.missingData : [];
    const evidence = Array.isArray(item.evidence) ? item.evidence : [];
    return `
      <div class="short-cycle-row">
        <div class="short-cycle-row-head">
          <div>
            <strong>#${formatNumber(item.rank, 0)} ${escapeHtml(item.name || item.shortName || "--")}</strong>
            <small>${escapeHtml(item.shortName || "--")} · ${escapeHtml(item.category || "--")} · ${escapeHtml(item.direction || "--")}</small>
          </div>
          <div>
            <span class="status-pill neutral">${escapeHtml(item.targetTimeframe || "--")}</span>
            <span class="badge warn">${escapeHtml(validationLabel)}</span>
          </div>
        </div>
        <div class="artifact-metrics">
          <span>短周期分 ${formatNumber(item.shortCycleScore, 1)}</span>
          <span>样本 ${item.sampleCount ?? "--"}</span>
          <span>胜率 ${formatPercent(item.winRatePct)}</span>
          <span>PF ${formatNumber(item.profitFactor)}</span>
          <span>RR ${formatNumber(item.rewardRiskRatio)}</span>
          <span>回撤 ${formatPercent(item.maxDrawdownPct)}</span>
        </div>
        <div class="short-cycle-tags">
          <span>${escapeHtml(item.candidateFrequencyLabel || "短周期候选")}</span>
          <span>${escapeHtml(item.sourceTitle || item.sourceStrategyId || "待创建研究资产")}</span>
          <span>${escapeHtml(item.sourceQueueLabel || item.sourceQueueType || "研究池")}</span>
        </div>
        <div class="short-cycle-note">
          <strong>入场想法：</strong>${escapeHtml(item.entryIdea || "--")}<br />
          <strong>风险重点：</strong>${escapeHtml(item.riskIdea || "--")}<br />
          <strong>为什么入池：</strong>${escapeHtml(item.whySelected || "--")}<br />
          <strong>下一步：</strong>${escapeHtml(item.nextAction || "--")}
        </div>
        ${evidence.length ? `<div class="short-cycle-missing">${evidence.slice(0, 4).map((line) => `<span>${escapeHtml(line)}</span>`).join("")}</div>` : ""}
        ${missing.length ? `<div class="short-cycle-missing">${missing.slice(0, 4).map((line) => `<span>缺口：${escapeHtml(line)}</span>`).join("")}</div>` : ""}
      </div>
    `;
  }).join("") || '<div class="item">暂无短周期候选。请先导入策略资产。</div>';
}

function promotionGateBadge(item) {
  const tone = item?.tone || "neutral";
  let kind = "warn";
  if (tone === "ok") kind = "ok";
  if (tone === "danger") kind = "danger";
  if (tone === "neutral") kind = "neutral";
  return `<span class="badge ${kind}">${escapeHtml(item?.gateLabel || item?.bucketLabel || "--")}</span>`;
}

function renderPromotionRows(rows, emptyText, limit = 5) {
  const safeRows = Array.isArray(rows) ? rows : [];
  return safeRows.slice(0, limit).map((item) => {
    const reasons = Array.isArray(item.reasons) ? item.reasons : [];
    const warnings = Array.isArray(item.warnings) ? item.warnings : [];
    const checks = Array.isArray(item.passedChecks) ? item.passedChecks : [];
    return `
      <div class="promotion-gate-row ${escapeHtml(item.tone || "neutral")}">
        <div class="promotion-gate-row-head">
          <div>
            <strong>${escapeHtml(item.title || item.strategy || item.strategyId || "--")}</strong>
            <small>${escapeHtml(item.strategyId || item.strategy || item.sourceFile || item.version || "--")}</small>
          </div>
          ${promotionGateBadge(item)}
        </div>
        <div class="artifact-metrics">
          <span>样本 ${item.sampleCount ?? "--"}</span>
          <span>胜率 ${formatPercent(item.winRatePct)}</span>
          <span>PF ${formatNumber(item.profitFactor)}</span>
          <span>RR ${formatNumber(item.rewardRiskRatio)}</span>
          <span>收益 ${formatPercent(item.totalReturnPct)}</span>
          <span>回撤 ${formatPercent(item.maxDrawdownPct)}</span>
        </div>
        <div class="artifact-note">
          下一步：${escapeHtml(item.nextAction || "继续人工复核。")}
          ${reasons.length ? `<br />原因：${reasons.slice(0, 3).map(escapeHtml).join(" / ")}` : ""}
          ${warnings.length ? `<br />提醒：${warnings.slice(0, 2).map(escapeHtml).join(" / ")}` : ""}
          ${checks.length ? `<br />通过：${checks.slice(0, 2).map(escapeHtml).join(" / ")}` : ""}
        </div>
      </div>
    `;
  }).join("") || `<div class="promotion-gate-empty">${escapeHtml(emptyText)}</div>`;
}

function renderStrategyPromotionGate(payload) {
  const summary = payload?.summary || {};
  const buckets = payload?.buckets || {};
  if (!el("promotionGateSummaryBadge")) return;
  el("promotionGateSummaryBadge").textContent = `幸存 ${formatNumber(summary.survivorCount, 0)} · 负样本 ${formatNumber(summary.negativeSampleCount, 0)}`;
  el("promotionSurvivors").textContent = formatNumber(summary.survivorCount, 0);
  el("promotionWatchlist").textContent = formatNumber(summary.watchlistCount, 0);
  el("promotionNeedsWork").textContent = formatNumber(summary.needsWorkCount, 0);
  el("promotionNegative").textContent = formatNumber(summary.negativeSampleCount, 0);
  const notes = Array.isArray(payload?.safetyNotes) ? payload.safetyNotes : [];
  el("promotionGateSafety").textContent = notes[0] || "策略晋级闸门只做本地研究分桶，不是交易信号，不创建订单。";
  const blockers = Array.isArray(summary.promotionBlockers) ? summary.promotionBlockers : [];
  el("promotionGateNextAction").innerHTML = `
    <strong>${escapeHtml(summary.nextAction || "等待策略晋级数据。")}</strong>
    ${blockers.length ? `<span>阻塞：${blockers.map(escapeHtml).join(" / ")}</span>` : "<span>没有发现可执行权限，当前仍是研究控制台。</span>"}
  `;
  const survivorRows = [
    ...(Array.isArray(buckets.survivors) ? buckets.survivors : []),
    ...(Array.isArray(buckets.watchlist) ? buckets.watchlist : []),
  ];
  const needsRows = [
    ...(Array.isArray(buckets.needsWork) ? buckets.needsWork : []),
    ...(Array.isArray(buckets.archived) ? buckets.archived : []),
  ];
  el("promotionSurvivorList").innerHTML = renderPromotionRows(survivorRows, "暂无幸存者。先做策略换代和补证据。", 6);
  el("promotionNegativeList").innerHTML = renderPromotionRows(buckets.negativeSamples, "暂无负样本报告。", 6);
  el("promotionNeedsWorkList").innerHTML = renderPromotionRows(needsRows, "暂无需要补证据的策略。", 10);
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
  const observationQualityPanel = payload.paperObservationQualityPanel || {};
  const graveyard = Array.isArray(learningLoop.strategyGraveyard) ? learningLoop.strategyGraveyard : [];
  const refactors = Array.isArray(refactorReport.refactorCandidates) ? refactorReport.refactorCandidates : [];
  const experiments = Array.isArray(experimentReport.experimentSpecs) ? experimentReport.experimentSpecs : [];
  const reviews = Array.isArray(rereviewReport.paperObservationReviews) ? rereviewReport.paperObservationReviews : [];
  const observationTasks = Array.isArray(observationTaskPack.paperObservationTasks)
    ? observationTaskPack.paperObservationTasks
    : [];
  const logbook = payload.paperObservationLogbook || {};
  const logbookSummary = logbook.summary || {};
  const qualitySummary = observationQualityPanel.summary || {};
  const qualityRows = Array.isArray(observationQualityPanel.qualityRows)
    ? observationQualityPanel.qualityRows
    : [];
  renderSandboxSimulationLane(observationTasks, qualityRows);
  renderStrategyObservationDailyReport(observationTasks, qualityRows);
  renderSimulationAdmissionGate(observationTasks, qualityRows);

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
  if (el("learningObservationQualityScore")) {
    el("learningObservationQualityScore").textContent = formatNumber(summary.observationQualityAverageScore ?? qualitySummary.averageQualityScore, 1);
  }
  if (el("learningObservationPriorityCount")) {
    el("learningObservationPriorityCount").textContent = String(summary.observationPriorityWatchCount ?? qualitySummary.priorityWatchCount ?? 0);
  }
  if (el("learningObservationRiskReviewCount")) {
    el("learningObservationRiskReviewCount").textContent = String(summary.observationNeedsRiskReviewCount ?? qualitySummary.needsRiskReviewCount ?? 0);
  }
  if (el("learningObservationPauseCount")) {
    el("learningObservationPauseCount").textContent = String(summary.observationPauseCandidateCount ?? qualitySummary.pauseCandidateCount ?? 0);
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
  if (el("learningObservationQualityList")) {
    el("learningObservationQualityList").innerHTML = qualityRows.slice(0, 5).map((row) => {
      const tone = row.qualityTone === "good" ? "ok" : row.qualityTone === "danger" ? "danger" : "warn";
      const progress = row.progress || {};
      const components = row.scoreComponents || {};
      return `
        <div class="research-task-row observation-quality-card">
          <div class="research-task-head">
            <strong>${escapeHtml(row.title || row.candidateId || row.taskId || "--")}</strong>
            <span class="badge ${tone}">${escapeHtml(row.qualityLabelCn || tObservationQuality(row.qualityLabel))} · ${formatNumber(row.qualityScore, 0)}分</span>
          </div>
          <small>${escapeHtml(row.displaySubtitle || "本地观察质量")} · ${escapeHtml(row.taskId || "--")}</small>
          <div class="artifact-metrics">
            <span>日志 ${row.logCount ?? 0}</span>
            <span>规则匹配 ${row.ruleMatchedCount ?? 0}</span>
            <span>闭合样本 ${row.closedPaperSampleCount ?? 0}/${row.targetClosedSamples ?? "--"}</span>
            <span>剩余 ${row.remainingClosedSamples ?? "--"}</span>
            <span>风险 ${row.riskWarningCount ?? 0}</span>
            <span>失效 ${row.invalidatedCount ?? 0}</span>
          </div>
          <div class="quality-progress-grid">
            <span>日志覆盖 ${formatPercent(progress.logCoveragePct, 0)}</span>
            <span>规则覆盖 ${formatPercent(progress.ruleMatchCoveragePct, 0)}</span>
            <span>闭合覆盖 ${formatPercent(progress.closedSampleCoveragePct, 0)}</span>
            <span>最近 ${formatDate(row.latestLogAt)}</span>
          </div>
          <div class="quality-score-components">
            <small>得分：日志 ${formatNumber(components.logCoverage, 1)} / 规则 ${formatNumber(components.ruleMatchCoverage, 1)} / 闭合 ${formatNumber(components.closedSampleCoverage, 1)} / 新鲜度 ${formatNumber(components.recency, 1)} / 风险 ${formatNumber(components.riskHygiene, 1)}</small>
          </div>
          <div>下一步：${escapeHtml(row.nextAction || "继续本地观察，不进入 Dry-run。")}</div>
        </div>
      `;
    }).join("") || '<div class="item">暂无观察质量数据。请先导入 V13.7.23 报告。</div>';
  }
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

function getCurrentMobileStatus() {
  return latestMobilePayload && latestMobilePayload.safetyBoundary ? latestMobilePayload : emptyMobileStatus;
}

function renderConsoleFromPayloads() {
  const core = latestCoreConsolePayload || {};
  const review = latestSandboxReviewPayload || {};
  const strategies = core.strategies || { strategies: [] };
  const reports = core.reports || { reports: [] };
  const strategyItems = strategies.strategies || [];
  const reportItems = reports.reports || [];
  const mobile = getCurrentMobileStatus();
  const connection = core.connection || { notes: [], mobileStatusUrls: [] };
  const exchanges = core.exchanges || { sources: [] };
  const slots = core.slots || { slots: [] };
  const artifacts = core.artifacts || { artifacts: [], summary: {} };
  const paperTasks = core.paperTasks || { tasks: [], summary: {} };
  const usableStrategyCatalog = core.usableStrategyCatalog || { strategies: [], summary: {} };
  const sandboxDailyReport = core.sandboxDailyReport || { reports: [], latestReport: { summary: {}, strategyHealthRows: [] } };
  const sandboxAutoRunner = core.sandboxAutoRunner || { autoRunner: {}, events: [] };
  const sandboxQualityCenter = review.sandboxQualityCenter || { summary: {}, strategies: [], readonlyPreparation: {} };
  const sandboxConcentrationReview = review.sandboxConcentrationReview || { summary: {}, strategies: [], variantGroups: [] };
  const sandboxResultReview = review.sandboxResultReview || { summary: {}, strategies: [], familyReviews: [] };
  const strategyAssetPlaybook = review.strategyAssetPlaybook || { summary: {}, strategies: [], executionReadiness: {} };
  const noKeyPreLive = core.noKeyPreLive || { summary: {}, strategyCards: [], publicCandidates: [], recentTickets: [] };
  const autoExecutionEngine = core.autoExecutionEngine || { summary: {}, records: [], recentRuns: [] };
  const autoExecutionLifecycle = core.autoExecutionLifecycle || { summary: {}, lanes: [], records: [] };
  const autoExecutionReview = core.autoExecutionReview || { summary: {}, blockedReasonBreakdown: [], activeHoldingQueue: [], closedResultsQueue: [], blockedReviewQueue: [], strategyLifecycleSummary: [] };
  const autoExecutionLearning = core.autoExecutionLearning || { summary: {}, byStrategy: [], bySymbol: [], byDirection: [] };
  const exchangeDemo = core.exchangeDemo || { summary: {}, modeCards: [], recentEvents: [], credentialStatus: {} };
  const liveCandidates = core.liveCandidates || { summary: {}, packages: [], recentApprovalActions: [] };
  const riskProfiles = core.riskProfiles || { summary: {}, profiles: [], activeProfiles: {} };
  const liveCanary = core.liveCanary || { summary: {}, runtimeGates: {}, runtime: {}, liveReleases: { summary: {} }, blockers: [] };
  const executionOutcomes = core.executionOutcomes || { summary: {}, records: [], quarantinedExecutionRecords: [] };
  const liveReadiness = core.liveReadiness || { rows: [], summary: {} };
  const forwardReview = core.forwardReview || { rows: [], summary: {} };
  const simulationBridge = core.simulationBridge || emptySimulationBridge;
  const simulationReview = core.simulationReview || emptySimulationReview;
  const strategyLearningLoop = latestStrategyLearningLoopPayload || emptyStrategyLearningLoop;
  const strategyLifecycle = core.strategyLifecycle || emptyStrategyLifecycle;

  renderSimpleConsole(strategyItems, reportItems, mobile, usableStrategyCatalog, sandboxDailyReport, sandboxAutoRunner, liveReadiness, simulationBridge, simulationReview, sandboxQualityCenter, sandboxConcentrationReview, sandboxResultReview, strategyAssetPlaybook);
  renderLocalLabPage(usableStrategyCatalog, sandboxDailyReport, sandboxAutoRunner, sandboxQualityCenter, sandboxResultReview, simulationBridge, simulationReview, strategyLearningLoop);
  renderNoKeyPreLiveWorkbench(noKeyPreLive);
  renderAutoExecutionEngine(autoExecutionEngine);
  renderAutoExecutionLifecycle(autoExecutionLifecycle);
  renderAutoExecutionReview(autoExecutionReview);
  renderAutoExecutionLearning(autoExecutionLearning);
  renderExchangeDemoSimulation(exchangeDemo);
  renderLiveCandidateStatus(liveCandidates);
  renderRiskProfiles(riskProfiles);
  renderLiveCanary(liveCanary);
  renderExecutionOutcomes(executionOutcomes);
  renderCommandCenter(strategyItems, reportItems, mobile);
  renderRuntimeMonitor(strategyItems, mobile);
  renderStrategies(strategyItems);
  renderReports(reportItems);
  renderExchanges(exchanges.sources || [], mobile);
  renderStrategySlots(slots.slots || []);
  renderStrategyArtifacts(artifacts);
  renderUsableStrategyCatalog(usableStrategyCatalog);
  renderSandboxSimulationLane(
    buildUsableCatalogObservationTasks(usableStrategyCatalog),
    sandboxDailyReport?.latestReport?.strategyHealthRows || [],
  );
  renderSandboxDailyReport(sandboxDailyReport);
  renderSandboxAutoRunner(sandboxAutoRunner);
  renderLiveReadiness(liveReadiness);
  renderForwardReview(forwardReview);
  renderStrategyLifecycle(strategyLifecycle);
  renderStrategyPlaybook(strategyItems, mobile, strategyLearningLoop);
  renderForwardValidation(mobile.forwardValidation);
  renderPaperObservationTasks(paperTasks);
  renderMobileConnectionInfo(connection);
  el("mobilePreview").textContent = mobileStatusLoaded
    ? JSON.stringify(mobile, null, 2)
    : "完整手机状态按需加载：进入“手机控制台”页面后自动读取，避免拖慢首页。";
}

async function loadSandboxReviewDataIfNeeded(force = false) {
  if (sandboxReviewLoading) return sandboxReviewLoading;
  if (!force && latestSandboxReviewPayload.sandboxQualityCenter && latestSandboxReviewPayload.sandboxResultReview) {
    return latestSandboxReviewPayload;
  }
  sandboxReviewLoading = loadJsonMap([
    { key: "sandboxQualityCenter", url: "/api/local-sandbox/quality-center", fallback: { summary: {}, strategies: [], readonlyPreparation: {} }, timeoutMs: 12000 },
    { key: "sandboxConcentrationReview", url: "/api/local-sandbox/concentration-review", fallback: { summary: {}, strategies: [], variantGroups: [] }, timeoutMs: 12000 },
    { key: "sandboxResultReview", url: "/api/local-sandbox/result-review", fallback: { summary: {}, strategies: [], familyReviews: [] }, timeoutMs: 12000 },
    { key: "strategyAssetPlaybook", url: "/api/strategy-asset-playbook", fallback: { summary: {}, strategies: [], executionReadiness: {} }, timeoutMs: 30000 },
  ], 2).then((payload) => {
    latestSandboxReviewPayload = payload;
    renderConsoleFromPayloads();
    return payload;
  }).finally(() => {
    sandboxReviewLoading = null;
  });
  return sandboxReviewLoading;
}

async function loadLocalLabEnrichmentIfNeeded(force = false) {
  if (localLabEnrichmentLoading) return localLabEnrichmentLoading;
  if (!force && latestCoreConsolePayload.simulationBridge && latestCoreConsolePayload.simulationReview && latestStrategyLearningLoopPayload.strategyLearningLoop) {
    return latestCoreConsolePayload;
  }
  localLabEnrichmentLoading = loadJsonMap([
    { key: "simulationBridge", url: "/api/simulation-bridge", fallback: emptySimulationBridge, timeoutMs: 6000 },
    { key: "simulationReview", url: "/api/simulation-review", fallback: emptySimulationReview, timeoutMs: 6000 },
    { key: "strategyLearningLoop", url: "/api/strategy-learning-loop", fallback: emptyStrategyLearningLoop, timeoutMs: 12000 },
  ], 2).then((payload) => {
    latestCoreConsolePayload = {
      ...latestCoreConsolePayload,
      simulationBridge: payload.simulationBridge || emptySimulationBridge,
      simulationReview: payload.simulationReview || emptySimulationReview,
    };
    latestStrategyLearningLoopPayload = payload.strategyLearningLoop || emptyStrategyLearningLoop;
    renderConsoleFromPayloads();
    renderSimulationReview(latestCoreConsolePayload.simulationReview || emptySimulationReview);
    renderStrategyLearningLoop(latestStrategyLearningLoopPayload);
    return latestCoreConsolePayload;
  }).finally(() => {
    localLabEnrichmentLoading = null;
  });
  return localLabEnrichmentLoading;
}

async function loadMobileStatusIfNeeded(force = false) {
  if (mobileStatusLoading) return mobileStatusLoading;
  if (!force && mobileStatusLoaded) return latestMobilePayload;
  setText("mobilePreview", "正在加载手机控制台完整状态...");
  mobileStatusLoading = getJsonSafe("/api/mobile/status", emptyMobileStatus, 10000).then((payload) => {
    latestMobilePayload = payload || emptyMobileStatus;
    mobileStatusLoaded = true;
    renderConsoleFromPayloads();
    return latestMobilePayload;
  }).finally(() => {
    mobileStatusLoading = null;
  });
  return mobileStatusLoading;
}

async function loadAdvancedDataIfNeeded(force = false) {
  if (advancedDataLoading) return advancedDataLoading;
  if (!force && advancedDataLoaded) return latestAdvancedPayload;
  advancedDataLoading = (async () => {
    await loadLocalLabEnrichmentIfNeeded(force);
    const advanced = await loadJsonMap([
      { key: "audit", url: "/api/audit", fallback: { events: [] } },
      { key: "candidateQueue", url: "/api/candidate-queue", fallback: { strategies: [], summary: {} } },
      { key: "shortCycleCandidates", url: "/api/short-cycle-candidates", fallback: { candidates: [], summary: {} } },
      { key: "closedSampleReplay", url: "/api/closed-sample-replay", fallback: { samples: [], summary: {} }, timeoutMs: 12000 },
      { key: "weaknessActionBoard", url: "/api/weakness-action-board", fallback: { actions: [], summary: {} }, timeoutMs: 12000 },
      { key: "researchPipeline", url: "/api/research-execution-pipeline", fallback: { summary: {}, stages: [], actions: [] }, timeoutMs: 12000 },
      { key: "testnetDesignBoundary", url: "/api/testnet-design-boundary", fallback: { summary: {}, checklist: [], disabledActions: [] } },
      { key: "preLivePreparation", url: "/api/pre-live-preparation-pack", fallback: { summary: {}, rehearsalSummary: {}, preLiveClosureReport: [], recentRehearsals: [] } },
      { key: "testnetDrill", url: "/api/testnet-drill", fallback: { summary: {}, strategies: [], orderLifecycle: [], riskTemplate: [] }, timeoutMs: 30000 },
      { key: "testnetAudit", url: "/api/testnet-audit-pack", fallback: { summary: {}, auditItems: [], criticalBlockers: [] }, timeoutMs: 60000 },
      { key: "testnetPermission", url: "/api/testnet-permission-check", fallback: { summary: {}, checks: [], referenceInputs: [] }, timeoutMs: 30000 },
      { key: "testnetSmallOrder", url: "/api/testnet-small-order-simulation", fallback: { summary: {}, defaultTicket: {}, orderPath: [], recentSimulations: [] }, timeoutMs: 30000 },
      { key: "strategyPromotionGate", url: "/api/strategy-promotion-gate", fallback: { candidates: [], summary: {} }, timeoutMs: 12000 },
      { key: "researchTaskBoard", url: "/api/research-task-board", fallback: { tasks: [], summary: {} } },
    ], 3);
    latestAdvancedPayload = advanced;
    advancedDataLoaded = true;
    renderAudit(advanced.audit?.events || []);
    renderCandidateQueue(advanced.candidateQueue || { strategies: [], summary: {} });
    renderShortCycleCandidatePool(advanced.shortCycleCandidates || { candidates: [], summary: {} });
    renderSimulationReview(latestCoreConsolePayload.simulationReview || emptySimulationReview);
    renderClosedSampleReplay(advanced.closedSampleReplay || { samples: [], summary: {} });
    renderWeaknessActionBoard(advanced.weaknessActionBoard || { actions: [], summary: {} });
    renderResearchExecutionPipeline(advanced.researchPipeline || { summary: {}, stages: [], actions: [] });
    renderTestnetDesignBoundary(advanced.testnetDesignBoundary || { summary: {}, checklist: [], disabledActions: [] });
    renderPreLivePreparationPack(advanced.preLivePreparation || { summary: {}, rehearsalSummary: {}, preLiveClosureReport: [], recentRehearsals: [] });
    renderTestnetDrill(advanced.testnetDrill || { summary: {}, strategies: [], orderLifecycle: [], riskTemplate: [] });
    renderTestnetAuditPack(advanced.testnetAudit || { summary: {}, auditItems: [], criticalBlockers: [] });
    renderTestnetPermissionCheck(advanced.testnetPermission || { summary: {}, checks: [], referenceInputs: [] });
    renderTestnetSmallOrderSimulation(advanced.testnetSmallOrder || { summary: {}, defaultTicket: {}, orderPath: [], recentSimulations: [] });
    renderStrategyPromotionGate(advanced.strategyPromotionGate || { candidates: [], summary: {} });
    renderResearchTaskBoard(advanced.researchTaskBoard || { tasks: [], summary: {} });
    renderStrategyLearningLoop(latestStrategyLearningLoopPayload);
    return advanced;
  })().finally(() => {
    advancedDataLoading = null;
  });
  return advancedDataLoading;
}

function loadDataForSection(sectionId) {
  if (sectionId === "localLab") {
    void loadSandboxReviewDataIfNeeded();
    void loadLocalLabEnrichmentIfNeeded();
  }
  if (sectionId === "mobileConsole") {
    void loadMobileStatusIfNeeded();
  }
  if (sectionId === "exchangeDemo") {
    void loadDemoWorkflow();
  }
  if (document.body.classList.contains("show-advanced")) {
    void loadAdvancedDataIfNeeded();
  }
}

async function refreshAll() {
  latestStrategyLearningLoopPayload = emptyStrategyLearningLoop;
  const [workflow, strategyLifecycle] = await Promise.all([
    getJsonSafe("/api/workflow", emptyWorkflow, 10000),
    getJsonSafe("/api/strategy-lifecycle", emptyStrategyLifecycle, 30000),
  ]);
  latestCoreConsolePayload = { ...latestCoreConsolePayload, workflow, strategyLifecycle };
  renderDualLayerWorkflow(workflow);
  renderStrategyLifecycle(strategyLifecycle);
  const corePayload = await loadJsonMap([
    { key: "strategies", url: "/api/strategies", fallback: { strategies: [] }, timeoutMs: 6000 },
    { key: "reports", url: "/api/reports", fallback: { reports: [] }, timeoutMs: 6000 },
    { key: "connection", url: "/api/mobile/connection-info", fallback: { notes: [], mobileStatusUrls: [] }, timeoutMs: 4000 },
    { key: "exchanges", url: "/api/exchanges", fallback: { sources: [] }, timeoutMs: 4000 },
    { key: "slots", url: "/api/strategy-slots", fallback: { slots: [] }, timeoutMs: 4000 },
    { key: "artifacts", url: "/api/strategy-artifacts", fallback: { artifacts: [], summary: {} }, timeoutMs: 8000 },
    { key: "paperTasks", url: "/api/paper-observation-tasks", fallback: { tasks: [], summary: {} }, timeoutMs: 8000 },
    { key: "usableStrategyCatalog", url: "/api/usable-strategy-catalog", fallback: { strategies: [], summary: {} }, timeoutMs: 6000 },
    { key: "sandboxDailyReport", url: "/api/local-sandbox/daily-report?limit=10", fallback: { reports: [], latestReport: { summary: {}, strategyHealthRows: [] } }, timeoutMs: 6000 },
    { key: "sandboxAutoRunner", url: "/api/local-sandbox/auto-runner", fallback: { autoRunner: {}, events: [] }, timeoutMs: 6000 },
    { key: "noKeyPreLive", url: "/api/no-key-pre-live", fallback: { summary: {}, strategyCards: [], publicCandidates: [], recentTickets: [] }, timeoutMs: 8000 },
    { key: "autoExecutionEngine", url: "/api/auto-execution-engine", fallback: { summary: {}, records: [], recentRuns: [] }, timeoutMs: 8000 },
    { key: "autoExecutionLifecycle", url: "/api/auto-execution-lifecycle", fallback: { summary: {}, lanes: [], records: [] }, timeoutMs: 8000 },
    { key: "autoExecutionReview", url: "/api/auto-execution-review", fallback: { summary: {}, blockedReasonBreakdown: [], activeHoldingQueue: [], closedResultsQueue: [], blockedReviewQueue: [], strategyLifecycleSummary: [] }, timeoutMs: 8000 },
    { key: "autoExecutionLearning", url: "/api/auto-execution-learning", fallback: { summary: {}, byStrategy: [], bySymbol: [], byDirection: [] }, timeoutMs: 8000 },
    { key: "exchangeDemo", url: "/api/exchange-demo/simulation", fallback: { summary: {}, modeCards: [], recentEvents: [], credentialStatus: {} }, timeoutMs: 12000 },
    { key: "liveCandidates", url: "/api/live-candidates", fallback: { summary: {}, packages: [], recentApprovalActions: [] }, timeoutMs: 6000 },
    { key: "riskProfiles", url: "/api/risk-profiles", fallback: { summary: {}, profiles: [], activeProfiles: {} }, timeoutMs: 6000 },
    { key: "liveCanary", url: "/api/live-canary", fallback: { summary: {}, runtimeGates: {}, runtime: {}, liveReleases: { summary: {} }, blockers: [] }, timeoutMs: 6000 },
    { key: "executionOutcomes", url: "/api/execution-outcomes", fallback: { summary: {}, records: [], quarantinedExecutionRecords: [] }, timeoutMs: 6000 },
    { key: "liveReadiness", url: "/api/live-readiness", fallback: { rows: [], summary: {} }, timeoutMs: 8000 },
    { key: "forwardReview", url: "/api/forward-review", fallback: { rows: [], summary: {} }, timeoutMs: 8000 },
  ], 4);
  latestCoreConsolePayload = { ...corePayload, workflow, strategyLifecycle };
  renderConsoleFromPayloads();
  updateCurrentSection();
  void loadSandboxReviewDataIfNeeded();
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
  const hashId = (window.location.hash || "#simpleConsole").replace("#", "");
  const requestedId = hashAliases[hashId] || (sectionLabels[hashId] ? hashId : "simpleConsole");
  if (requestedId !== hashId && window.location.hash) {
    window.location.hash = `#${requestedId}`;
    return;
  }
  const isPrimaryPage = primaryPageIds.includes(requestedId);
  if (isPrimaryPage) {
    document.querySelectorAll(".page-section").forEach((section) => {
      section.classList.toggle("active-page", section.id === requestedId);
    });
  } else if (document.body.classList.contains("show-advanced")) {
    document.querySelectorAll(".page-section").forEach((section) => {
      section.classList.remove("active-page");
    });
  } else {
    window.location.hash = "#simpleConsole";
    return;
  }
  document.querySelectorAll(".rail-item").forEach((item) => {
    item.classList.toggle("active", item.getAttribute("href") === `#${requestedId}`);
  });
  const backHomeButton = el("backHomeButton");
  if (backHomeButton) backHomeButton.hidden = requestedId === "simpleConsole";
  const current = el("currentSectionLabel");
  if (current) current.textContent = `当前：${sectionLabels[requestedId] || requestedId}`;
}

function scrollToOverview() {
  window.location.hash = "#simpleConsole";
  updateCurrentSection();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function importReportsNow(buttonId = "importButton") {
  const button = el(buttonId);
  if (button) button.disabled = true;
  try {
    await postJson("/api/import", {});
    await refreshAll();
  } finally {
    if (button) button.disabled = false;
  }
}

async function runLocalSandboxFromSimple() {
  const button = el("simpleRunSandboxButton");
  if (button) button.disabled = true;
  try {
    await runLocalSandboxNow();
  } finally {
    if (button) button.disabled = false;
  }
}

async function runLocalLabSandboxFromPanel() {
  const button = el("localLabRunSandboxButton");
  if (button) button.disabled = true;
  setText("localLabActionStatus", "正在切换本地沙盒持续观察状态...");
  try {
    await runLocalSandboxNow();
    setText("localLabActionStatus", "本地沙盒状态已更新。页面会继续显示虚拟观察数据，不连接交易所。");
  } catch (error) {
    setText("localLabActionStatus", `本地沙盒操作失败：${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

async function buildLocalLabDailyReport() {
  const button = el("localLabDailyReportButton");
  if (button) button.disabled = true;
  setText("localLabActionStatus", "正在生成本地沙盒日报...");
  try {
    await postJson("/api/local-sandbox/build-daily-report", {});
    await refreshAll();
    setText("localLabActionStatus", "已生成本地沙盒日报。");
  } catch (error) {
    setText("localLabActionStatus", `沙盒日报生成失败：${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

function getExchangeDemoTicketPayload() {
  return {
    instId: el("exchangeDemoInstIdInput")?.value || "BTC-USDT-SWAP",
    side: el("exchangeDemoSideInput")?.value || "buy",
    tdMode: el("exchangeDemoTdModeInput")?.value || "isolated",
    ordType: el("exchangeDemoOrdTypeInput")?.value || "market",
    size: el("exchangeDemoSizeInput")?.value || "",
    px: el("exchangeDemoPriceInput")?.value || "",
    notionalUsdt: Number(el("exchangeDemoNotionalInput")?.value || 250),
    ordId: el("exchangeDemoOrdIdInput")?.value || "",
    manualConfirm: el("exchangeDemoConfirmInput")?.value || "",
  };
}

function fillExchangeDemoTicketFromCandidate(candidate = null) {
  const row = candidate || latestExchangeDemoCandidate || {};
  if (!row.instId) {
    setText("exchangeDemoPipelineStatus", "暂无可填入候选。请先扫描 Demo 候选。");
    return;
  }
  const instInput = el("exchangeDemoInstIdInput");
  const sideInput = el("exchangeDemoSideInput");
  const ordInput = el("exchangeDemoOrdTypeInput");
  const notionalInput = el("exchangeDemoNotionalInput");
  const sizeInput = el("exchangeDemoSizeInput");
  if (instInput) instInput.value = row.instId;
  if (sideInput) sideInput.value = row.side || "buy";
  if (ordInput) ordInput.value = "market";
  if (notionalInput) notionalInput.value = String(Math.min(Number(notionalInput.value || 250), 250));
  if (sizeInput && !sizeInput.value) sizeInput.placeholder = "仍需手动填写 OKX sz";
  latestExchangeDemoCandidate = row;
  setText("exchangeDemoPipelineStatus", `已填入 ${row.instId} · ${row.side === "sell" ? "做空方向" : "做多方向"}。仍需手动填写 sz 和确认口令，不会自动提交订单。`);
}

async function scanExchangeDemoCandidates() {
  const button = el("exchangeDemoScanButton");
  if (button) button.disabled = true;
  setText("exchangeDemoPipelineStatus", "正在用 OKX 公共行情扫描 Demo 候选；不会使用 API Key 或下单。");
  try {
    const response = await postJson("/api/exchange-demo/scan-candidates", { limit: 10 });
    renderExchangeDemoSimulation(response.exchangeDemoSimulation || {});
    setText("exchangeDemoPipelineStatus", response.ok
      ? "候选扫描完成。可以填入首选票据，再人工决定是否做 Demo 演练。"
      : "候选扫描未通过，请查看阻塞原因。");
  } catch (error) {
    setText("exchangeDemoPipelineStatus", `候选扫描失败：${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

async function scanNoKeyPreLiveCandidates() {
  const button = el("noKeyScanButton");
  if (button) button.disabled = true;
  setText("noKeyActionStatus", "正在用公共行情扫描候选；不需要 API Key，不会下单。");
  try {
    const response = await postJson("/api/no-key-pre-live/scan", { limit: 12 });
    latestCoreConsolePayload = {
      ...latestCoreConsolePayload,
      noKeyPreLive: response.noKeyPreLive || {},
    };
    renderNoKeyPreLiveWorkbench(response.noKeyPreLive || {});
    const autoPayload = await getJsonSafe("/api/auto-execution-engine?fresh=1", { summary: {}, records: [], recentRuns: [] }, 8000);
    const lifecyclePayload = await getJsonSafe("/api/auto-execution-lifecycle?fresh=1", { summary: {}, lanes: [], records: [] }, 8000);
    const reviewPayload = await getJsonSafe("/api/auto-execution-review?fresh=1", { summary: {}, blockedReasonBreakdown: [], activeHoldingQueue: [], closedResultsQueue: [], blockedReviewQueue: [], strategyLifecycleSummary: [] }, 8000);
    const learningPayload = await getJsonSafe("/api/auto-execution-learning?fresh=1", { summary: {}, byStrategy: [], bySymbol: [], byDirection: [] }, 8000);
    latestCoreConsolePayload = {
      ...latestCoreConsolePayload,
      autoExecutionEngine: autoPayload || {},
      autoExecutionLifecycle: lifecyclePayload || {},
      autoExecutionReview: reviewPayload || {},
      autoExecutionLearning: learningPayload || {},
    };
    renderAutoExecutionEngine(autoPayload || {});
    renderAutoExecutionLifecycle(lifecyclePayload || {});
    renderAutoExecutionReview(reviewPayload || {});
    renderAutoExecutionLearning(learningPayload || {});
    setText("noKeyActionStatus", response.ok
      ? "公共行情扫描完成。可以直接运行自动执行引擎生成本地生命周期记录。"
      : "公共行情扫描未完成，请查看候选状态。");
  } catch (error) {
    setText("noKeyActionStatus", `公共行情扫描失败：${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

async function createNoKeyPreLiveTicket() {
  const button = el("noKeyCreateTicketButton");
  if (button) button.disabled = true;
  const candidate = latestNoKeyPreLiveCandidate || {};
  setText("noKeyActionStatus", "正在生成本地观察票据；不会提交 Demo 或实盘订单。");
  try {
    const response = await postJson("/api/no-key-pre-live/create-ticket", {
      candidateId: candidate.candidateId || "",
      notionalUsdt: Number(el("noKeyTicketNotionalInput")?.value || 1000),
    });
    latestCoreConsolePayload = {
      ...latestCoreConsolePayload,
      noKeyPreLive: response.noKeyPreLive || {},
    };
    renderNoKeyPreLiveWorkbench(response.noKeyPreLive || {});
    setText("noKeyActionStatus", response.ok
      ? "已保存本地观察票据。它只是预实盘复核记录，不是交易所订单。"
      : "票据已按阻塞状态保存或未找到可用候选；请先完成公共行情扫描。");
  } catch (error) {
    setText("noKeyActionStatus", `本地观察票据生成失败：${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

async function runAutoExecutionEngine() {
  const button = el("autoExecutionRunButton");
  if (button) button.disabled = true;
  setText("autoExecutionStatus", "正在运行策略仲裁和本地自动生命周期记录；不会提交 Demo 或实盘订单。");
  try {
    const response = await postJson("/api/auto-execution-engine/run", {
      maxExecutions: 5,
      notionalUsdt: Number(el("noKeyTicketNotionalInput")?.value || 1000),
      refreshPublicScan: true,
    });
    const lifecyclePayload = await getJsonSafe("/api/auto-execution-lifecycle?fresh=1", { summary: {}, lanes: [], records: [] }, 8000);
    const reviewPayload = await getJsonSafe("/api/auto-execution-review?fresh=1", { summary: {}, blockedReasonBreakdown: [], activeHoldingQueue: [], closedResultsQueue: [], blockedReviewQueue: [], strategyLifecycleSummary: [] }, 8000);
    const learningPayload = await getJsonSafe("/api/auto-execution-learning?fresh=1", { summary: {}, byStrategy: [], bySymbol: [], byDirection: [] }, 8000);
    latestCoreConsolePayload = {
      ...latestCoreConsolePayload,
      noKeyPreLive: response.noKeyPreLive || latestCoreConsolePayload.noKeyPreLive,
      autoExecutionEngine: response.autoExecutionEngine || {},
      autoExecutionLifecycle: lifecyclePayload || {},
      autoExecutionReview: reviewPayload || {},
      autoExecutionLearning: learningPayload || {},
    };
    if (response.noKeyPreLive) renderNoKeyPreLiveWorkbench(response.noKeyPreLive);
    renderAutoExecutionEngine(response.autoExecutionEngine || {});
    renderAutoExecutionLifecycle(lifecyclePayload || {});
    renderAutoExecutionReview(reviewPayload || {});
    renderAutoExecutionLearning(learningPayload || {});
    const selected = response.run?.selectedCount ?? 0;
    const blocked = response.run?.blockedCount ?? 0;
    setText("autoExecutionStatus", `自动执行引擎完成：本地观察 ${selected} 条，阻塞 ${blocked} 条；实盘和 Demo 订单仍然锁定。`);
  } catch (error) {
    setText("autoExecutionStatus", `自动执行引擎失败：${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

async function advanceAutoExecutionLifecycle() {
  const button = el("autoLifecycleAdvanceButton");
  if (button) button.disabled = true;
  setText("autoLifecycleAdvanceStatus", "正在读取 OKX 公共行情并推进本地观察；不会创建 Demo 或实盘订单。");
  try {
    const response = await postJson("/api/auto-execution-lifecycle/advance", { maxRecords: 20 });
    const advance = response.lifecycleAdvance || {};
    const summary = advance.summary || {};
    latestCoreConsolePayload = {
      ...latestCoreConsolePayload,
      autoExecutionEngine: response.autoExecutionEngine || {},
      autoExecutionLifecycle: response.autoExecutionLifecycle || {},
      autoExecutionReview: response.autoExecutionReview || {},
      autoExecutionLearning: response.autoExecutionLearning || {},
    };
    renderAutoExecutionEngine(response.autoExecutionEngine || {});
    renderAutoExecutionLifecycle(response.autoExecutionLifecycle || {});
    renderAutoExecutionReview(response.autoExecutionReview || {});
    renderAutoExecutionLearning(response.autoExecutionLearning || {});
    setText(
      "autoLifecycleAdvanceStatus",
      `推进完成：建立基准 ${summary.referencesInitialized ?? 0} 条，更新价格 ${summary.pricesMarked ?? 0} 条，闭合 ${summary.closedThisRun ?? 0} 条，失败 ${summary.failedRecords ?? 0} 条。`,
    );
  } catch (error) {
    setText("autoLifecycleAdvanceStatus", `生命周期推进失败：${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

async function runExchangeDemoReadOnlyCheck() {
  const button = el("exchangeDemoReadOnlyButton");
  if (button) button.disabled = true;
  setText("exchangeDemoActionStatus", "正在执行 OKX Demo 只读检查；默认不下单、不撤单。");
  try {
    const response = await postJson("/api/exchange-demo/read-only-check", {});
    renderExchangeDemoSimulation(response.exchangeDemoSimulation || {});
    setText("exchangeDemoActionStatus", response.ok
      ? "OKX Demo 账户配置、模拟余额和模拟持仓只读检查通过。连接烟测与正式策略自动化仍是两道独立闸门。"
      : `只读检查被阻塞或失败：${(response.event?.blockers || response.rejectionReasons || []).map(translateExchangeDemoBlocker).join(" · ") || "请查看最近事件"}`);
  } catch (error) {
    setText("exchangeDemoActionStatus", `只读检查失败：${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

async function submitExchangeDemoOrder() {
  const button = el("exchangeDemoSubmitButton");
  if (button) button.disabled = true;
  setText("exchangeDemoActionStatus", "正在提交 OKX Demo 连接烟测订单；该结果不计入策略证据，也不会创建 Demo Release。");
  try {
    const response = await postJson("/api/exchange-demo/order", getExchangeDemoTicketPayload());
    renderExchangeDemoSimulation(response.exchangeDemoSimulation || {});
    setText("exchangeDemoActionStatus", response.ok
      ? "OKX Demo 连接烟测订单已提交。请复核返回结果；正式策略自动化状态不会因此改变。"
      : `连接烟测订单未提交：${(response.rejectionReasons || response.event?.blockers || []).map(translateExchangeDemoBlocker).join(" · ") || "请查看最近事件"}`);
  } catch (error) {
    setText("exchangeDemoActionStatus", `Demo 订单请求失败：${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

async function runExchangeDemoEmergencyStop() {
  const button = el("exchangeDemoEmergencyButton");
  if (button) button.disabled = true;
  setText("exchangeDemoActionStatus", "正在保存紧急停止演练；没有 ordId 或确认口令时只保存本地演练记录。");
  try {
    const response = await postJson("/api/exchange-demo/emergency-stop", getExchangeDemoTicketPayload());
    renderExchangeDemoSimulation(response.exchangeDemoSimulation || {});
    setText("exchangeDemoActionStatus", response.exchangeCancelSent
      ? "已向 OKX Demo 发出撤单请求。请复核最近事件。"
      : "已保存本地紧急停止演练，没有向交易所发送撤单请求。");
  } catch (error) {
    setText("exchangeDemoActionStatus", `紧急停止演练失败：${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

async function approveSelectedLiveCandidate() {
  const button = el("approveLiveCandidateButton");
  const selected = getSelectedLiveCandidate();
  if (!selected) {
    setText("liveApprovalActionStatus", "没有可批准的 Live Candidate。实盘保持锁定。");
    return;
  }
  button.disabled = true;
  setText("liveApprovalActionStatus", "正在写入 checksum 绑定的人工批准记录；不会启动实盘。 ");
  try {
    const response = await postJson("/api/live-candidates/approve", {
      liveCandidatePackageId: selected.liveCandidatePackageId,
      packageHash: selected.packageHash,
      confirmation: el("liveApprovalConfirmation").value,
      actor: "user_manual",
    });
    el("liveApprovalConfirmation").value = "";
    renderLiveCandidateStatus(response.liveCandidates || {});
    setText("liveApprovalActionStatus", "已批准进入未来发布复核。实盘适配器仍不存在，执行仍为关闭。");
  } catch (error) {
    setText("liveApprovalActionStatus", `批准失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function revokeSelectedLiveCandidate() {
  const button = el("revokeLiveCandidateButton");
  const selected = getSelectedLiveCandidate();
  if (!selected) {
    setText("liveApprovalActionStatus", "没有可撤销的 Live Candidate 批准记录。");
    return;
  }
  button.disabled = true;
  setText("liveApprovalActionStatus", "正在追加撤销记录；历史审批不会被删除。");
  try {
    const response = await postJson("/api/live-candidates/revoke", {
      liveCandidatePackageId: selected.liveCandidatePackageId,
      packageHash: selected.packageHash,
      actor: "user_manual",
    });
    renderLiveCandidateStatus(response.liveCandidates || {});
    setText("liveApprovalActionStatus", "已撤销当前 checksum 的批准。实盘继续锁定。");
  } catch (error) {
    setText("liveApprovalActionStatus", `撤销失败：${error.message}`);
  } finally {
    button.disabled = false;
  }
}

function setAdvancedMode(enabled) {
  document.body.classList.toggle("show-advanced", Boolean(enabled));
  const button = el("toggleAdvancedModeButton");
  if (button) {
    button.textContent = enabled ? "收起高级研究" : "展开高级研究";
    button.classList.toggle("is-running", Boolean(enabled));
  }
  try {
    window.localStorage.setItem("alphapilot.showAdvancedMode", enabled ? "1" : "0");
  } catch {
    // Local storage may be unavailable in strict browser modes; UI can still work.
  }
  updateCurrentSection();
}

function toggleAdvancedMode() {
  setAdvancedMode(!document.body.classList.contains("show-advanced"));
}

el("refreshButton").addEventListener("click", refreshAll);
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-issue-guidance-key]");
  if (!button || !issueController) return;
  issueController.open(button.dataset.issueGuidanceKey || "");
});
el("simpleRefreshButton")?.addEventListener("click", refreshAll);
el("workflowRefreshButton")?.addEventListener("click", refreshWorkflow);
el("workflowRunAllButton")?.addEventListener("click", () => runDualLayerWorkflowAction("run-all-awaiting"));
el("simpleConsole")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-workflow-action]");
  if (!button) return;
  const action = button.dataset.workflowAction;
  const workflowRunId = button.dataset.workflowRunId || "";
  const strategyVersionId = button.dataset.strategyVersionId || "";
  button.disabled = true;
  void runDualLayerWorkflowAction(action, { workflowRunId, strategyVersionId }).finally(() => {
    button.disabled = false;
  });
});
["localLifecycleList", "demoLifecycleList"].forEach((targetId) => {
  el(targetId)?.addEventListener("click", (event) => {
    const button = event.target.closest('[data-lifecycle-action="optimize"]');
    if (!button) return;
    const strategyId = button.dataset.strategyId || "";
    const item = (latestStrategyLifecyclePayload?.items || []).find((row) => row.strategyId === strategyId);
    if (item) openStrategyOptimizationDialog(item);
  });
});
el("strategyOptimizationForm")?.addEventListener("submit", submitStrategyOptimization);
el("strategyOptimizationCloseButton")?.addEventListener("click", closeStrategyOptimizationDialog);
el("strategyOptimizationCancelButton")?.addEventListener("click", closeStrategyOptimizationDialog);
el("strategyOptimizationDialog")?.addEventListener("click", (event) => {
  if (event.target === event.currentTarget) closeStrategyOptimizationDialog();
});
el("demoOverrideForm")?.addEventListener("submit", submitDemoOverride);
el("demoOverrideCloseButton")?.addEventListener("click", closeDemoOverrideDialog);
el("demoOverrideCancelButton")?.addEventListener("click", closeDemoOverrideDialog);
el("demoOverrideDialog")?.addEventListener("click", (event) => {
  if (event.target === event.currentTarget) closeDemoOverrideDialog();
});
el("weaknessActionStatusFilter")?.addEventListener("change", (event) => {
  weaknessActionFilters.status = event.target.value || "active";
  renderWeaknessActionBoard(latestWeaknessActionBoardPayload);
});
el("weaknessActionPriorityFilter")?.addEventListener("change", (event) => {
  weaknessActionFilters.priority = event.target.value || "all";
  renderWeaknessActionBoard(latestWeaknessActionBoardPayload);
});
el("importButton").addEventListener("click", () => importReportsNow("importButton"));
el("simpleImportButton")?.addEventListener("click", () => importReportsNow("simpleImportButton"));
el("simpleRunSandboxButton")?.addEventListener("click", runLocalSandboxFromSimple);
el("localLabRunSandboxButton")?.addEventListener("click", runLocalLabSandboxFromPanel);
el("localLabDailyReportButton")?.addEventListener("click", buildLocalLabDailyReport);
el("localLabRefreshButton")?.addEventListener("click", refreshAll);
el("exchangeDemoReadOnlyButton")?.addEventListener("click", runExchangeDemoReadOnlyCheck);
el("demoRuntimeLauncherButton")?.addEventListener("click", launchOkxDemoRuntime);
el("demoWorkflowRefreshButton")?.addEventListener("click", () => loadDemoWorkflow(true));
el("exchangeDemo")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-demo-workflow-action]");
  if (!button) return;
  const action = button.dataset.demoWorkflowAction || "";
  const strategyId = button.dataset.strategyId || "";
  if (action === "open_demo_override") {
    openDemoOverrideDialog(strategyId);
    return;
  }
  const extra = action === demoWorkflowActions.updateSettings.action
    ? { maxConcurrentSymbols: Number(button.closest(".demo-workflow-card")?.querySelector("[data-demo-symbol-limit]")?.value || 1) }
    : {};
  button.disabled = true;
  void runDemoWorkflowAction(action, strategyId, extra).finally(() => {
    button.disabled = false;
  });
});
el("exchangeDemoScanButton")?.addEventListener("click", scanExchangeDemoCandidates);
el("exchangeDemoFillTicketButton")?.addEventListener("click", () => fillExchangeDemoTicketFromCandidate());
el("noKeyScanButton")?.addEventListener("click", scanNoKeyPreLiveCandidates);
el("autoExecutionRunButton")?.addEventListener("click", runAutoExecutionEngine);
el("autoLifecycleAdvanceButton")?.addEventListener("click", advanceAutoExecutionLifecycle);
el("noKeyCreateTicketButton")?.addEventListener("click", createNoKeyPreLiveTicket);
el("exchangeDemoSubmitButton")?.addEventListener("click", submitExchangeDemoOrder);
el("exchangeDemoEmergencyButton")?.addEventListener("click", runExchangeDemoEmergencyStop);
el("approveLiveCandidateButton")?.addEventListener("click", approveSelectedLiveCandidate);
el("revokeLiveCandidateButton")?.addEventListener("click", revokeSelectedLiveCandidate);
el("riskProfileEnvironment")?.addEventListener("change", () => {
  selectedRiskProfileId = null;
  renderRiskProfiles(latestRiskProfilePayload || {});
});
el("riskProfileSelector")?.addEventListener("change", (event) => {
  selectedRiskProfileId = event.target.value || null;
  renderRiskProfiles(latestRiskProfilePayload || {});
});
el("saveRiskProfileButton")?.addEventListener("click", saveRiskProfileVersion);
el("activateRiskProfileButton")?.addEventListener("click", activateRiskProfileVersion);
el("rollbackRiskProfileButton")?.addEventListener("click", rollbackRiskProfileVersion);
el("liveCanaryReconcileButton")?.addEventListener("click", reconcileLiveCanary);
el("liveCanaryArmButton")?.addEventListener("click", armLiveCanary);
el("liveCanaryKillButton")?.addEventListener("click", stopLiveCanary);
el("exportExecutionOutcomesButton")?.addEventListener("click", exportExecutionOutcomes);
el("toggleAdvancedModeButton")?.addEventListener("click", () => {
  toggleAdvancedMode();
  if (document.body.classList.contains("show-advanced")) void loadAdvancedDataIfNeeded();
});
el("runResearchPipelineButton")?.addEventListener("click", runResearchPipeline);

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
el("runLocalSandboxButton")?.addEventListener("click", runLocalSandboxNow);
el("buildSandboxDailyReportButton")?.addEventListener("click", buildSandboxDailyReportNow);
el("saveSandboxAutoRunnerButton")?.addEventListener("click", saveSandboxAutoRunnerSettings);
el("runSandboxAutoOnceButton")?.addEventListener("click", runSandboxAutoRunnerOnce);
el("refreshForwardReviewButton")?.addEventListener("click", refreshForwardReview);
el("runPreLiveLifecyclePreviewButton")?.addEventListener("click", runPreLiveLifecyclePreview);
el("runTestnetDrillButton")?.addEventListener("click", runTestnetDrill);
el("runTestnetSmallOrderButton")?.addEventListener("click", runTestnetSmallOrderSimulation);
el("strategyQuickLogType").addEventListener("change", () => {
  const logType = el("strategyQuickLogType").value || "no_signal";
  el("strategyQuickSignalObserved").checked = ["signal_seen", "rule_matched"].includes(logType);
  el("strategyQuickRuleMatched").checked = logType === "rule_matched";
});
el("strategyQuickLogButton").addEventListener("click", async () => {
  const task = latestStrategyPlaybookTask;
  const taskId = task?.taskId || "";
  if (!taskId) {
    el("strategyQuickLogStatus").textContent = "请先选择一条纸面观察策略。";
    return;
  }
  const button = el("strategyQuickLogButton");
  button.disabled = true;
  el("strategyQuickLogStatus").textContent = "正在保存本地观察日志...";
  try {
    await postJson("/api/paper-observation-log", {
      artifactId: taskId,
      logType: el("strategyQuickLogType")?.value || "no_signal",
      signalObserved: Boolean(el("strategyQuickSignalObserved")?.checked),
      ruleMatched: Boolean(el("strategyQuickRuleMatched")?.checked),
      outcome: el("strategyQuickOutcome")?.value || "",
      note: el("strategyQuickNote")?.value || "",
    });
    el("strategyQuickOutcome").value = "";
    el("strategyQuickNote").value = "";
    await refreshAll();
    el("strategyQuickLogStatus").textContent = "已保存本地纸面观察日志；不会创建订单。";
  } catch (error) {
    el("strategyQuickLogStatus").textContent = `保存失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
});
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
function loadCurrentSectionData() {
  const hashId = (window.location.hash || "#simpleConsole").replace("#", "");
  const requestedId = hashAliases[hashId] || (sectionLabels[hashId] ? hashId : "simpleConsole");
  loadDataForSection(requestedId);
}

window.addEventListener("scroll", updateCurrentSection, { passive: true });
window.addEventListener("hashchange", () => {
  updateCurrentSection();
  loadCurrentSectionData();
  window.setTimeout(() => issueController?.presentHighestPriority(currentPrimaryPageId()), 0);
});

try {
  const lifecycleLayoutVersion = "v13.15.1";
  const storedLayoutVersion = window.localStorage.getItem("alphapilot.lifecycleLayoutVersion");
  if (storedLayoutVersion !== lifecycleLayoutVersion) {
    window.localStorage.setItem("alphapilot.lifecycleLayoutVersion", lifecycleLayoutVersion);
    window.localStorage.setItem("alphapilot.showAdvancedMode", "0");
    setAdvancedMode(false);
  } else {
    setAdvancedMode(window.localStorage.getItem("alphapilot.showAdvancedMode") === "1");
  }
} catch {
  setAdvancedMode(false);
}

refreshAll().catch((error) => {
  el("strategyList").innerHTML = `<div class="item">加载失败：${error.message}</div>`;
});
updateCurrentSection();
loadCurrentSectionData();
