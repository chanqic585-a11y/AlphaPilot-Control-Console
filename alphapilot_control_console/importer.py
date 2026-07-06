from __future__ import annotations

import json
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

CONTROL_CONSOLE_VERSION = "V13.7.8"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_8"


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
    return {"kind": "report"}


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
    index["summary"] = summary
    return index


def scan_quant_engine() -> dict[str, Any]:
    quant_path = get_quant_engine_path()
    reports_dir = quant_path / "reports"
    state = load_state()
    strategies: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []

    if reports_dir.exists():
        for report_path in sorted(reports_dir.glob("v13_5_*_report.json")):
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
    }
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
