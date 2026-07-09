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
  simpleConsole: "首页",
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
  const sandboxRows = buildSandboxSimulationRows(
    buildUsableCatalogObservationTasks(usableStrategyCatalog),
    Array.isArray(dailyReport.strategyHealthRows) ? dailyReport.strategyHealthRows : [],
  );
  const totalCapital = sandboxRows.reduce((sum, row) => sum + Number(row.capital || 0), 0);
  const totalEquity = sandboxRows.reduce((sum, row) => sum + Number(row.equity || 0), 0);
  const totalClosedSamples = sandboxRows.reduce((sum, row) => sum + Number(row.closedPaperSampleCount || 0), 0);
  const lowCount = catalogSummary.lowFrequencyCount ?? rows.filter((row) => row.frequencyBucket !== "short_cycle").length;
  const shortCount = catalogSummary.shortCycleCount ?? rows.filter((row) => row.frequencyBucket === "short_cycle").length;
  const readinessSummary = liveReadiness?.summary || {};
  const executionLocked = !mobile?.safetyBoundary?.orderCreationAllowed;

  setText("simpleConsoleOneLine", rows.length
    ? `当前整理出 ${rows.length} 条本地可观察策略：低频 ${lowCount} 条，短周期 ${shortCount} 条。先用沙盒累计样本，再决定是否升级。`
    : "还没有可观察策略目录。请先导入最新量化报告。");
  const badge = el("simpleConsoleBadge");
  if (badge) {
    badge.className = `status-pill ${runnerState.enabled ? "ok" : "warn"}`;
    badge.textContent = runnerState.enabled ? "沙盒运行中" : "沙盒未开启";
  }

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
  const button = el("runLocalSandboxButton");
  if (!button) return;
  button.classList.toggle("is-running", Boolean(enabled));
  button.dataset.running = enabled ? "true" : "false";
  button.textContent = enabled ? "沙盒运行中 · 点击停止" : "运行本地沙盒";
  button.title = enabled
    ? `本地沙盒正在持续观察，当前状态：${runnerStatus || "waiting"}。点击后停止自动观察。`
    : "点击后开启本地沙盒持续观察，并立即运行一轮。";
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
  el("sandboxAutoIntervalInput").value = String(runner.intervalMinutes || 360);
  el("sandboxAutoMaxRunsInput").value = String(runner.maxRunsPerDay || 4);
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
  return `<span class="badge ${tone}">${escapeHtml(row?.statusLabel || "--")} ? ${formatNumber(row?.readinessScore, 0)}?</span>`;
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
  el("liveReadinessStatus").textContent = summary.manualTicketReadyCount > 0 ? "??????" : "????";
  el("liveReadinessStatus").className = `status-pill ${summary.manualTicketReadyCount > 0 ? "warn" : "danger"}`;
  el("liveReadinessNextAction").textContent = summary.nextAction || "?? 7?10? ????????????";

  el("liveReadinessList").innerHTML = rows.map((row) => {
    const metrics = row.metrics || {};
    const quality = row.quality || {};
    const blockers = Array.isArray(row.blockers) ? row.blockers : [];
    const passed = Array.isArray(row.passedChecks) ? row.passedChecks : [];
    const buttonDisabled = row.manualTicketAllowed ? "" : "disabled";
    const buttonLabel = row.manualTicketAllowed ? "??????" : "????";
    return `
      <div class="live-readiness-row">
        <div class="live-readiness-row-head">
          <div>
            <strong>${escapeHtml(row.title || row.taskId || "--")}</strong>
            <small>${escapeHtml(row.taskId || "--")} ? ${escapeHtml(row.timeframe || "--")} ? ?? ${formatDate(quality.latestLogAt)}</small>
          </div>
          ${liveReadinessBadge(row)}
        </div>
        <div class="artifact-metrics">
          <span>?? ${metrics.tradeCount ?? metrics.filledSignalCount ?? "--"}/${thresholds.minHistoricalTrades ?? "--"}</span>
          <span>?? ${formatPercent(metrics.winRatePct)}</span>
          <span>PF ${formatNumber(metrics.profitFactor)}</span>
          <span>??? ${formatNumber(metrics.rewardRiskRatio || metrics.targetRewardRiskRatio)}</span>
          <span>?? ${formatPercent(metrics.maxDrawdownPct)}</span>
          <span>?? ${formatNumber(quality.qualityScore, 0)}</span>
          <span>?? ${quality.logCount ?? 0}</span>
          <span>?? ${quality.ruleMatchedCount ?? 0}</span>
          <span>?? ${quality.closedPaperSampleCount ?? 0}</span>
        </div>
        <div class="live-readiness-blockers">
          ${(blockers.length ? blockers : ["??????????????????"])
            .slice(0, 8)
            .map((item) => `<small>${escapeHtml(item)}</small>`)
            .join("")}
        </div>
        <details class="live-readiness-checks">
          <summary>?????????????</summary>
          <div>
            <strong>???</strong>
            ${(passed.length ? passed : ["?????"])
              .map((item) => `<small>${escapeHtml(item)}</small>`)
              .join("")}
          </div>
          <div>
            <strong>?????</strong>
            ${(row.hardExecutionBlockers || [])
              .map((item) => `<small>${escapeHtml(item)}</small>`)
              .join("")}
          </div>
        </details>
        <div class="live-readiness-ticket-line">
          <span>${escapeHtml(row.nextAction || "???????")}</span>
          <button type="button" data-live-ticket="${escapeHtml(row.taskId || "")}" ${buttonDisabled}>${buttonLabel}</button>
        </div>
      </div>
    `;
  }).join("") || '<div class="live-readiness-empty">????????????? Quant Engine ??????????</div>';

  el("liveTicketList").innerHTML = tickets.slice(0, 10).map((ticket) => `
    <div class="live-ticket-row">
      <strong>${escapeHtml(ticket.title || ticket.taskId || "--")}</strong>
      <small>${formatDate(ticket.createdAt)} ? ${escapeHtml(ticket.status || "draft_manual_review")}</small>
      <div class="artifact-metrics">
        <span>?? ${formatNumber(ticket.readinessScore, 0)}</span>
        <span>?? ${escapeHtml(ticket.timeframe || "--")}</span>
        <span>?? ${escapeHtml(ticket.selectedPair || "?????")}</span>
      </div>
      <div>?????????????????????????????????</div>
    </div>
  `).join("") || '<div class="live-readiness-empty">?????????????????</div>';

  el("liveReadinessList").querySelectorAll("[data-live-ticket]").forEach((button) => {
    button.addEventListener("click", async () => {
      const taskId = button.getAttribute("data-live-ticket") || "";
      button.disabled = true;
      try {
        await postJson("/api/manual-execution-ticket", {
          taskId,
          note: "?????????????????????????",
        });
        await refreshAll();
      } catch (error) {
        el("liveReadinessNextAction").textContent = `??????${error.message}??????????`;
      } finally {
        button.disabled = false;
      }
    });
  });
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
      intervalMinutes: Number(el("sandboxAutoIntervalInput")?.value || 360),
      maxRunsPerDay: Number(el("sandboxAutoMaxRunsInput")?.value || 4),
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

async function refreshAll() {
  const core = await loadJsonMap([
    { key: "strategies", url: "/api/strategies", fallback: { strategies: [] } },
    { key: "reports", url: "/api/reports", fallback: { reports: [] } },
    { key: "mobile", url: "/api/mobile/status", fallback: {} },
    { key: "connection", url: "/api/mobile/connection-info", fallback: { notes: [], mobileStatusUrls: [] } },
    { key: "audit", url: "/api/audit", fallback: { events: [] } },
    { key: "exchanges", url: "/api/exchanges", fallback: { sources: [] } },
    { key: "slots", url: "/api/strategy-slots", fallback: { slots: [] } },
    { key: "artifacts", url: "/api/strategy-artifacts", fallback: { artifacts: [], summary: {} } },
    { key: "paperTasks", url: "/api/paper-observation-tasks", fallback: { tasks: [], summary: {} } },
    { key: "usableStrategyCatalog", url: "/api/usable-strategy-catalog", fallback: { strategies: [], summary: {} } },
    { key: "sandboxDailyReport", url: "/api/local-sandbox/daily-report?limit=10", fallback: { reports: [], latestReport: { summary: {}, strategyHealthRows: [] } } },
    { key: "sandboxAutoRunner", url: "/api/local-sandbox/auto-runner", fallback: { autoRunner: {}, events: [] } },
    { key: "sandboxQualityCenter", url: "/api/local-sandbox/quality-center", fallback: { summary: {}, strategies: [], readonlyPreparation: {} }, timeoutMs: 12000 },
    { key: "sandboxConcentrationReview", url: "/api/local-sandbox/concentration-review", fallback: { summary: {}, strategies: [], variantGroups: [] }, timeoutMs: 12000 },
    { key: "sandboxResultReview", url: "/api/local-sandbox/result-review", fallback: { summary: {}, strategies: [], familyReviews: [] }, timeoutMs: 12000 },
    { key: "strategyAssetPlaybook", url: "/api/strategy-asset-playbook", fallback: { summary: {}, strategies: [], executionReadiness: {} }, timeoutMs: 30000 },
    { key: "liveReadiness", url: "/api/live-readiness", fallback: { rows: [], summary: {} } },
    { key: "forwardReview", url: "/api/forward-review", fallback: { rows: [], summary: {} } },
  ], 4);
  const strategies = core.strategies || { strategies: [] };
  const reports = core.reports || { reports: [] };
  const mobile = core.mobile || {};
  const connection = core.connection || { notes: [], mobileStatusUrls: [] };
  const audit = core.audit || { events: [] };
  const exchanges = core.exchanges || { sources: [] };
  const slots = core.slots || { slots: [] };
  const artifacts = core.artifacts || { artifacts: [], summary: {} };
  const paperTasks = core.paperTasks || { tasks: [], summary: {} };
  const usableStrategyCatalog = core.usableStrategyCatalog || { strategies: [], summary: {} };
  const sandboxDailyReport = core.sandboxDailyReport || { reports: [], latestReport: { summary: {}, strategyHealthRows: [] } };
  const sandboxAutoRunner = core.sandboxAutoRunner || { autoRunner: {}, events: [] };
  const sandboxQualityCenter = core.sandboxQualityCenter || { summary: {}, strategies: [], readonlyPreparation: {} };
  const sandboxConcentrationReview = core.sandboxConcentrationReview || { summary: {}, strategies: [], variantGroups: [] };
  const sandboxResultReview = core.sandboxResultReview || { summary: {}, strategies: [], familyReviews: [] };
  const strategyAssetPlaybook = core.strategyAssetPlaybook || { summary: {}, strategies: [], executionReadiness: {} };
  const liveReadiness = core.liveReadiness || { rows: [], summary: {} };
  const forwardReview = core.forwardReview || { rows: [], summary: {} };
  const emptySimulationBridge = { summary: {}, observationTasks: [] };
  const emptySimulationReview = { queue: [], summary: {} };
  const emptyStrategyLearningLoop = { summary: {}, refactorCandidates: [], experimentSpecs: [] };
  const strategyItems = strategies.strategies || [];
  const reportItems = reports.reports || [];
  latestStrategyLearningLoopPayload = emptyStrategyLearningLoop;
  renderSimpleConsole(strategyItems, reportItems, mobile, usableStrategyCatalog, sandboxDailyReport, sandboxAutoRunner, liveReadiness, emptySimulationBridge, emptySimulationReview, sandboxQualityCenter, sandboxConcentrationReview, sandboxResultReview, strategyAssetPlaybook);
  renderCommandCenter(strategyItems, reportItems, mobile);
  renderRuntimeMonitor(strategyItems, mobile);
  renderStrategies(strategyItems);
  renderReports(reportItems);
  renderAudit(audit.events || []);
  renderExchanges(exchanges.sources || [], mobile);
  renderStrategySlots(slots.slots || []);
  renderStrategyArtifacts(artifacts);
  renderUsableStrategyCatalog(usableStrategyCatalog);
  renderSimulationReview(emptySimulationReview);
  renderClosedSampleReplay({ samples: [], summary: {} });
  renderWeaknessActionBoard({ actions: [], summary: {} });
  renderResearchExecutionPipeline({ summary: {}, stages: [], actions: [] });
  renderTestnetDesignBoundary({ summary: {}, checklist: [], disabledActions: [] });
  renderPreLivePreparationPack({ summary: {}, rehearsalSummary: {}, preLiveClosureReport: [], recentRehearsals: [] });
  renderTestnetDrill({ summary: {}, strategies: [], orderLifecycle: [], riskTemplate: [] });
  renderTestnetAuditPack({ summary: {}, auditItems: [], criticalBlockers: [] });
  renderTestnetPermissionCheck({ summary: {}, checks: [], referenceInputs: [] });
  renderTestnetSmallOrderSimulation({ summary: {}, defaultTicket: {}, orderPath: [], recentSimulations: [] });
  renderStrategyPromotionGate({ candidates: [], summary: {} });
  renderResearchTaskBoard({ tasks: [], summary: {} });
  renderStrategyLearningLoop(emptyStrategyLearningLoop);
  renderSandboxSimulationLane(
    buildUsableCatalogObservationTasks(usableStrategyCatalog),
    sandboxDailyReport?.latestReport?.strategyHealthRows || [],
  );
  renderSandboxDailyReport(sandboxDailyReport);
  renderSandboxAutoRunner(sandboxAutoRunner);
  renderLiveReadiness(liveReadiness);
  renderForwardReview(forwardReview);
  renderStrategyPlaybook(strategyItems, mobile, emptyStrategyLearningLoop);
  renderForwardValidation(mobile.forwardValidation);
  renderPaperObservationTasks(paperTasks);
  renderMobileConnectionInfo(connection);
  el("mobilePreview").textContent = JSON.stringify(mobile, null, 2);

  const advanced = await loadJsonMap([
    { key: "candidateQueue", url: "/api/candidate-queue", fallback: { strategies: [], summary: {} } },
    { key: "shortCycleCandidates", url: "/api/short-cycle-candidates", fallback: { candidates: [], summary: {} } },
    { key: "simulationBridge", url: "/api/simulation-bridge", fallback: { summary: {}, observationTasks: [] } },
    { key: "simulationReview", url: "/api/simulation-review", fallback: { queue: [], summary: {} } },
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
    { key: "strategyLearningLoop", url: "/api/strategy-learning-loop", fallback: emptyStrategyLearningLoop, timeoutMs: 12000 },
  ], 3);
  const simulationBridge = advanced.simulationBridge || emptySimulationBridge;
  const simulationReview = advanced.simulationReview || emptySimulationReview;
  const strategyLearningLoop = advanced.strategyLearningLoop || emptyStrategyLearningLoop;
  latestStrategyLearningLoopPayload = strategyLearningLoop;
  renderSimpleConsole(strategyItems, reportItems, mobile, usableStrategyCatalog, sandboxDailyReport, sandboxAutoRunner, liveReadiness, simulationBridge, simulationReview, sandboxQualityCenter, sandboxConcentrationReview, sandboxResultReview, strategyAssetPlaybook);
  renderCandidateQueue(advanced.candidateQueue || { strategies: [], summary: {} });
  renderShortCycleCandidatePool(advanced.shortCycleCandidates || { candidates: [], summary: {} });
  renderSimulationReview(simulationReview);
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
  renderStrategyLearningLoop(strategyLearningLoop);
  renderStrategyPlaybook(strategyItems, mobile, strategyLearningLoop);
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
    .filter((section) => section && section.offsetParent !== null);
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
  document.getElementById("simpleConsole")?.scrollIntoView({ behavior: "smooth", block: "start" });
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
}

function toggleAdvancedMode() {
  setAdvancedMode(!document.body.classList.contains("show-advanced"));
}

el("refreshButton").addEventListener("click", refreshAll);
el("simpleRefreshButton")?.addEventListener("click", refreshAll);
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
el("toggleAdvancedModeButton")?.addEventListener("click", toggleAdvancedMode);
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
window.addEventListener("scroll", updateCurrentSection, { passive: true });
window.addEventListener("hashchange", updateCurrentSection);

try {
  setAdvancedMode(window.localStorage.getItem("alphapilot.showAdvancedMode") === "1");
} catch {
  setAdvancedMode(false);
}

refreshAll().catch((error) => {
  el("strategyList").innerHTML = `<div class="item">加载失败：${error.message}</div>`;
});
updateCurrentSection();
