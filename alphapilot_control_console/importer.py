from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import SAFETY_BOUNDARY, get_quant_engine_path
from .state_store import (
    ARTIFACT_REVIEW_LABELS,
    PAPER_OBSERVATION_LOG_LABELS,
    append_audit,
    load_state,
    now_iso,
    read_exchange_probe_results,
    write_mobile_status,
)

CONTROL_CONSOLE_VERSION = "V13.7.19"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_19"
BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
FORWARD_VALIDATION_REVIEW_DATE = date(2026, 7, 10)
FORWARD_VALIDATION_REVIEW_LABEL = "2026年7月10日（北京时间）"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _bool(data: dict[str, Any], key: str) -> bool:
    return bool(data.get(key))


def _report_summary(report: dict[str, Any], path: Path) -> dict[str, Any]:
    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    return {
        "reportId": report.get("reportId") or path.stem,
        "version": report.get("version"),
        "status": report.get("status"),
        "generatedAt": report.get("generatedAt"),
        "path": str(path),
        "exchangeDryRunApproved": _bool(decision, "exchangeDryRunApproved")
        or _bool(report, "exchangeDryRunApproved"),
        "liveTradingApproved": _bool(decision, "liveTradingApproved") or _bool(report, "liveTradingApproved"),
        "summary": _compact_report_summary(report),
    }


def _compact_report_summary(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("ledgerMetrics"):
        metrics = report["ledgerMetrics"]
        return {
            "kind": "local_paper_ledger",
            "filledSignalCount": metrics.get("filledSignalCount"),
            "winRatePct": metrics.get("winRatePct"),
            "profitFactor": metrics.get("profitFactor"),
            "rewardRiskRatio": metrics.get("rewardRiskRatio"),
            "maxDrawdownPct": metrics.get("maxDrawdownPct"),
        }
    if report.get("bestRawCandidate"):
        candidate = report["bestRawCandidate"]
        metrics = candidate.get("metrics", {})
        return {
            "kind": "alpha_replay",
            "candidateId": candidate.get("candidateId"),
            "tradeCount": metrics.get("tradeCount"),
            "winRatePct": metrics.get("winRatePct"),
            "profitFactor": metrics.get("profitFactor"),
            "rewardRiskRatio": metrics.get("rewardRiskRatio"),
            "rawGatePassed": candidate.get("gate", {}).get("passed"),
        }
    if report.get("reviewProtocol") and report.get("reviews"):
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        status_counts = summary.get("statusCounts") if isinstance(summary.get("statusCounts"), dict) else {}
        return {
            "kind": "multi_agent_strategy_review",
            "reviewedSubjectCount": summary.get("reviewedSubjectCount"),
            "paperObservationCandidateCount": summary.get("paperObservationCandidateCount"),
            "keepResearchingCount": status_counts.get("keep_researching"),
            "rejectForNowCount": status_counts.get("reject_for_now"),
            "dryRunApproved": summary.get("dryRunApproved"),
            "liveTradingApproved": summary.get("liveTradingApproved"),
        }
    if report.get("learningLedger"):
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        return {
            "kind": "strategy_learning_loop",
            "learningItemCount": summary.get("learningItemCount"),
            "graveyardCount": summary.get("graveyardCount"),
            "researchWatchlistCount": summary.get("researchWatchlistCount"),
            "dryRunApproved": summary.get("dryRunApproved"),
            "liveTradingApproved": summary.get("liveTradingApproved"),
        }
    if report.get("refactorCandidates"):
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        return {
            "kind": "strategy_refactor_candidates",
            "candidateCount": summary.get("candidateCount"),
            "researchBacktestSpecReadyCount": summary.get("researchBacktestSpecReadyCount"),
            "paperObservationAllowedCount": summary.get("paperObservationAllowedCount"),
            "topCandidateId": summary.get("topCandidateId"),
            "dryRunApproved": summary.get("dryRunApproved"),
            "liveTradingApproved": summary.get("liveTradingApproved"),
        }
    if report.get("experimentSpecs"):
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        return {
            "kind": "regime_filtered_experiment_specs",
            "experimentSpecCount": summary.get("experimentSpecCount"),
            "readyForBacktestImplementationCount": summary.get("readyForBacktestImplementationCount"),
            "paperObservationAllowedCount": summary.get("paperObservationAllowedCount"),
            "nextStep": summary.get("nextStep"),
            "dryRunApproved": summary.get("dryRunApproved"),
            "liveTradingApproved": summary.get("liveTradingApproved"),
        }
    if report.get("paperObservationReviews"):
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        return {
            "kind": "paper_observation_rereview",
            "reviewedExperimentCount": summary.get("reviewedExperimentCount"),
            "paperObservationApprovedCount": summary.get("paperObservationApprovedCount"),
            "researchBacktestOnlyCount": summary.get("researchBacktestOnlyCount"),
            "nextExecutableResearchStep": summary.get("nextExecutableResearchStep"),
            "dryRunApproved": summary.get("dryRunApproved"),
            "liveTradingApproved": summary.get("liveTradingApproved"),
        }
    if report.get("backtest") and report.get("reportId") == "v13_7_19_lf_factor_confluence_backtest":
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        return {
            "kind": "lf_factor_confluence_deterministic_backtest",
            "experimentId": summary.get("experimentId"),
            "tradeCount": summary.get("tradeCount"),
            "winRatePct": summary.get("winRatePct"),
            "profitFactor": summary.get("profitFactor"),
            "targetRewardRiskRatio": summary.get("targetRewardRiskRatio"),
            "maxDrawdownPct": summary.get("maxDrawdownPct"),
            "passGatePassed": summary.get("passGatePassed"),
            "paperObservationApproved": summary.get("paperObservationApproved"),
            "dryRunApproved": summary.get("dryRunApproved"),
            "liveTradingApproved": summary.get("liveTradingApproved"),
        }
    return {"kind": "report"}


def _build_strategy_learning_loop(reports_dir: Path) -> dict[str, Any]:
    learning_loop = _read_json(reports_dir / "v13_7_15_strategy_learning_loop_report.json")
    refactor_candidates = _read_json(reports_dir / "v13_7_16_strategy_refactor_candidates_report.json")
    experiment_specs = _read_json(reports_dir / "v13_7_17_regime_filtered_experiment_specs_report.json")
    paper_rereview = _read_json(reports_dir / "v13_7_18_paper_observation_rereview_report.json")
    factor_confluence_backtest = _read_json(reports_dir / "v13_7_19_lf_factor_confluence_backtest_report.json")

    learning_summary = learning_loop.get("summary") if isinstance(learning_loop, dict) else {}
    refactor_summary = refactor_candidates.get("summary") if isinstance(refactor_candidates, dict) else {}
    experiment_summary = experiment_specs.get("summary") if isinstance(experiment_specs, dict) else {}
    rereview_summary = paper_rereview.get("summary") if isinstance(paper_rereview, dict) else {}
    backtest_summary = factor_confluence_backtest.get("summary") if isinstance(factor_confluence_backtest, dict) else {}

    generated_at_values = [
        str(report.get("generatedAt"))
        for report in (learning_loop, refactor_candidates, experiment_specs, paper_rereview, factor_confluence_backtest)
        if isinstance(report, dict) and report.get("generatedAt")
    ]

    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": max(generated_at_values) if generated_at_values else None,
        "learningLoop": learning_loop or {},
        "refactorCandidates": refactor_candidates or {},
        "experimentSpecs": experiment_specs or {},
        "paperReReview": paper_rereview or {},
        "factorConfluenceBacktest": factor_confluence_backtest or {},
        "summary": {
            "learningItemCount": learning_summary.get("learningItemCount", 0),
            "graveyardCount": learning_summary.get("graveyardCount", 0),
            "researchWatchlistCount": learning_summary.get("researchWatchlistCount", 0),
            "factorMemoryCount": learning_summary.get("factorMemoryCount", 0),
            "refactorCandidateCount": refactor_summary.get("candidateCount", 0),
            "researchBacktestSpecReadyCount": refactor_summary.get("researchBacktestSpecReadyCount", 0),
            "experimentSpecCount": experiment_summary.get("experimentSpecCount", 0),
            "readyForBacktestImplementationCount": experiment_summary.get("readyForBacktestImplementationCount", 0),
            "paperObservationApprovedCount": rereview_summary.get("paperObservationApprovedCount", 0),
            "researchBacktestOnlyCount": rereview_summary.get("researchBacktestOnlyCount", 0),
            "deterministicBacktestTradeCount": backtest_summary.get("tradeCount", 0),
            "deterministicBacktestProfitFactor": backtest_summary.get("profitFactor"),
            "deterministicBacktestGatePassed": backtest_summary.get("passGatePassed", False),
            "deterministicBacktestPaperApproved": backtest_summary.get("paperObservationApproved", False),
            "dryRunApproved": any(
                bool(summary.get("dryRunApproved"))
                for summary in (learning_summary, refactor_summary, experiment_summary, rereview_summary, backtest_summary)
                if isinstance(summary, dict)
            ),
            "liveTradingApproved": any(
                bool(summary.get("liveTradingApproved"))
                for summary in (learning_summary, refactor_summary, experiment_summary, rereview_summary, backtest_summary)
                if isinstance(summary, dict)
            ),
            "nextExecutableResearchStep": backtest_summary.get("nextStep")
            or rereview_summary.get("nextExecutableResearchStep")
            or experiment_summary.get("nextStep")
            or refactor_summary.get("nextStep")
            or learning_summary.get("nextStep"),
        },
    }


def _strategy_from_package(package: dict[str, Any], report: dict[str, Any] | None, path: Path) -> dict[str, Any]:
    ledger_metrics = (report or {}).get("ledgerMetrics", {})
    gate = (report or {}).get("gate", {})
    gate_passed = bool(gate.get("passed") or gate.get("localPaperRefreshCandidateReady"))
    strategy_id = package.get("packageId") or package.get("candidateId") or path.stem
    suggested_status = "local_paper_ready" if gate_passed else "research_only"
    if package.get("exchangeDryRunApproved") or package.get("liveTradingApproved"):
        suggested_status = "disabled"
    return {
        "strategyId": strategy_id,
        "title": package.get("candidateId") or strategy_id,
        "version": package.get("version"),
        "candidateId": package.get("candidateId"),
        "selectedPolicyId": package.get("selectedPolicyId"),
        "sourcePath": str(path),
        "sourceReport": str(path.parent / "v13_5_21_local_paper_refresh_candidate_report.json"),
        "suggestedStatus": suggested_status,
        "selectedSignalCount": package.get("selectedSignalCount"),
        "stopLossPct": package.get("stopLossPct"),
        "targetRMultiple": package.get("targetRMultiple"),
        "maxConcurrentPositions": package.get("maxConcurrentPositions"),
        "riskPerSignalPct": package.get("riskPerSignalPct"),
        "localSimulationOnly": bool(package.get("localSimulationOnly", True)),
        "exchangeDryRunApproved": bool(package.get("exchangeDryRunApproved", False)),
        "liveTradingApproved": bool(package.get("liveTradingApproved", False)),
        "metrics": {
            "filledSignalCount": ledger_metrics.get("filledSignalCount"),
            "winRatePct": ledger_metrics.get("winRatePct"),
            "profitFactor": ledger_metrics.get("profitFactor"),
            "rewardRiskRatio": ledger_metrics.get("rewardRiskRatio"),
            "maxDrawdownPct": ledger_metrics.get("maxDrawdownPct"),
        },
        "gate": gate,
    }


def _strategy_from_alpha191_report(report: dict[str, Any], path: Path) -> dict[str, Any]:
    candidate = report.get("bestRawCandidate") or {}
    metrics = candidate.get("metrics", {})
    decision = report.get("decision") or {}
    return {
        "strategyId": "v13_5_23_alpha191_crypto_subset_observer",
        "title": candidate.get("candidateId") or "V13.5.23 Alpha191 crypto-safe subset observer",
        "version": report.get("version"),
        "candidateId": candidate.get("candidateId"),
        "selectedPolicyId": (report.get("bestExitAwarePolicy") or {}).get("policyId"),
        "sourcePath": str(path),
        "sourceReport": str(path),
        "suggestedStatus": "research_only",
        "selectedSignalCount": (report.get("bestExitAwarePolicy") or {}).get("selectedSignalCount"),
        "stopLossPct": candidate.get("stopLossPct"),
        "targetRMultiple": candidate.get("targetRMultiple"),
        "maxConcurrentPositions": None,
        "riskPerSignalPct": None,
        "localSimulationOnly": True,
        "exchangeDryRunApproved": bool(decision.get("exchangeDryRunApproved", False)),
        "liveTradingApproved": bool(decision.get("liveTradingApproved", False)),
        "metrics": {
            "tradeCount": metrics.get("tradeCount"),
            "winRatePct": metrics.get("winRatePct"),
            "profitFactor": metrics.get("profitFactor"),
            "rewardRiskRatio": metrics.get("rewardRiskRatio"),
            "maxDrawdownPct": metrics.get("maxDrawdownPct"),
        },
        "gate": {
            "rawReplayGatePassed": decision.get("rawReplayGatePassed"),
            "exitAwareGatePassed": decision.get("exitAwareGatePassed"),
            "localPaperGatePassed": decision.get("localPaperGatePassed"),
        },
    }


def _metric_number(metrics: dict[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    try:
        number_value = float(value)
    except (TypeError, ValueError):
        return None
    return number_value


def _metric_value(metrics: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _metric_number(metrics, key)
        if value is not None:
            return value
    return None


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _human_strategy_name(artifact: dict[str, Any]) -> dict[str, str]:
    raw_parts = [
        str(artifact.get("title") or ""),
        str(artifact.get("strategyId") or ""),
        str(artifact.get("reportId") or ""),
        str(artifact.get("sourceFile") or ""),
    ]
    raw = " ".join(raw_parts).lower()
    if "local_paper_refresh" in raw:
        name = "本地纸面刷新候选"
        subtitle = "从本地纸面刷新流程筛出的候选，重点看后续观察日志。"
    elif "paper_sandbox_ledger" in raw:
        name = "纸面沙盒台账"
        subtitle = "记录纸面沙盒样本和结果，用于复核观察质量。"
    elif "paper_monitoring" in raw:
        name = "纸面观察监控"
        subtitle = "用于持续查看纸面观察样本是否稳定。"
    elif "forward_confirmation" in raw:
        name = "前向确认纸面沙盒"
        subtitle = "观察候选在前向样本里的确认情况。"
    elif "comparative_backtest" in raw:
        name = "多策略对比回测"
        subtitle = "用于横向比较不同策略候选的历史表现。"
    elif "expanded_validation" in raw:
        name = "扩展验证报告"
        subtitle = "扩大样本后的验证结果，重点看稳健性。"
    elif "v03_selection" in raw:
        name = "V03 候选选择"
        subtitle = "第三版候选策略筛选结果。"
    elif "execution_reality" in raw:
        name = "执行现实约束设计"
        subtitle = "用于检查滑点、流动性和现实执行限制。"
    elif "dynamic_universe" in raw:
        name = "动态币种池构建"
        subtitle = "按历史条件构建可观察币种池。"
    elif "probability_dataset" in raw:
        name = "概率数据集构建"
        subtitle = "为概率/分桶研究准备样本数据。"
    elif "probability_bucket" in raw:
        name = "概率分桶粗化"
        subtitle = "把过细概率桶合并成更稳的观察区间。"
    elif "low_frequency_baseline" in raw:
        name = "低频基线对照"
        subtitle = "NoTrade / BuyHold / 等权基线，用于设定策略门槛。"
    elif "low_frequency_candidate" in raw:
        name = "低频候选规格"
        subtitle = "低频策略候选定义，还不是实盘策略。"
    elif "alpha191" in raw or "alpha_191" in raw:
        name = "Alpha191 因子观察策略"
        subtitle = "多因子研究候选，用于观察因子方向和稳定性。"
    elif "dynamic" in raw and "regime" in raw:
        name = "动态市场状态策略"
        subtitle = "按市场状态切换观察条件，适合做 regime 复核。"
    elif "low" in raw and "frequency" in raw:
        name = "低频主流币趋势策略"
        subtitle = "偏低频方向筛选，重点看趋势质量和回撤控制。"
    elif "pullback" in raw:
        name = "趋势回撤观察策略"
        subtitle = "趋势方向内等待回撤后的研究候选。"
    elif "volume" in raw or "rebound" in raw:
        name = "放量反弹研究策略"
        subtitle = "观察放量、反弹和风险过滤是否同时成立。"
    elif "short" in raw or "rejection" in raw:
        name = "短线反转拒绝策略"
        subtitle = "观察反转失败、假突破和拒绝形态。"
    elif "benchmark" in raw:
        name = "基准对照策略"
        subtitle = "用于和 NoTrade / BuyHold / 等权基线对比。"
    elif "factor" in raw:
        name = "因子研究观察策略"
        subtitle = "用于观察单因子或组合因子的历史表现。"
    else:
        name = str(artifact.get("title") or artifact.get("strategyId") or "未命名策略")
        subtitle = "本地策略资产，保留原始 ID 作为追溯依据。"
    return {"displayName": name, "displaySubtitle": subtitle}


def _build_artifact_score_breakdown(artifact: dict[str, Any]) -> dict[str, Any]:
    metrics = artifact.get("metrics") if isinstance(artifact.get("metrics"), dict) else {}
    sample_count = _metric_value(metrics, "sampleCount", "tradeCount", "filledSignalCount") or 0
    win_rate = _metric_value(metrics, "winRatePct")
    reward_risk = _metric_value(metrics, "rewardRiskRatio")
    drawdown = _metric_value(metrics, "maxDrawdownPct")
    profit_factor = _metric_value(metrics, "profitFactor")
    total_return = _metric_value(metrics, "totalReturnPct")
    baseline_delta = _metric_value(
        metrics,
        "baselineReturnDeltaPct",
        "excessReturnPct",
        "vsBuyHoldReturnPct",
        "alphaReturnPct",
    )

    win_rate_contribution = _clamp(((win_rate or 0) - 45) * 1.1, 0, 25)
    reward_risk_contribution = _clamp((reward_risk or 0) / 2 * 25, 0, 25)
    sample_size_penalty = 0 if sample_count >= 50 else _clamp((50 - sample_count) / 50 * 18, 0, 18)
    drawdown_penalty = 0 if drawdown is None or drawdown <= 12 else _clamp((drawdown - 12) * 0.8, 0, 18)
    stability_penalty = 0
    if artifact.get("readinessTier") in {"needs_review", "archived_or_failed", "blocked_by_safety_review"}:
        stability_penalty += 12
    if profit_factor is None or profit_factor < 1:
        stability_penalty += 8

    baseline_comparison = "not_available"
    if baseline_delta is not None:
        baseline_comparison = "above_baseline" if baseline_delta > 0 else "below_baseline"
    elif total_return is not None:
        baseline_comparison = "return_available_without_baseline"

    return {
        "method": "console_explain_only_v13_7_7",
        "researchScore": artifact.get("researchScore"),
        "winRateContribution": round(win_rate_contribution, 2),
        "rewardRiskContribution": round(reward_risk_contribution, 2),
        "sampleSizePenalty": round(sample_size_penalty, 2),
        "drawdownPenalty": round(drawdown_penalty, 2),
        "stabilityPenalty": round(stability_penalty, 2),
        "baselineComparison": baseline_comparison,
        "baselineDeltaPct": baseline_delta,
        "notes": [
            "Score explanation is a local review aid, not a profit probability.",
            "Low sample size, high drawdown, weak PF, or safety blocks should slow down observation.",
            "Paper observation status is a manual research label and does not create orders.",
        ],
    }


def _build_paper_observation_checklist(artifact: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    metrics = artifact.get("metrics") if isinstance(artifact.get("metrics"), dict) else {}
    sample_count = int(_metric_value(metrics, "sampleCount", "tradeCount", "filledSignalCount") or 0)
    target_sample_count = 30 if sample_count < 30 else max(sample_count + 20, 50)
    status = str(review.get("reviewStatus") or "unreviewed")
    return {
        "status": "active" if status == "paper_observation" else "not_started",
        "startAt": review.get("reviewedAt") if status == "paper_observation" else None,
        "observationPeriod": "next_30_to_60_calendar_days",
        "currentSampleCount": sample_count,
        "targetSampleCount": target_sample_count,
        "progressPct": round(_clamp(sample_count / target_sample_count * 100 if target_sample_count else 0, 0, 100), 2),
        "requiredChecks": [
            "Confirm signal sample count and data freshness.",
            "Confirm risk/reward remains near 2R research target.",
            "Confirm drawdown and losing streak remain acceptable.",
            "Record paper observations only; do not create real orders.",
        ],
        "safetyNote": "Paper observation is a research checklist only. Trade API, orders, and automatic execution remain disabled.",
    }


def _logs_for_artifact(logs_by_artifact: dict[str, Any], artifact_id: str, limit: int = 5) -> list[dict[str, Any]]:
    rows = logs_by_artifact.get(artifact_id, [])
    if not isinstance(rows, list):
        return []
    clean_rows = [row for row in rows if isinstance(row, dict)]
    return sorted(clean_rows, key=lambda item: str(item.get("createdAt") or ""), reverse=True)[:limit]


def _count_logs(logs: list[dict[str, Any]], log_type: str) -> int:
    return sum(1 for row in logs if row.get("logType") == log_type)


def _build_paper_observation_health(
    artifact: dict[str, Any],
    task: dict[str, Any],
    logs: list[dict[str, Any]],
    checklist: dict[str, Any],
) -> dict[str, Any]:
    task_status = str(task.get("taskStatus") or "planned")
    progress_pct = float(task.get("progressPct") or checklist.get("progressPct") or 0)
    log_count = len(logs)
    signal_seen_count = sum(1 for row in logs if row.get("signalObserved"))
    rule_matched_count = sum(1 for row in logs if row.get("ruleMatched") or row.get("logType") == "rule_matched")
    missed_count = _count_logs(logs, "missed")
    invalidated_count = _count_logs(logs, "invalidated")
    risk_warning_count = _count_logs(logs, "risk_warning")
    score = 50
    if task_status == "active":
        score += 10
    if log_count >= 3:
        score += 10
    if rule_matched_count > 0:
        score += 10
    if progress_pct >= 60:
        score += 10
    if invalidated_count > 0:
        score -= 15
    if missed_count >= 2:
        score -= 10
    if risk_warning_count > 0:
        score -= 10
    score = int(_clamp(score, 0, 100))
    if task_status == "completed":
        health_label = "completed"
        health_tone = "good"
        next_action = "整理观察结果，确认是否进入下一轮策略研究。"
    elif task_status == "paused":
        health_label = "paused"
        health_tone = "warn"
        next_action = "暂停继续观察，等待新样本或新版本策略。"
    elif task_status == "rejected":
        health_label = "rejected"
        health_tone = "danger"
        next_action = "保留淘汰原因，避免重复研究同类失败条件。"
    elif invalidated_count > 0 or risk_warning_count > 0:
        health_label = "needs_review"
        health_tone = "danger"
        next_action = "优先复核失效或风险记录，暂缓扩大观察范围。"
    elif score >= 75:
        health_label = "healthy_observation"
        health_tone = "good"
        next_action = "继续累计纸面观察日志，保持人工复核。"
    elif score >= 50:
        health_label = "watching"
        health_tone = "warn"
        next_action = "继续观察，同时补足规则匹配和未触发样本。"
    else:
        health_label = "needs_more_observation"
        health_tone = "warn"
        next_action = "样本或日志不足，先补记录再判断。"
    risk_flags: list[str] = []
    if invalidated_count:
        risk_flags.append("存在条件失效记录")
    if risk_warning_count:
        risk_flags.append("存在风险提醒记录")
    if missed_count >= 2:
        risk_flags.append("多次错过观察")
    if log_count == 0:
        risk_flags.append("尚未记录观察日志")
    latest_log_at = logs[0].get("createdAt") if logs else None
    return {
        "healthScore": score,
        "healthLabel": health_label,
        "healthTone": health_tone,
        "logCount": log_count,
        "latestLogAt": latest_log_at,
        "signalSeenCount": signal_seen_count,
        "ruleMatchedCount": rule_matched_count,
        "missedCount": missed_count,
        "invalidatedCount": invalidated_count,
        "riskWarningCount": risk_warning_count,
        "riskFlags": risk_flags,
        "nextReviewAction": next_action,
        "note": "Health score is a local paper-observation completeness score, not a probability of profit.",
        "strategyDisplayName": artifact.get("displayName") or artifact.get("title"),
    }


def _build_paper_observation_task_view(
    artifact: dict[str, Any],
    task: dict[str, Any] | None,
    checklist: dict[str, Any],
    logs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    metrics = artifact.get("metrics") if isinstance(artifact.get("metrics"), dict) else {}
    sample_count = int(_metric_value(metrics, "sampleCount", "tradeCount", "filledSignalCount") or 0)
    task = task if isinstance(task, dict) else {}
    target_sample_count = int(task.get("targetSampleCount") or checklist.get("targetSampleCount") or 50)
    task_status = str(task.get("taskStatus") or "planned")
    recent_logs = logs or []
    view = {
        "taskId": task.get("taskId"),
        "artifactId": artifact.get("artifactId"),
        "strategyId": artifact.get("strategyId"),
        "title": artifact.get("displayName") or artifact.get("title"),
        "originalTitle": artifact.get("title"),
        "displaySubtitle": artifact.get("displaySubtitle"),
        "version": artifact.get("version"),
        "taskStatus": task_status,
        "taskLabel": task.get("taskLabel") or {
            "planned": "计划中",
            "active": "观察中",
            "paused": "已暂停",
            "completed": "已完成",
            "rejected": "已淘汰",
        }.get(task_status, task_status),
        "currentSampleCount": sample_count,
        "targetSampleCount": target_sample_count,
        "progressPct": round(_clamp(sample_count / target_sample_count * 100 if target_sample_count else 0, 0, 100), 2),
        "observationDays": int(task.get("observationDays") or 60),
        "startedAt": task.get("startedAt"),
        "completedAt": task.get("completedAt"),
        "updatedAt": task.get("updatedAt"),
        "note": task.get("note") or "",
        "source": task.get("source") or CONTROL_CONSOLE_SOURCE,
        "safetyNote": "Observation tasks are local research workflow records only. They do not create orders.",
    }
    view["health"] = _build_paper_observation_health(artifact, view, recent_logs, checklist)
    view["recentLogs"] = recent_logs
    return view


def _default_artifact_review(artifact_id: str) -> dict[str, Any]:
    return {
        "artifactId": artifact_id,
        "reviewStatus": "unreviewed",
        "reviewLabel": ARTIFACT_REVIEW_LABELS["unreviewed"],
        "reviewNote": "",
        "reviewedAt": None,
        "source": CONTROL_CONSOLE_SOURCE,
    }


def _review_status_counts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {status: 0 for status in ARTIFACT_REVIEW_LABELS}
    for artifact in artifacts:
        status = str(artifact.get("reviewStatus") or "unreviewed")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _task_status_counts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {
        "planned": 0,
        "active": 0,
        "paused": 0,
        "completed": 0,
        "rejected": 0,
    }
    for artifact in artifacts:
        task = artifact.get("paperObservationTask") if isinstance(artifact.get("paperObservationTask"), dict) else {}
        status = str(task.get("taskStatus") or "planned")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _count_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _artifact_search_text(artifact: dict[str, Any]) -> str:
    values = [
        artifact.get("artifactId"),
        artifact.get("strategyId"),
        artifact.get("title"),
        artifact.get("displayName"),
        artifact.get("displaySubtitle"),
        artifact.get("version"),
        artifact.get("sourceFile"),
        artifact.get("sourceKind"),
        artifact.get("recommendedAction"),
    ]
    return " ".join(str(value or "").lower() for value in values)


def _classify_method_type(artifact: dict[str, Any]) -> tuple[str, str]:
    text = _artifact_search_text(artifact)
    source_kind = str(artifact.get("sourceKind") or "").lower()
    if "benchmark" in text or "buyhold" in text or "no_trade" in text:
        return "benchmark", "基准策略"
    if "ml" in text or "machine" in text or "model" in text or "classifier" in text:
        return "ml_model", "机器学习模型"
    if "alpha191" in text or "factor" in text or "因子" in text or source_kind in {"best_exit_aware_policy"}:
        return "factor_based", "因子策略"
    if source_kind.endswith("report") or source_kind == "report_summary":
        if any(token in text for token in ("trend", "pullback", "rebound", "rejection", "directional", "ema", "volume")):
            return "rule_based", "规则策略"
        return "report_only", "报告资产"
    return "rule_based", "规则策略"


def _classify_label_status(metrics: dict[str, Any], artifact: dict[str, Any]) -> tuple[str, str]:
    has_trade_count = _metric_value(metrics, "tradeCount", "sampleCount", "filledSignalCount") is not None
    has_win_rate = _metric_value(metrics, "winRatePct") is not None
    has_r = _metric_value(metrics, "rewardRiskRatio") is not None or "rmultiple" in _artifact_search_text(artifact)
    has_path = _metric_value(metrics, "maxDrawdownPct", "maxConsecutiveLosses") is not None
    if has_r and has_win_rate:
        return "has_2r_and_win_loss_labels", "已有 2R / 胜负标签"
    if has_win_rate and has_trade_count:
        return "has_win_loss_labels", "已有胜负标签"
    if has_path and has_trade_count:
        return "has_path_quality_labels", "已有路径质量标签"
    if has_trade_count:
        return "has_sample_labels", "已有样本标签"
    return "missing_labels", "缺标签"


def _classify_walk_forward_status(artifact: dict[str, Any]) -> tuple[str, str]:
    text = _artifact_search_text(artifact)
    if "walk_forward" in text or "walk-forward" in text:
        return "walk_forward_validated", "已 walk-forward 验证"
    if "forward" in text or "paper" in text or "monitoring" in text:
        return "forward_observation_artifact", "前向观察资产"
    if "expanded_validation" in text or "validation" in text:
        return "expanded_backtest_validated", "扩展回测验证"
    return "not_walk_forward_validated", "未 walk-forward 验证"


def _classify_ml_status(method_type: str, label_status: str, metrics: dict[str, Any]) -> tuple[str, str]:
    sample_count = int(_metric_value(metrics, "sampleCount", "tradeCount", "filledSignalCount") or 0)
    if method_type == "ml_model":
        return "trained_model_reported", "已报告训练模型"
    if sample_count >= 300 and label_status != "missing_labels":
        return "ml_dataset_ready", "可生成 ML 训练集"
    if sample_count >= 80 and label_status != "missing_labels":
        return "label_ready_needs_more_samples", "有标签但样本偏少"
    if method_type == "factor_based":
        return "factor_features_available", "有因子特征，待补标签/样本"
    if label_status == "missing_labels":
        return "missing_labels", "缺少 ML 标签"
    return "not_ml_strategy", "非 ML 策略"


def _candidate_decision(
    artifact: dict[str, Any],
    method_type: str,
    ml_status: str,
    label_status: str,
    walk_forward_status: str,
) -> tuple[str, str, list[str]]:
    metrics = artifact.get("metrics") if isinstance(artifact.get("metrics"), dict) else {}
    readiness = str(artifact.get("readinessTier") or "")
    review_status = str(artifact.get("reviewStatus") or "")
    sample_count = int(_metric_value(metrics, "sampleCount", "tradeCount", "filledSignalCount") or 0)
    profit_factor = _metric_value(metrics, "profitFactor")
    reward_risk = _metric_value(metrics, "rewardRiskRatio")
    drawdown = _metric_value(metrics, "maxDrawdownPct")
    reasons: list[str] = []
    if review_status == "rejected" or readiness == "archived_or_failed":
        reasons.append("已归档/失败或人工淘汰，不进入当前前向验证。")
        return "rejected_or_archived", "淘汰/归档", reasons
    if method_type in {"benchmark", "report_only"}:
        reasons.append("属于基准或报告资产，用于对照研究，不直接前向验证。")
        return "research_only", "只做研究观察", reasons
    if sample_count < 30:
        reasons.append("样本数低于 30，需要先补回测。")
        return "needs_backtest", "需要补回测", reasons
    if label_status == "missing_labels":
        reasons.append("缺少胜负、2R 或路径质量标签。")
        return "needs_labels", "需要补标签", reasons
    if drawdown is not None and drawdown > 60:
        reasons.append("历史最大回撤过高，先暂停。")
        return "paused", "暂停", reasons
    if profit_factor is not None and profit_factor < 1:
        reasons.append("Profit Factor 低于 1，暂不进入前向验证。")
        return "paused", "暂停", reasons
    if reward_risk is not None and reward_risk < 1.5:
        reasons.append("盈亏比不足，优先继续研究。")
        return "research_only", "只做研究观察", reasons
    if ml_status in {"ml_dataset_ready", "trained_model_reported"} and walk_forward_status in {
        "forward_observation_artifact",
        "walk_forward_validated",
        "expanded_backtest_validated",
    }:
        reasons.append("样本、标签和验证记录较完整，可进入前向验证候选池。")
        return "can_forward_validate", "可进入前向验证", reasons
    if ml_status in {"ml_dataset_ready", "factor_features_available", "label_ready_needs_more_samples"}:
        reasons.append("可用于 ML 评价或因子筛选，但还需要前向观察。")
        return "ml_evaluation_queue", "进入 ML 评价队列", reasons
    reasons.append("规则资产可继续观察，但暂不作为主验证策略。")
    return "research_only", "只做研究观察", reasons


def _build_ml_coverage(artifact: dict[str, Any]) -> dict[str, Any]:
    metrics = artifact.get("metrics") if isinstance(artifact.get("metrics"), dict) else {}
    method_type, method_label = _classify_method_type(artifact)
    label_status, label_label = _classify_label_status(metrics, artifact)
    walk_status, walk_label = _classify_walk_forward_status(artifact)
    ml_status, ml_label = _classify_ml_status(method_type, label_status, metrics)
    decision, decision_label, reasons = _candidate_decision(
        artifact, method_type, ml_status, label_status, walk_status
    )
    return {
        "methodType": method_type,
        "methodLabel": method_label,
        "mlStatus": ml_status,
        "mlStatusLabel": ml_label,
        "labelStatus": label_status,
        "labelStatusLabel": label_label,
        "walkForwardStatus": walk_status,
        "walkForwardStatusLabel": walk_label,
        "candidateDecision": decision,
        "candidateDecisionLabel": decision_label,
        "decisionReasons": reasons,
        "note": "ML status describes research-data readiness. It is not a trading signal.",
    }


def _ml_coverage_summary(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [item.get("mlCoverage") for item in artifacts if isinstance(item.get("mlCoverage"), dict)]
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "totalArtifacts": len(artifacts),
        "methodTypeCounts": _count_by_key(rows, "methodType"),
        "mlStatusCounts": _count_by_key(rows, "mlStatus"),
        "labelStatusCounts": _count_by_key(rows, "labelStatus"),
        "walkForwardStatusCounts": _count_by_key(rows, "walkForwardStatus"),
        "candidateDecisionCounts": _count_by_key(rows, "candidateDecision"),
        "mlDatasetReadyCount": sum(1 for item in rows if item.get("mlStatus") == "ml_dataset_ready"),
        "trainedModelReportedCount": sum(1 for item in rows if item.get("mlStatus") == "trained_model_reported"),
        "forwardCandidateCount": sum(1 for item in rows if item.get("candidateDecision") == "can_forward_validate"),
        "mlEvaluationQueueCount": sum(1 for item in rows if item.get("candidateDecision") == "ml_evaluation_queue"),
        "safetyNote": "ML coverage is for research screening only. It does not create orders.",
    }


def _candidate_queue_label(queue_type: str) -> str:
    labels = {
        "priority_forward_validation": "前向验证优先",
        "ml_evaluation": "ML 评价队列",
        "needs_backtest": "需要补回测",
        "needs_labels": "需要补标签",
        "research_watchlist": "研究观察",
        "paused": "暂停",
        "rejected": "淘汰/归档",
    }
    return labels.get(queue_type, queue_type)


def _candidate_queue_type(decision: str) -> str:
    if decision == "can_forward_validate":
        return "priority_forward_validation"
    if decision == "ml_evaluation_queue":
        return "ml_evaluation"
    if decision == "needs_backtest":
        return "needs_backtest"
    if decision == "needs_labels":
        return "needs_labels"
    if decision == "paused":
        return "paused"
    if decision == "rejected_or_archived":
        return "rejected"
    return "research_watchlist"


def _candidate_next_action(queue_type: str) -> str:
    actions = {
        "priority_forward_validation": "先建立正式前向观察任务，记录至少 3 条观察日志和 1 次规则匹配。",
        "ml_evaluation": "整理训练样本和标签，进入离线 ML/因子评价，不进入执行。",
        "needs_backtest": "先补长区间、多币种或多市场回测，再决定是否进入观察。",
        "needs_labels": "补齐胜负、2R 或路径质量标签，再进入 ML 评价。",
        "research_watchlist": "保留研究观察，暂不作为主验证策略。",
        "paused": "暂停推进，先复核回撤、PF、样本或人工暂停原因。",
        "rejected": "保持归档或淘汰状态，不进入当前候选队列。",
    }
    return actions.get(queue_type, "继续人工复核。")


def _backtest_completion_map(completion_report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(completion_report, dict):
        return {}
    tasks = completion_report.get("tasks") if isinstance(completion_report.get("tasks"), list) else []
    rows: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("taskId") or "").strip()
        if task_id:
            rows[task_id] = task
            rows[f"v13_7_12_backtest_gap_{task_id}"] = task
    return rows


def _candidate_priority_score(artifact: dict[str, Any], queue_type: str) -> float:
    metrics = artifact.get("metrics") if isinstance(artifact.get("metrics"), dict) else {}
    weights = {
        "priority_forward_validation": 1000,
        "ml_evaluation": 820,
        "needs_backtest": 560,
        "needs_labels": 520,
        "research_watchlist": 260,
        "paused": 80,
        "rejected": -100,
    }
    score = float(weights.get(queue_type, 0))
    score += float(artifact.get("researchScore") or 0)
    score += min(float(_metric_value(metrics, "sampleCount", "tradeCount", "filledSignalCount") or 0), 500) / 20
    score += float(_metric_value(metrics, "profitFactor") or 0) * 8
    score += float(_metric_value(metrics, "rewardRiskRatio") or 0) * 6
    drawdown = _metric_value(metrics, "maxDrawdownPct")
    if drawdown is not None:
        score -= min(float(drawdown), 100) / 5
    return round(score, 2)


def _candidate_queue_row(artifact: dict[str, Any]) -> dict[str, Any]:
    metrics = artifact.get("metrics") if isinstance(artifact.get("metrics"), dict) else {}
    ml = artifact.get("mlCoverage") if isinstance(artifact.get("mlCoverage"), dict) else {}
    decision = str(ml.get("candidateDecision") or "research_only")
    queue_type = _candidate_queue_type(decision)
    return {
        "artifactId": artifact.get("artifactId"),
        "strategyId": artifact.get("strategyId"),
        "title": artifact.get("displayName") or artifact.get("title") or artifact.get("strategyId"),
        "originalTitle": artifact.get("title"),
        "displaySubtitle": artifact.get("displaySubtitle"),
        "version": artifact.get("version"),
        "reportId": artifact.get("reportId"),
        "sourceFile": artifact.get("sourceFile"),
        "queueType": queue_type,
        "queueLabel": _candidate_queue_label(queue_type),
        "priorityScore": _candidate_priority_score(artifact, queue_type),
        "candidateDecision": decision,
        "candidateDecisionLabel": ml.get("candidateDecisionLabel"),
        "methodType": ml.get("methodType"),
        "methodLabel": ml.get("methodLabel"),
        "mlStatus": ml.get("mlStatus"),
        "mlStatusLabel": ml.get("mlStatusLabel"),
        "labelStatus": ml.get("labelStatus"),
        "labelStatusLabel": ml.get("labelStatusLabel"),
        "walkForwardStatus": ml.get("walkForwardStatus"),
        "walkForwardStatusLabel": ml.get("walkForwardStatusLabel"),
        "readinessTier": artifact.get("readinessTier"),
        "reviewStatus": artifact.get("reviewStatus"),
        "researchScore": artifact.get("researchScore"),
        "sampleCount": _metric_value(metrics, "sampleCount", "tradeCount", "filledSignalCount"),
        "winRatePct": _metric_value(metrics, "winRatePct"),
        "profitFactor": _metric_value(metrics, "profitFactor"),
        "rewardRiskRatio": _metric_value(metrics, "rewardRiskRatio"),
        "maxDrawdownPct": _metric_value(metrics, "maxDrawdownPct"),
        "totalReturnPct": _metric_value(metrics, "totalReturnPct"),
        "nextAction": _candidate_next_action(queue_type),
        "decisionReasons": ml.get("decisionReasons") if isinstance(ml.get("decisionReasons"), list) else [],
        "safetyNote": "Candidate queue is read-only research prioritization. It does not create orders.",
    }


def _build_strategy_candidate_queue(index: dict[str, Any], limit: int = 60) -> dict[str, Any]:
    artifacts = index.get("artifacts") if isinstance(index.get("artifacts"), list) else []
    rows = [_candidate_queue_row(item) for item in artifacts if isinstance(item, dict)]
    rows = sorted(rows, key=lambda item: float(item.get("priorityScore") or 0), reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    summary = {
        "totalCandidates": len(rows),
        "forwardReadyCount": sum(1 for item in rows if item.get("queueType") == "priority_forward_validation"),
        "mlEvaluationCount": sum(1 for item in rows if item.get("queueType") == "ml_evaluation"),
        "needsBacktestCount": sum(1 for item in rows if item.get("queueType") == "needs_backtest"),
        "needsLabelsCount": sum(1 for item in rows if item.get("queueType") == "needs_labels"),
        "researchWatchlistCount": sum(1 for item in rows if item.get("queueType") == "research_watchlist"),
        "pausedCount": sum(1 for item in rows if item.get("queueType") == "paused"),
        "rejectedCount": sum(1 for item in rows if item.get("queueType") == "rejected"),
        "topQueueType": rows[0].get("queueType") if rows else None,
        "topCandidateTitle": rows[0].get("title") if rows else None,
        "queueMethod": "candidateDecision, ML readiness, label readiness, research score, sample count, PF, reward-risk, and drawdown penalty",
        "safetyNote": "Queue ranking is research triage only. It is not a trading signal or execution instruction.",
    }
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "generatedAt": now_iso(),
        "source": CONTROL_CONSOLE_SOURCE,
        "summary": summary,
        "candidates": rows[:limit],
        "safetyBoundary": SAFETY_BOUNDARY,
    }


def _candidate_queue_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "totalCandidates": len(rows),
        "forwardReadyCount": sum(1 for item in rows if item.get("queueType") == "priority_forward_validation"),
        "mlEvaluationCount": sum(1 for item in rows if item.get("queueType") == "ml_evaluation"),
        "needsBacktestCount": sum(1 for item in rows if item.get("queueType") == "needs_backtest"),
        "needsLabelsCount": sum(1 for item in rows if item.get("queueType") == "needs_labels"),
        "researchWatchlistCount": sum(1 for item in rows if item.get("queueType") == "research_watchlist"),
        "pausedCount": sum(1 for item in rows if item.get("queueType") == "paused"),
        "rejectedCount": sum(1 for item in rows if item.get("queueType") == "rejected"),
        "backtestCompletedNotReadyCount": sum(
            1 for item in rows if item.get("candidateDecision") == "backtest_completed_not_ready"
        ),
        "topQueueType": rows[0].get("queueType") if rows else None,
        "topCandidateTitle": rows[0].get("title") if rows else None,
        "queueMethod": "candidateDecision, ML readiness, label readiness, research score, sample count, PF, reward-risk, drawdown penalty, and backtest completion status",
        "safetyNote": "Queue ranking is research triage only. It is not a trading signal or execution instruction.",
    }


def _apply_backtest_completion_to_candidate_queue(
    candidate_queue: dict[str, Any],
    completion_report: dict[str, Any] | None,
) -> dict[str, Any]:
    completed = _backtest_completion_map(completion_report)
    if not completed:
        return candidate_queue
    rows = candidate_queue.get("candidates") if isinstance(candidate_queue.get("candidates"), list) else []
    updated_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        task = completed.get(str(row.get("artifactId") or "")) or completed.get(str(row.get("taskId") or ""))
        row = dict(row)
        if task and row.get("queueType") == "needs_backtest":
            row["queueType"] = "research_watchlist"
            row["queueLabel"] = "补测已完成"
            row["candidateDecision"] = "backtest_completed_not_ready"
            row["candidateDecisionLabel"] = "补测完成未通过"
            row["nextAction"] = task.get("nextAction") or "补测完成但未通过观察门槛，继续研究观察。"
            row["decisionReasons"] = [
                "V13.7.13 补测已完成。",
                str(task.get("finding") or "补测未通过观察/模拟盘门槛。"),
            ]
            row["backtestCompletion"] = {
                "completionStatus": task.get("completionStatus"),
                "result": task.get("result"),
                "paperOrShadowApproved": task.get("paperOrShadowApproved"),
                "evidenceFiles": task.get("evidenceFiles") if isinstance(task.get("evidenceFiles"), list) else [],
            }
            row["priorityScore"] = min(float(row.get("priorityScore") or 0), 260.0)
        updated_rows.append(row)
    updated_rows = sorted(updated_rows, key=lambda item: float(item.get("priorityScore") or 0), reverse=True)
    for rank, row in enumerate(updated_rows, start=1):
        row["rank"] = rank
    return {
        **candidate_queue,
        "summary": _candidate_queue_summary(updated_rows),
        "candidates": updated_rows[: len(rows)],
        "backtestTaskCompletionSummary": completion_report.get("summary") if isinstance(completion_report, dict) else {},
    }


def _research_task_type_label(task_type: str) -> str:
    labels = {
        "forward_observation": "前向观察任务",
        "backtest_gap": "补回测任务",
        "label_gap": "补标签任务",
        "ml_evaluation": "ML 评价任务",
    }
    return labels.get(task_type, task_type)


def _research_task_acceptance_checks(task_type: str) -> list[str]:
    checks = {
        "forward_observation": [
            "建立正式 active 前向观察任务，不能只保留 smoke/test 任务。",
            "至少记录 3 条前向观察日志。",
            "至少记录 1 次规则匹配。",
            "没有未处理的失效或风险提醒。",
        ],
        "backtest_gap": [
            "补齐 2020-2026 长区间回测或当前可用最长区间。",
            "覆盖更多币种，优先 Top 100 中有足够 OHLCV 的标的。",
            "保留手续费、滑点、延迟、连续亏损压力测试。",
            "与 NoTrade / BuyHold / EqualWeight 基线对比。",
        ],
        "label_gap": [
            "补胜负标签、2R 标签或路径质量标签。",
            "标明标签来源和时间切分，不能事后挑样本。",
            "低质量或缺失标签继续留在研究观察，不进入 ML 评价。",
        ],
        "ml_evaluation": [
            "按训练、验证、测试切分做离线评价。",
            "检查特征泄漏、样本过少和过拟合风险。",
            "ML 只做候选排序和过滤，不输出交易指令。",
        ],
    }
    return checks.get(task_type, ["继续人工复核，保持研究边界。"])


def _research_task_row(candidate: dict[str, Any], task_type: str) -> dict[str, Any]:
    artifact_id = str(candidate.get("artifactId") or candidate.get("strategyId") or candidate.get("rank") or "unknown")
    task_id = f"v13_7_12_{task_type}_{artifact_id}".replace(" ", "_").replace("/", "_").replace("\\", "_")
    return {
        "taskId": task_id,
        "taskType": task_type,
        "taskTypeLabel": _research_task_type_label(task_type),
        "status": "research_todo",
        "rank": candidate.get("rank"),
        "artifactId": candidate.get("artifactId"),
        "strategyId": candidate.get("strategyId"),
        "title": candidate.get("title"),
        "displaySubtitle": candidate.get("displaySubtitle"),
        "version": candidate.get("version"),
        "queueType": candidate.get("queueType"),
        "priorityScore": candidate.get("priorityScore"),
        "sampleCount": candidate.get("sampleCount"),
        "winRatePct": candidate.get("winRatePct"),
        "profitFactor": candidate.get("profitFactor"),
        "rewardRiskRatio": candidate.get("rewardRiskRatio"),
        "maxDrawdownPct": candidate.get("maxDrawdownPct"),
        "nextAction": candidate.get("nextAction"),
        "acceptanceChecks": _research_task_acceptance_checks(task_type),
        "decisionReasons": candidate.get("decisionReasons") if isinstance(candidate.get("decisionReasons"), list) else [],
        "safetyNote": "Research task board is read-only. It does not run backtests, create orders, or execute dry-run.",
    }


def _build_research_task_board(
    candidate_queue: dict[str, Any],
    forward_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = candidate_queue.get("candidates") if isinstance(candidate_queue.get("candidates"), list) else []
    forward_rows = [
        _research_task_row(item, "forward_observation")
        for item in candidates
        if item.get("queueType") == "priority_forward_validation"
    ]
    backtest_rows = [
        _research_task_row(item, "backtest_gap")
        for item in candidates
        if item.get("queueType") == "needs_backtest"
    ]
    label_rows = [
        _research_task_row(item, "label_gap")
        for item in candidates
        if item.get("queueType") == "needs_labels"
    ]
    ml_rows = [
        _research_task_row(item, "ml_evaluation")
        for item in candidates
        if item.get("queueType") == "ml_evaluation"
    ]
    all_tasks = forward_rows + backtest_rows + label_rows + ml_rows
    forward_validation = forward_validation if isinstance(forward_validation, dict) else {}
    summary = {
        "totalResearchTasks": len(all_tasks),
        "forwardObservationTaskCount": len(forward_rows),
        "backtestTaskCount": len(backtest_rows),
        "labelTaskCount": len(label_rows),
        "mlEvaluationTaskCount": len(ml_rows),
        "topForwardTitle": forward_rows[0].get("title") if forward_rows else None,
        "topBacktestTitle": backtest_rows[0].get("title") if backtest_rows else None,
        "acceptanceGate": forward_validation.get("acceptanceGate"),
        "acceptanceGateLabel": forward_validation.get("acceptanceGateLabel"),
        "reviewDateLabel": forward_validation.get("reviewDateLabel"),
        "safetyNote": "Tasks are research scheduling artifacts only. They do not trigger backtests, orders, dry-run, or auto trading.",
    }
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "generatedAt": now_iso(),
        "source": CONTROL_CONSOLE_SOURCE,
        "summary": summary,
        "forwardObservationTasks": forward_rows[:8],
        "backtestTasks": backtest_rows[:12],
        "labelTasks": label_rows[:8],
        "mlEvaluationTasks": ml_rows[:8],
        "allTasks": all_tasks[:40],
        "safetyBoundary": SAFETY_BOUNDARY,
    }


def _apply_artifact_reviews(index: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    reviews = state.get("artifactReviews") if isinstance(state.get("artifactReviews"), dict) else {}
    tasks = state.get("paperObservationTasks") if isinstance(state.get("paperObservationTasks"), dict) else {}
    logs_by_artifact = state.get("paperObservationLogs") if isinstance(state.get("paperObservationLogs"), dict) else {}
    all_items: list[dict[str, Any]] = []
    for key in ("artifacts", "topArtifacts"):
        rows = index.get(key)
        if not isinstance(rows, list):
            continue
        for item in rows:
            if not isinstance(item, dict):
                continue
            artifact_id = str(item.get("artifactId") or item.get("strategyId") or item.get("reportId") or "").strip()
            if not artifact_id:
                continue
            item["artifactId"] = artifact_id
            display = _human_strategy_name(item)
            item["displayName"] = display["displayName"]
            item["displaySubtitle"] = display["displaySubtitle"]
            review = reviews.get(artifact_id) if isinstance(reviews.get(artifact_id), dict) else _default_artifact_review(artifact_id)
            status = str(review.get("reviewStatus") or "unreviewed")
            item["reviewStatus"] = status
            item["reviewLabel"] = ARTIFACT_REVIEW_LABELS.get(status, ARTIFACT_REVIEW_LABELS["unreviewed"])
            item["reviewNote"] = str(review.get("reviewNote") or "")
            item["reviewedAt"] = review.get("reviewedAt")
            item["reviewSource"] = review.get("source") or CONTROL_CONSOLE_SOURCE
            item["mlCoverage"] = _build_ml_coverage(item)
            item["scoreBreakdown"] = _build_artifact_score_breakdown(item)
            checklist = _build_paper_observation_checklist(item, review)
            item["paperObservationChecklist"] = checklist
            task = tasks.get(artifact_id) if isinstance(tasks.get(artifact_id), dict) else None
            recent_logs = _logs_for_artifact(logs_by_artifact, artifact_id, limit=5)
            item["paperObservationTask"] = _build_paper_observation_task_view(item, task, checklist, recent_logs)
            all_items.append(item)
    artifacts = index.get("artifacts") if isinstance(index.get("artifacts"), list) else all_items
    summary = index.get("summary") if isinstance(index.get("summary"), dict) else {}
    review_counts = _review_status_counts([item for item in artifacts if isinstance(item, dict)])
    task_counts = _task_status_counts([item for item in artifacts if isinstance(item, dict)])
    summary["reviewStatusCounts"] = review_counts
    summary["paperObservationTaskStatusCounts"] = task_counts
    summary["manualReviewCount"] = sum(count for status, count in review_counts.items() if status != "unreviewed")
    summary["activePaperObservationTaskCount"] = task_counts.get("active", 0)
    summary["paperObservationLogCount"] = sum(
        len(rows) for rows in logs_by_artifact.values() if isinstance(rows, list)
    )
    summary["mlCoverage"] = _ml_coverage_summary([item for item in artifacts if isinstance(item, dict)])
    index["summary"] = summary
    return index


def scan_quant_engine() -> dict[str, Any]:
    quant_path = get_quant_engine_path()
    reports_dir = quant_path / "reports"
    state = load_state()
    strategies: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []

    if reports_dir.exists():
        report_paths: dict[str, Path] = {}
        for pattern in ("v13_5_*_report.json", "v13_7_1*_report.json"):
            for report_path in sorted(reports_dir.glob(pattern)):
                report_paths[str(report_path)] = report_path
        for report_path in sorted(report_paths.values()):
            report = _read_json(report_path)
            if report:
                reports.append(_report_summary(report, report_path))

        package_path = reports_dir / "v13_5_21_local_paper_refresh_candidate_package.json"
        package = _read_json(package_path)
        report = _read_json(reports_dir / "v13_5_21_local_paper_refresh_candidate_report.json")
        if package:
            strategies.append(_strategy_from_package(package, report, package_path))

        alpha191_path = reports_dir / "v13_5_23_alpha191_crypto_subset_replay_report.json"
        alpha191_report = _read_json(alpha191_path)
        if alpha191_report:
            strategies.append(_strategy_from_alpha191_report(alpha191_report, alpha191_path))

    runtime_status = _read_json(reports_dir / "runtime_status.json") if reports_dir.exists() else None
    signal_tape = _read_json(reports_dir / "signal_tape.json") if reports_dir.exists() else None
    paper_observation_ledger = _read_json(reports_dir / "paper_observation_ledger.json") if reports_dir.exists() else None
    strategy_artifact_index = _read_json(reports_dir / "strategy_artifact_index.json") if reports_dir.exists() else None
    backtest_task_completion = (
        _read_json(reports_dir / "v13_7_13_backtest_task_completion_report.json") if reports_dir.exists() else None
    )
    strategy_learning_loop = _build_strategy_learning_loop(reports_dir) if reports_dir.exists() else {}
    if strategy_artifact_index:
        strategy_artifact_index = _apply_artifact_reviews(strategy_artifact_index, state)

    state_by_strategy = state.get("strategies", {})
    for strategy in strategies:
        override = state_by_strategy.get(strategy["strategyId"], {})
        strategy["consoleStatus"] = override.get("status") or strategy["suggestedStatus"]
        strategy["consoleNote"] = override.get("note") or ""
        strategy["consoleUpdatedAt"] = override.get("updatedAt")

    payload = {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "quantEnginePath": str(quant_path),
        "quantEngineAvailable": quant_path.exists(),
        "reportsDirAvailable": reports_dir.exists(),
        "generatedAt": now_iso(),
        "safetyBoundary": SAFETY_BOUNDARY,
        "strategies": strategies,
        "reports": sorted(reports, key=lambda item: item.get("generatedAt") or "", reverse=True)[:30],
        "runtimeStatus": runtime_status or {},
        "signalTape": signal_tape or {},
        "paperObservationLedger": paper_observation_ledger or {},
        "strategyArtifactIndex": strategy_artifact_index or {},
        "backtestTaskCompletion": backtest_task_completion or {},
        "strategyLearningLoop": strategy_learning_loop,
    }
    payload["strategyCandidateQueue"] = _apply_backtest_completion_to_candidate_queue(
        _build_strategy_candidate_queue(payload["strategyArtifactIndex"]),
        payload["backtestTaskCompletion"],
    )
    payload["forwardValidation"] = _build_forward_validation_summary(payload["strategyArtifactIndex"])
    payload["researchTaskBoard"] = _build_research_task_board(
        payload["strategyCandidateQueue"],
        payload["forwardValidation"],
    )
    write_mobile_status(build_mobile_status(payload))
    return payload


def _compact_strategy_artifact_index(index: dict[str, Any], limit: int = 30) -> dict[str, Any]:
    artifacts = index.get("artifacts") if isinstance(index.get("artifacts"), list) else []
    top_artifacts = artifacts if artifacts else index.get("topArtifacts") if isinstance(index.get("topArtifacts"), list) else []
    return {
        "version": index.get("version"),
        "generatedAt": index.get("generatedAt"),
        "source": index.get("source"),
        "summary": index.get("summary") if isinstance(index.get("summary"), dict) else {},
        "safetyBoundary": index.get("safetyBoundary") if isinstance(index.get("safetyBoundary"), dict) else {},
        "topArtifacts": top_artifacts[:limit],
    }


def _compact_paper_observation_tasks(index: dict[str, Any], limit: int = 30) -> dict[str, Any]:
    artifacts = index.get("artifacts") if isinstance(index.get("artifacts"), list) else []
    top_artifacts = artifacts if artifacts else index.get("topArtifacts") if isinstance(index.get("topArtifacts"), list) else []
    tasks = []
    for artifact in top_artifacts:
        if not isinstance(artifact, dict):
            continue
        task = artifact.get("paperObservationTask") if isinstance(artifact.get("paperObservationTask"), dict) else None
        if not task:
            continue
        if task.get("taskStatus") == "planned" and artifact.get("reviewStatus") != "paper_observation":
            continue
        tasks.append({
            **task,
            "title": artifact.get("displayName") or artifact.get("title"),
            "originalTitle": artifact.get("title"),
            "displaySubtitle": artifact.get("displaySubtitle"),
            "strategyId": artifact.get("strategyId"),
            "version": artifact.get("version"),
            "readinessTier": artifact.get("readinessTier"),
            "reviewStatus": artifact.get("reviewStatus"),
            "researchScore": artifact.get("researchScore"),
            "metrics": artifact.get("metrics") if isinstance(artifact.get("metrics"), dict) else {},
        })
    return {
        "version": index.get("version"),
        "generatedAt": index.get("generatedAt"),
        "source": CONTROL_CONSOLE_SOURCE,
        "summary": {
            "totalTasks": len(tasks),
            "activeCount": sum(1 for item in tasks if item.get("taskStatus") == "active"),
            "pausedCount": sum(1 for item in tasks if item.get("taskStatus") == "paused"),
            "completedCount": sum(1 for item in tasks if item.get("taskStatus") == "completed"),
            "rejectedCount": sum(1 for item in tasks if item.get("taskStatus") == "rejected"),
            "healthyCount": sum(1 for item in tasks if (item.get("health") or {}).get("healthLabel") == "healthy_observation"),
            "needsReviewCount": sum(1 for item in tasks if (item.get("health") or {}).get("healthLabel") == "needs_review"),
            "totalLogCount": sum(int((item.get("health") or {}).get("logCount") or 0) for item in tasks),
            "latestLogAt": max(
                [str((item.get("health") or {}).get("latestLogAt") or "") for item in tasks],
                default="",
            )
            or None,
        },
        "tasks": tasks[:limit],
    }


def _is_smoke_task(task: dict[str, Any]) -> bool:
    text = " ".join(
        str(task.get(key) or "").lower()
        for key in ("note", "source", "taskLabel", "title", "originalTitle")
    )
    return any(marker in text for marker in ("smoke", "test-only", "接口 smoke", "测试任务"))


def _forward_gate_label(value: str) -> str:
    labels = {
        "needs_active_validation": "还没有正式验证中的策略",
        "waiting_until_review_date": "等待 7 月 10 日前向验收",
        "needs_observation_logs": "需要补观察日志",
        "needs_rule_match": "需要至少一次规则匹配",
        "needs_risk_review": "需要先复核风险/失效记录",
        "eligible_for_paper_review": "可进入纸面模拟观察复核",
    }
    return labels.get(value, value)


def _build_forward_validation_summary(index: dict[str, Any]) -> dict[str, Any]:
    artifacts = index.get("artifacts") if isinstance(index.get("artifacts"), list) else []
    tasks: list[dict[str, Any]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        task = artifact.get("paperObservationTask") if isinstance(artifact.get("paperObservationTask"), dict) else None
        if not task:
            continue
        task = {
            **task,
            "title": artifact.get("displayName") or artifact.get("title"),
            "originalTitle": artifact.get("title"),
            "displaySubtitle": artifact.get("displaySubtitle"),
            "strategyId": artifact.get("strategyId"),
            "version": artifact.get("version"),
            "readinessTier": artifact.get("readinessTier"),
            "reviewStatus": artifact.get("reviewStatus"),
            "metrics": artifact.get("metrics") if isinstance(artifact.get("metrics"), dict) else {},
        }
        task["isTestTask"] = _is_smoke_task(task)
        tasks.append(task)

    active_tasks = [task for task in tasks if task.get("taskStatus") == "active"]
    test_active_tasks = [task for task in active_tasks if task.get("isTestTask")]
    effective_active_tasks = [task for task in active_tasks if not task.get("isTestTask")]
    planned_tasks = [task for task in tasks if task.get("taskStatus") == "planned"]
    health_rows = [task.get("health") for task in tasks if isinstance(task.get("health"), dict)]
    total_logs = sum(int(row.get("logCount") or 0) for row in health_rows)
    rule_matched = sum(int(row.get("ruleMatchedCount") or 0) for row in health_rows)
    invalidated = sum(int(row.get("invalidatedCount") or 0) for row in health_rows)
    risk_warnings = sum(int(row.get("riskWarningCount") or 0) for row in health_rows)

    today = datetime.now(BEIJING_TZ).date()
    days_until_review = (FORWARD_VALIDATION_REVIEW_DATE - today).days
    if not effective_active_tasks:
        gate = "needs_active_validation"
    elif days_until_review > 0:
        gate = "waiting_until_review_date"
    elif total_logs < 3:
        gate = "needs_observation_logs"
    elif rule_matched < 1:
        gate = "needs_rule_match"
    elif invalidated > 0 or risk_warnings > 0:
        gate = "needs_risk_review"
    else:
        gate = "eligible_for_paper_review"

    top_candidates = sorted(
        planned_tasks,
        key=lambda item: (
            float(item.get("progressPct") or 0),
            float((item.get("health") or {}).get("healthScore") or 0),
        ),
        reverse=True,
    )[:8]

    return {
        "version": CONTROL_CONSOLE_VERSION,
        "generatedAt": now_iso(),
        "source": CONTROL_CONSOLE_SOURCE,
        "reviewDate": FORWARD_VALIDATION_REVIEW_DATE.isoformat(),
        "reviewDateLabel": FORWARD_VALIDATION_REVIEW_LABEL,
        "daysUntilReview": max(days_until_review, 0),
        "strictActiveValidationCount": len(effective_active_tasks),
        "rawActiveTaskCount": len(active_tasks),
        "testOnlyActiveTaskCount": len(test_active_tasks),
        "plannedCandidateCount": len(planned_tasks),
        "candidatePoolCount": len(tasks),
        "artifactPoolCount": len(artifacts),
        "totalObservationLogCount": total_logs,
        "ruleMatchedCount": rule_matched,
        "invalidatedCount": invalidated,
        "riskWarningCount": risk_warnings,
        "acceptanceGate": gate,
        "acceptanceGateLabel": _forward_gate_label(gate),
        "canEnterPaperSimulationReview": gate == "eligible_for_paper_review",
        "validationMethod": [
            "先把候选策略标记为纸面观察，形成 active 验证任务。",
            "每天记录无信号、看到信号、规则匹配、错过、失效、风险提醒。",
            "7 月 10 日只做验收复核，不自动进入实盘或下单。",
            "至少需要观察日志、规则匹配记录和风险记录，不能只看历史回测。",
        ],
        "minimumAcceptanceChecks": [
            "至少 1 条正式 active 验证任务，且不是 smoke/test 任务。",
            "至少 3 条前向观察日志。",
            "至少 1 次规则匹配记录。",
            "没有未处理的条件失效或风险提醒。",
            "继续保持 Trade API / Withdraw API / API Key / 自动交易全部关闭。",
        ],
        "activeValidationTasks": effective_active_tasks[:5],
        "testOnlyActiveTasks": test_active_tasks[:5],
        "topCandidatesForPromotion": top_candidates,
        "answerSummary": (
            f"严格口径：{len(effective_active_tasks)} 条正式验证中；"
            f"系统 active 口径：{len(active_tasks)} 条，其中测试任务 {len(test_active_tasks)} 条；"
            f"候选池：{len(tasks)} 条。"
        ),
        "safetyNote": "Forward validation is a research acceptance workflow only. It does not create orders.",
    }


def _compact_signal_tape(signal_tape: dict[str, Any], limit: int = 20) -> dict[str, Any]:
    signals = signal_tape.get("signals") if isinstance(signal_tape.get("signals"), list) else []
    return {
        "version": signal_tape.get("version"),
        "generatedAt": signal_tape.get("generatedAt"),
        "source": signal_tape.get("source"),
        "summary": signal_tape.get("summary") if isinstance(signal_tape.get("summary"), dict) else {},
        "signals": signals[:limit],
    }


def _compact_paper_observation_ledger(paper_ledger: dict[str, Any], limit: int = 20) -> dict[str, Any]:
    observations = paper_ledger.get("observations") if isinstance(paper_ledger.get("observations"), list) else []
    return {
        "version": paper_ledger.get("version"),
        "generatedAt": paper_ledger.get("generatedAt"),
        "source": paper_ledger.get("source"),
        "summary": paper_ledger.get("summary") if isinstance(paper_ledger.get("summary"), dict) else {},
        "observations": observations[:limit],
    }


def _compact_runtime_status(runtime_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": runtime_status.get("version"),
        "generatedAt": runtime_status.get("generatedAt"),
        "source": runtime_status.get("source"),
        "activeStrategy": runtime_status.get("activeStrategy")
        if isinstance(runtime_status.get("activeStrategy"), dict)
        else None,
        "strategyCount": runtime_status.get("strategyCount"),
        "reportCount": runtime_status.get("reportCount"),
        "signalTapeCount": runtime_status.get("signalTapeCount"),
        "paperObservationCount": runtime_status.get("paperObservationCount"),
        "runtimeHealth": runtime_status.get("runtimeHealth")
        if isinstance(runtime_status.get("runtimeHealth"), dict)
        else {},
        "latestSignalTime": runtime_status.get("latestSignalTime"),
        "paperObservationSummary": runtime_status.get("paperObservationSummary")
        if isinstance(runtime_status.get("paperObservationSummary"), dict)
        else {},
        "nextStep": runtime_status.get("nextStep"),
        "contractFiles": runtime_status.get("contractFiles")
        if isinstance(runtime_status.get("contractFiles"), dict)
        else {},
    }


def _strategy_signal_count(strategy: dict[str, Any] | None) -> int | None:
    if not strategy:
        return None
    metrics = strategy.get("metrics") if isinstance(strategy.get("metrics"), dict) else {}
    value = strategy.get("selectedSignalCount") or metrics.get("filledSignalCount") or metrics.get("tradeCount")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _pick_primary_strategy(strategies: list[dict[str, Any]]) -> dict[str, Any] | None:
    for status in ("local_paper_ready", "forward_testing", "research_only"):
        strategy = next((item for item in strategies if item.get("consoleStatus") == status), None)
        if strategy:
            return strategy
    return strategies[0] if strategies else None


def _build_command_summary(payload: dict[str, Any]) -> dict[str, Any]:
    strategies = payload.get("strategies") if isinstance(payload.get("strategies"), list) else []
    reports = payload.get("reports") if isinstance(payload.get("reports"), list) else []
    primary = _pick_primary_strategy(strategies)
    metrics = primary.get("metrics", {}) if primary else {}
    ready_count = sum(1 for item in strategies if item.get("consoleStatus") == "local_paper_ready")
    research_count = sum(1 for item in strategies if item.get("consoleStatus") == "research_only")
    signal_count = _strategy_signal_count(primary)
    win_rate = _metric_number(metrics, "winRatePct")
    profit_factor = _metric_number(metrics, "profitFactor")
    reward_risk = _metric_number(metrics, "rewardRiskRatio")
    max_drawdown = _metric_number(metrics, "maxDrawdownPct")

    health_score = 0
    if primary:
        health_score += 20
    if ready_count > 0:
        health_score += 20
    if signal_count and signal_count >= 10:
        health_score += 15
    if profit_factor is not None and profit_factor >= 1:
        health_score += 15
    if reward_risk is not None and reward_risk >= 1.5:
        health_score += 15
    if max_drawdown is not None and max_drawdown <= 25:
        health_score += 15
    health_score = min(100, health_score)

    if ready_count > 0:
        readiness = "local_paper_review_ready"
    elif primary:
        readiness = "research_observer_ready"
    else:
        readiness = "needs_quant_report_import"

    if health_score >= 75:
        health_label = "healthy_research_runtime"
    elif health_score >= 45:
        health_label = "partial_research_runtime"
    else:
        health_label = "needs_more_data"

    return {
        "activeStrategyId": primary.get("strategyId") if primary else None,
        "activeStrategyTitle": primary.get("title") if primary else None,
        "activeStrategyVersion": primary.get("version") if primary else None,
        "activeStatus": primary.get("consoleStatus") if primary else None,
        "readyCount": ready_count,
        "researchCount": research_count,
        "reportCount": len(reports),
        "strategyCount": len(strategies),
        "signalCount": signal_count,
        "winRatePct": win_rate,
        "profitFactor": profit_factor,
        "rewardRiskRatio": reward_risk,
        "maxDrawdownPct": max_drawdown,
        "healthScore": health_score,
        "healthLabel": health_label,
        "readiness": readiness,
        "executionLockLabel": "read_only_no_trade_execution",
        "nextStep": "Review strategy, signal, risk, and local paper evidence before any future manual action.",
    }


def build_mobile_status(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": payload["version"],
        "generatedAt": payload["generatedAt"],
        "source": payload["source"],
        "safetyBoundary": payload["safetyBoundary"],
        "strategyCount": len(payload["strategies"]),
        "commandSummary": _build_command_summary(payload),
        "runtimeStatus": _compact_runtime_status(payload.get("runtimeStatus", {})),
        "signalTape": _compact_signal_tape(payload.get("signalTape", {})),
        "paperObservationLedger": _compact_paper_observation_ledger(payload.get("paperObservationLedger", {})),
        "strategyArtifactIndex": _compact_strategy_artifact_index(payload.get("strategyArtifactIndex", {})),
        "paperObservationTasks": _compact_paper_observation_tasks(payload.get("strategyArtifactIndex", {})),
        "forwardValidation": payload.get("forwardValidation")
        or _build_forward_validation_summary(payload.get("strategyArtifactIndex", {})),
        "strategyCandidateQueue": payload.get("strategyCandidateQueue") or _build_strategy_candidate_queue(
            payload.get("strategyArtifactIndex", {})
        ),
        "researchTaskBoard": payload.get("researchTaskBoard")
        or _build_research_task_board(
            payload.get("strategyCandidateQueue") or _build_strategy_candidate_queue(
                payload.get("strategyArtifactIndex", {})
            ),
            payload.get("forwardValidation")
            or _build_forward_validation_summary(payload.get("strategyArtifactIndex", {})),
        ),
        "exchangeConnectivity": _mobile_exchange_connectivity(),
        "strategies": [
            {
                "strategyId": item["strategyId"],
                "title": item["title"],
                "version": item["version"],
                "consoleStatus": item["consoleStatus"],
                "suggestedStatus": item["suggestedStatus"],
                "exchangeDryRunApproved": item["exchangeDryRunApproved"],
                "liveTradingApproved": item["liveTradingApproved"],
                "metrics": item["metrics"],
            }
            for item in payload["strategies"]
        ],
    }


def _mobile_exchange_connectivity() -> dict[str, Any]:
    probe = read_exchange_probe_results()
    if not probe:
        return {
            "latestProbeAt": None,
            "publicOnly": True,
            "resultCount": 0,
            "connectedExchangeCount": 0,
            "message": "No public exchange probe has been run yet.",
        }
    results = probe.get("results") if isinstance(probe.get("results"), list) else []
    return {
        "latestProbeAt": probe.get("generatedAt"),
        "publicOnly": True,
        "symbol": probe.get("symbol"),
        "timeframe": probe.get("timeframe"),
        "resultCount": len(results),
        "connectedExchangeCount": sum(1 for item in results if item.get("ok")),
        "exchanges": [
            {
                "exchange": item.get("exchange"),
                "ok": item.get("ok"),
                "latencyMs": item.get("latencyMs"),
                "apiKeyUsed": item.get("apiKeyUsed"),
                "ordersAllowed": item.get("ordersAllowed"),
            }
            for item in results
        ],
    }


def import_now() -> dict[str, Any]:
    payload = scan_quant_engine()
    append_audit(
        "quant_reports_imported",
        {
            "strategyCount": len(payload["strategies"]),
            "reportCount": len(payload["reports"]),
            "artifactCount": len(payload.get("strategyArtifactIndex", {}).get("artifacts", []))
            if isinstance(payload.get("strategyArtifactIndex"), dict)
            else 0,
            "quantEnginePath": payload["quantEnginePath"],
        },
    )
    return payload


def main() -> None:
    payload = import_now()
    print(json.dumps({
        "strategyCount": len(payload["strategies"]),
        "reportCount": len(payload["reports"]),
        "quantEngineAvailable": payload["quantEngineAvailable"],
        "reportsDirAvailable": payload["reportsDirAvailable"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
