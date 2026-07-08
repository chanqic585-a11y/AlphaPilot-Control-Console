from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .config import SAFETY_BOUNDARY
from .local_sandbox_quality_center import build_local_sandbox_quality_center
from .simulation_review import build_simulation_review
from .state_store import list_paper_observation_logs, now_iso


CONTROL_CONSOLE_VERSION = "V13.8.7"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_7"
REVIEW_MINIMUM_CLOSED_SAMPLES = 30
PAIR_CONCENTRATION_LIMIT = 0.8
WINDOW_CONCENTRATION_LIMIT = 0.5
MIN_UNIQUE_REPLAY_WINDOWS = 5


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed else fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _extract_outcome_r(row: dict[str, Any]) -> float | None:
    if row.get("outcomeR") is not None:
        return _safe_float(row.get("outcomeR"))
    text = str(row.get("outcome") or "").strip().upper().replace(" ", "")
    if not text.endswith("R"):
        return None
    return _safe_float(text[:-1])


def _task_logs(task_id: str) -> list[dict[str, Any]]:
    rows = list_paper_observation_logs(task_id)
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _closed_logs(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in logs if _extract_outcome_r(row) is not None]


def _group_breakdown(logs: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for row in logs:
        value = str(row.get(key) or "unknown").strip() or "unknown"
        counter[value] += 1
    total = sum(counter.values())
    if total <= 0:
        return []
    return [
        {
            key: value,
            "sampleCount": count,
            "sampleShare": round(count / total, 4),
        }
        for value, count in counter.most_common()
    ]


def _outcome_distribution(logs: list[dict[str, Any]]) -> dict[str, Any]:
    wins = 0
    losses = 0
    flats = 0
    total_r = 0.0
    for row in logs:
        outcome_r = _extract_outcome_r(row)
        if outcome_r is None:
            continue
        total_r += outcome_r
        if outcome_r > 0:
            wins += 1
        elif outcome_r < 0:
            losses += 1
        else:
            flats += 1
    total = wins + losses + flats
    return {
        "winCount": wins,
        "lossCount": losses,
        "flatCount": flats,
        "closedSamples": total,
        "winRate": round(wins / total * 100, 2) if total else None,
        "totalR": round(total_r, 4),
    }


def _strategy_family_name(strategy_name: str) -> str:
    text = strategy_name.strip()
    text = re.sub(r"\bATR\s*\d+(?:\.\d+)?\b", "ATRx", text, flags=re.IGNORECASE)
    text = re.sub(r"Top\s*\d+", "Topx", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "unknown"


def _variant_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        family = _strategy_family_name(str(row.get("strategyName") or row.get("taskId") or "unknown"))
        grouped.setdefault(family, []).append(row)
    result = []
    for family, items in grouped.items():
        if len(items) <= 1:
            continue
        result.append({
            "familyName": family,
            "variantCount": len(items),
            "taskIds": [str(item.get("taskId") or "") for item in items],
            "strategyNames": [str(item.get("strategyName") or "") for item in items],
            "bestByClosedSamples": max(items, key=lambda item: _safe_int(item.get("closedSamples"))).get("strategyName"),
            "reviewNote": "同一策略族存在多个参数/资产筛选变体，后续应做变体合并或留一复核。",
        })
    result.sort(key=lambda item: -_safe_int(item.get("variantCount")))
    return result


def _decision_for_strategy(
    row: dict[str, Any],
    pair_breakdown: list[dict[str, Any]],
    window_breakdown: list[dict[str, Any]],
) -> tuple[str, str, list[str]]:
    closed_samples = _safe_int(row.get("closedSamples"))
    profit_factor = row.get("profitFactor")
    win_rate = row.get("winRate")
    max_drawdown_r = _safe_float(row.get("maxDrawdownR"))
    top_pair_share = _safe_float(pair_breakdown[0].get("sampleShare")) if pair_breakdown else 0.0
    top_window_share = _safe_float(window_breakdown[0].get("sampleShare")) if window_breakdown else 0.0
    reasons: list[str] = []

    if closed_samples < REVIEW_MINIMUM_CLOSED_SAMPLES:
        reasons.append(f"闭合样本 {closed_samples}/{REVIEW_MINIMUM_CLOSED_SAMPLES}，未达到集中度复核最低门槛。")
        return ("wait_for_sample_gate", "继续收集闭合样本", reasons)
    if top_pair_share >= PAIR_CONCENTRATION_LIMIT:
        top_pair = pair_breakdown[0].get("pair") if pair_breakdown else "unknown"
        reasons.append(f"样本过度集中在 {top_pair}，占比 {round(top_pair_share * 100, 2)}%。")
        reasons.append("下一步优先扩展币种覆盖，不能因为单一币种表现好就进入 testnet。")
        return ("expand_pair_coverage", "扩展币种覆盖后再复核", reasons)
    if len(window_breakdown) < MIN_UNIQUE_REPLAY_WINDOWS or top_window_share >= WINDOW_CONCENTRATION_LIMIT:
        reasons.append(f"回放窗口覆盖不足，唯一窗口数 {len(window_breakdown)}，最高窗口占比 {round(top_window_share * 100, 2)}%。")
        return ("expand_replay_windows", "扩展历史窗口后再复核", reasons)
    if profit_factor is not None and _safe_float(profit_factor) >= 1.5 and _safe_float(win_rate) >= 45 and max_drawdown_r <= 3:
        reasons.append("样本、胜率、PF 和回撤满足下一轮复核条件，但仍不是实盘许可。")
        return ("ready_for_next_review", "进入下一轮人工/自动复核", reasons)
    reasons.append("未触发硬性淘汰，但优势还不够清晰。")
    return ("continue_observing", "继续本地沙盒观察", reasons)


def build_local_sandbox_concentration_review() -> dict[str, Any]:
    quality_center = build_local_sandbox_quality_center()
    simulation_review = build_simulation_review()
    review_by_task = {
        str(row.get("taskId") or ""): row
        for row in simulation_review.get("queue", [])
        if isinstance(row, dict)
    }
    quality_rows = [
        row
        for row in quality_center.get("strategies", [])
        if isinstance(row, dict)
    ]
    variant_groups = _variant_groups(quality_rows)
    strategies = []
    for row in quality_rows:
        task_id = str(row.get("taskId") or "").strip()
        if not task_id:
            continue
        logs = _closed_logs(_task_logs(task_id))
        simulation_row = review_by_task.get(task_id, {})
        breakdowns = simulation_row.get("breakdowns") if isinstance(simulation_row.get("breakdowns"), dict) else {}
        pair_breakdown = breakdowns.get("byPair") if isinstance(breakdowns.get("byPair"), list) else _group_breakdown(logs, "pair")
        window_breakdown = _group_breakdown(logs, "replayWindowId")
        regime_breakdown = breakdowns.get("byMarketRegime") if isinstance(breakdowns.get("byMarketRegime"), list) else _group_breakdown(logs, "marketRegime")
        decision, decision_label, reasons = _decision_for_strategy(row, pair_breakdown, window_breakdown)
        closed_samples = _safe_int(row.get("closedSamples"))
        if closed_samples < REVIEW_MINIMUM_CLOSED_SAMPLES and decision == "wait_for_sample_gate":
            review_bucket = "waiting_for_samples"
        elif decision in {"expand_pair_coverage", "expand_replay_windows"}:
            review_bucket = "needs_concentration_expansion"
        elif decision == "ready_for_next_review":
            review_bucket = "next_review_candidate"
        else:
            review_bucket = "continue_observing"
        strategies.append({
            "taskId": task_id,
            "strategyId": row.get("strategyId"),
            "strategyName": row.get("strategyName"),
            "timeframe": row.get("timeframe"),
            "closedSamples": closed_samples,
            "winRate": row.get("winRate"),
            "profitFactor": row.get("profitFactor"),
            "totalR": row.get("totalR"),
            "maxDrawdownR": row.get("maxDrawdownR"),
            "promotionStatus": row.get("promotionStatus"),
            "qualityScore": row.get("qualityScore"),
            "warnings": row.get("warnings") if isinstance(row.get("warnings"), list) else [],
            "outcomeDistribution": _outcome_distribution(logs),
            "pairBreakdown": pair_breakdown,
            "replayWindowBreakdown": window_breakdown,
            "marketRegimeBreakdown": regime_breakdown,
            "topPairShare": pair_breakdown[0].get("sampleShare") if pair_breakdown else None,
            "topReplayWindowShare": window_breakdown[0].get("sampleShare") if window_breakdown else None,
            "uniquePairCount": len(pair_breakdown),
            "uniqueReplayWindowCount": len(window_breakdown),
            "reviewBucket": review_bucket,
            "decision": decision,
            "decisionLabel": decision_label,
            "reviewReasons": reasons,
            "manualActionRequired": False,
        })
    strategies.sort(
        key=lambda item: (
            item["reviewBucket"] != "needs_concentration_expansion",
            item["reviewBucket"] != "next_review_candidate",
            -_safe_int(item.get("closedSamples")),
            -_safe_float(item.get("profitFactor"), -1),
        )
    )
    needs_expansion_count = sum(1 for item in strategies if item.get("reviewBucket") == "needs_concentration_expansion")
    next_review_count = sum(1 for item in strategies if item.get("reviewBucket") == "next_review_candidate")
    waiting_count = sum(1 for item in strategies if item.get("reviewBucket") == "waiting_for_samples")
    if next_review_count and not needs_expansion_count and not waiting_count:
        top_issue = "可进入下一轮复核"
        next_action = "集中度门槛已通过；进入下一轮结果质量、策略变体合并和风控复核。仍不批准 testnet、API Key 或真实订单。"
    elif needs_expansion_count:
        top_issue = "样本集中度过高"
        next_action = "无需手动进入阶段；继续让本地沙盒运行，并优先扩展集中策略的币种和回放窗口覆盖。"
    else:
        top_issue = "继续收集样本"
        next_action = "继续让本地沙盒运行，先补足每条策略的闭合样本和失败样本。"
    summary = {
        "strategyCount": len(strategies),
        "reviewReadyCount": sum(1 for item in strategies if _safe_int(item.get("closedSamples")) >= REVIEW_MINIMUM_CLOSED_SAMPLES),
        "needsConcentrationExpansionCount": needs_expansion_count,
        "nextReviewCandidateCount": next_review_count,
        "waitingForSamplesCount": waiting_count,
        "variantGroupCount": len(variant_groups),
        "topIssue": top_issue,
        "manualActionRequired": False,
        "nextAction": next_action,
    }
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": summary,
        "strategies": strategies,
        "variantGroups": variant_groups,
        "qualityCenterSummary": quality_center.get("summary"),
        "safetyBoundary": SAFETY_BOUNDARY,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyNote": "Concentration review is local research only. It cannot approve testnet, live trading, API keys, private exchange access, or orders.",
    }
