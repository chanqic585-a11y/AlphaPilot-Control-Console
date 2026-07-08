from __future__ import annotations

import re
from typing import Any

from .config import SAFETY_BOUNDARY
from .local_sandbox_concentration_review import build_local_sandbox_concentration_review
from .state_store import now_iso


CONTROL_CONSOLE_VERSION = "V13.8.8"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_8"


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


def _family_name(strategy_name: str) -> str:
    text = str(strategy_name or "").strip()
    text = re.sub(r"\bATR\s*\d+(?:\.\d+)?\b", "ATRx", text, flags=re.IGNORECASE)
    text = re.sub(r"Top\s*\d+", "Topx", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "unknown"


def _coverage_score(row: dict[str, Any]) -> float:
    unique_pairs = _safe_int(row.get("uniquePairCount"))
    top_pair_share = _safe_float(row.get("topPairShare"), 1.0)
    unique_windows = _safe_int(row.get("uniqueReplayWindowCount"))
    pair_points = min(unique_pairs, 8) / 8 * 14
    concentration_points = max(0.0, 1.0 - top_pair_share) * 18
    window_points = min(unique_windows, 40) / 40 * 8
    return round(pair_points + concentration_points + window_points, 2)


def _performance_score(row: dict[str, Any]) -> float:
    win_rate = _safe_float(row.get("winRate"))
    profit_factor = _safe_float(row.get("profitFactor"))
    total_r = _safe_float(row.get("totalR"))
    closed = max(1, _safe_int(row.get("closedSamples")))
    expectancy_r = total_r / closed
    win_points = max(0.0, min(16.0, (win_rate - 35.0) / 25.0 * 16.0))
    pf_points = max(0.0, min(18.0, (profit_factor - 1.0) / 1.5 * 18.0))
    expectancy_points = max(0.0, min(8.0, expectancy_r / 0.8 * 8.0))
    return round(win_points + pf_points + expectancy_points, 2)


def _sample_score(row: dict[str, Any]) -> float:
    closed = _safe_int(row.get("closedSamples"))
    return round(min(closed, 80) / 80 * 15, 2)


def _risk_score(row: dict[str, Any]) -> float:
    max_drawdown_r = _safe_float(row.get("maxDrawdownR"))
    warnings = row.get("warnings") if isinstance(row.get("warnings"), list) else []
    score = 18.0
    score -= min(max_drawdown_r, 8.0) * 1.2
    if "loss_streak_warning" in warnings:
        score -= 4
    if "risk_warning_needs_review" in warnings:
        score -= 5
    if "invalidated_samples_need_review" in warnings:
        score -= 5
    return round(max(0.0, score), 2)


def _regime_score(row: dict[str, Any]) -> float:
    regimes = row.get("marketRegimeBreakdown") if isinstance(row.get("marketRegimeBreakdown"), list) else []
    non_unknown = [
        item
        for item in regimes
        if isinstance(item, dict) and str(item.get("marketRegime") or "") != "unknown"
    ]
    unique_regimes = len(non_unknown)
    top_share = max((_safe_float(item.get("sampleShare")) for item in non_unknown), default=1.0)
    diversity = min(unique_regimes, 3) / 3 * 7
    balance = max(0.0, 1.0 - top_share) * 5
    return round(diversity + balance, 2)


def _score_row(row: dict[str, Any]) -> dict[str, Any]:
    sample = _sample_score(row)
    performance = _performance_score(row)
    coverage = _coverage_score(row)
    risk = _risk_score(row)
    regime = _regime_score(row)
    total = round(sample + performance + coverage + risk + regime, 2)
    if total >= 85:
        grade = "A"
    elif total >= 75:
        grade = "B"
    elif total >= 65:
        grade = "C"
    else:
        grade = "D"
    return {
        "totalScore": total,
        "grade": grade,
        "components": {
            "sampleScore": sample,
            "performanceScore": performance,
            "coverageScore": coverage,
            "riskScore": risk,
            "regimeScore": regime,
        },
    }


def _decision(row: dict[str, Any], score: dict[str, Any], is_representative: bool) -> tuple[str, str, list[str]]:
    reasons: list[str] = []
    profit_factor = _safe_float(row.get("profitFactor"))
    win_rate = _safe_float(row.get("winRate"))
    top_pair_share = _safe_float(row.get("topPairShare"), 1.0)
    closed = _safe_int(row.get("closedSamples"))
    if closed < 30:
        reasons.append("闭合样本不足 30，不能进入结果质量复核。")
        return "wait_for_samples", "继续补样本", reasons
    if profit_factor < 1.2 or win_rate < 45:
        reasons.append("PF 或胜率低于下一轮复核底线。")
        return "downgrade_reference", "降级为参考样本", reasons
    if top_pair_share >= 0.8:
        reasons.append("样本仍然集中在单一币种，先扩展覆盖。")
        return "expand_coverage", "继续扩展覆盖", reasons
    if is_representative:
        reasons.append("该策略是同族当前代表变体，进入下一轮风控和变体复核。")
        return "keep_representative_next_review", "保留代表策略", reasons
    reasons.append("同族已有更优代表，当前变体先合并为对照样本。")
    return "merge_duplicate_variant", "合并为对照变体", reasons


def _rank_key(row: dict[str, Any]) -> tuple[float, float, int, float]:
    return (
        _safe_float(row.get("resultQuality", {}).get("totalScore")),
        _safe_float(row.get("profitFactor")),
        _safe_int(row.get("closedSamples")),
        _safe_float(row.get("totalR")),
    )


def build_local_sandbox_result_review() -> dict[str, Any]:
    concentration = build_local_sandbox_concentration_review()
    raw_rows = [row for row in concentration.get("strategies", []) if isinstance(row, dict)]
    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        scored = _score_row(row)
        family = _family_name(str(row.get("strategyName") or row.get("taskId") or "unknown"))
        rows.append({
            **row,
            "familyName": family,
            "resultQuality": scored,
        })
    families: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        families.setdefault(str(row.get("familyName") or "unknown"), []).append(row)

    family_reviews = []
    representative_task_ids: set[str] = set()
    for family, items in families.items():
        sorted_items = sorted(items, key=_rank_key, reverse=True)
        representative = sorted_items[0] if sorted_items else {}
        representative_task_id = str(representative.get("taskId") or "")
        if representative_task_id:
            representative_task_ids.add(representative_task_id)
        family_reviews.append({
            "familyName": family,
            "variantCount": len(items),
            "representativeTaskId": representative_task_id,
            "representativeName": representative.get("strategyName"),
            "representativeScore": representative.get("resultQuality", {}).get("totalScore"),
            "representativeGrade": representative.get("resultQuality", {}).get("grade"),
            "mergedVariantTaskIds": [str(item.get("taskId") or "") for item in sorted_items[1:]],
            "reviewNote": "保留当前得分最高的代表策略，其余同族变体作为对照样本继续留档。",
        })

    reviewed_rows = []
    for row in rows:
        is_representative = str(row.get("taskId") or "") in representative_task_ids
        decision, label, reasons = _decision(row, row.get("resultQuality", {}), is_representative)
        reviewed_rows.append({
            **row,
            "resultDecision": decision,
            "resultDecisionLabel": label,
            "resultReviewReasons": reasons,
            "manualActionRequired": False,
        })
    reviewed_rows.sort(
        key=lambda row: (
            row.get("resultDecision") != "keep_representative_next_review",
            row.get("resultDecision") != "merge_duplicate_variant",
            -_safe_float(row.get("resultQuality", {}).get("totalScore")),
        )
    )
    representative_count = sum(1 for row in reviewed_rows if row.get("resultDecision") == "keep_representative_next_review")
    merge_count = sum(1 for row in reviewed_rows if row.get("resultDecision") == "merge_duplicate_variant")
    downgrade_count = sum(1 for row in reviewed_rows if row.get("resultDecision") == "downgrade_reference")
    expand_count = sum(1 for row in reviewed_rows if row.get("resultDecision") == "expand_coverage")
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "strategyCount": len(reviewed_rows),
            "familyCount": len(family_reviews),
            "representativeCount": representative_count,
            "mergeCandidateCount": merge_count,
            "downgradeCount": downgrade_count,
            "coverageExpansionCount": expand_count,
            "nextReviewCandidateCount": representative_count,
            "manualActionRequired": False,
            "topIssue": "策略变体需要合并" if merge_count else "继续结果质量复核",
            "nextAction": "保留每个策略族的代表变体，其余变体作为对照样本；下一步复核风控、费用滑点和前向稳定性。",
        },
        "strategies": reviewed_rows,
        "familyReviews": sorted(family_reviews, key=lambda item: _safe_float(item.get("representativeScore")), reverse=True),
        "concentrationSummary": concentration.get("summary"),
        "safetyBoundary": SAFETY_BOUNDARY,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyNote": "Result review is local research only. It cannot approve testnet, live trading, API keys, private exchange access, or orders.",
    }
