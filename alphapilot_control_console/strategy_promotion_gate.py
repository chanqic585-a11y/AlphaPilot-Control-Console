from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import SAFETY_BOUNDARY, get_quant_engine_path
from .forward_review import build_forward_review
from .short_cycle_candidates import build_short_cycle_candidate_pool
from .state_store import now_iso


CONTROL_CONSOLE_VERSION = "V13.7.39"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_39"

MIN_SAMPLE_COUNT = 30
MIN_SURVIVOR_SAMPLE_COUNT = 100
MIN_PROFIT_FACTOR = 1.25
MIN_REWARD_RISK = 1.65
MIN_STRICT_REWARD_RISK = 1.80
MAX_DRAWDOWN_PCT = 25
MIN_FORWARD_LOGS = 3
MIN_MANUAL_CLOSED_SAMPLES = 1


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    return int(_safe_float(value, fallback))


def _as_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _read_top50_report() -> dict[str, Any] | None:
    report_path = get_quant_engine_path() / "reports" / "v13_7_38_top50_short_cycle_backtest_report.json"
    if not report_path.exists():
        return None
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _metric(item: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = item.get(key)
        if value is not None:
            return _safe_float(value)
    return None


def _candidate_id(item: dict[str, Any]) -> str:
    return str(item.get("artifactId") or item.get("strategyId") or item.get("poolId") or item.get("strategy") or "").strip()


def _negative_sample_from_top50(row: dict[str, Any]) -> dict[str, Any]:
    gate_reasons = [str(item) for item in row.get("gateReasons") or []]
    return {
        "itemId": f"top50::{row.get('strategy')}",
        "title": row.get("label") or row.get("strategy") or "Top50 short-cycle candidate",
        "strategy": row.get("strategy"),
        "timeframe": row.get("timeframe"),
        "bucket": "negative_sample",
        "bucketLabel": "负样本库",
        "gateDecision": "archive_negative_sample",
        "gateLabel": "扩样本失败，归档为负样本",
        "tone": "danger",
        "sampleCount": row.get("totalTrades"),
        "winRatePct": (_safe_float(row.get("winRate")) * 100) if row.get("winRate") is not None else None,
        "profitFactor": row.get("profitFactor"),
        "rewardRiskRatio": row.get("rewardRiskRatio"),
        "totalReturnPct": (_safe_float(row.get("profitTotal")) * 100) if row.get("profitTotal") is not None else None,
        "maxDrawdownPct": (_safe_float(row.get("maxDrawdownAccount")) * 100)
        if row.get("maxDrawdownAccount") is not None
        else None,
        "source": row.get("zip"),
        "reasons": gate_reasons or ["Top50 expanded backtest failed the research gate."],
        "nextAction": "停止前向复核；仅保留为失败样本，用于后续过滤器和策略换代。",
        "safetyNote": "负样本库只用于研究复盘，不会创建订单。",
    }


def _queue_candidate_gate(item: dict[str, Any]) -> dict[str, Any]:
    sample_count = _metric(item, "sampleCount") or 0.0
    win_rate = _metric(item, "winRatePct")
    profit_factor = _metric(item, "profitFactor")
    reward_risk = _metric(item, "rewardRiskRatio")
    drawdown = _metric(item, "maxDrawdownPct")
    total_return = _metric(item, "totalReturnPct")
    queue_type = str(item.get("queueType") or "")
    candidate_decision = str(item.get("candidateDecision") or "")
    ml_status = str(item.get("mlStatus") or "")
    label_status = str(item.get("labelStatus") or "")

    blockers: list[str] = []
    warnings: list[str] = []
    passes: list[str] = []

    if sample_count >= MIN_SURVIVOR_SAMPLE_COUNT:
        passes.append(f"样本 {sample_count:.0f} >= {MIN_SURVIVOR_SAMPLE_COUNT}")
    elif sample_count >= MIN_SAMPLE_COUNT:
        warnings.append(f"样本偏少：{sample_count:.0f}/{MIN_SURVIVOR_SAMPLE_COUNT}")
    else:
        blockers.append(f"样本不足：{sample_count:.0f}/{MIN_SAMPLE_COUNT}")

    if profit_factor is None:
        blockers.append("缺少 PF")
    elif profit_factor >= MIN_PROFIT_FACTOR:
        passes.append(f"PF {profit_factor:.2f} >= {MIN_PROFIT_FACTOR:.2f}")
    else:
        blockers.append(f"PF 不足：{profit_factor:.2f}/{MIN_PROFIT_FACTOR:.2f}")

    if reward_risk is None:
        warnings.append("缺少 RR/2R 标签")
    elif reward_risk >= MIN_STRICT_REWARD_RISK:
        passes.append(f"RR {reward_risk:.2f} >= {MIN_STRICT_REWARD_RISK:.2f}")
    elif reward_risk >= MIN_REWARD_RISK:
        warnings.append(f"RR 接近门槛：{reward_risk:.2f}/{MIN_STRICT_REWARD_RISK:.2f}")
    else:
        blockers.append(f"RR 不足：{reward_risk:.2f}/{MIN_REWARD_RISK:.2f}")

    if drawdown is None:
        warnings.append("缺少最大回撤")
    elif drawdown <= MAX_DRAWDOWN_PCT:
        passes.append(f"回撤 {drawdown:.2f}% <= {MAX_DRAWDOWN_PCT}%")
    else:
        blockers.append(f"回撤过高：{drawdown:.2f}%")

    if total_return is not None and total_return < 0:
        blockers.append(f"总收益为负：{total_return:.2f}%")

    if queue_type in {"rejected", "archived"} or candidate_decision == "rejected_or_archived":
        return {
            "bucket": "archived",
            "bucketLabel": "归档/淘汰",
            "gateDecision": "keep_archived",
            "gateLabel": "保持归档",
            "tone": "danger",
            "reasons": blockers + ["当前队列状态已归档/淘汰。"],
            "passedChecks": passes,
            "warnings": warnings,
        }

    if blockers:
        return {
            "bucket": "needs_work",
            "bucketLabel": "需要补证据",
            "gateDecision": "do_not_promote",
            "gateLabel": "暂不晋级",
            "tone": "warn",
            "reasons": blockers,
            "passedChecks": passes,
            "warnings": warnings,
        }

    if queue_type == "priority_forward_validation" or candidate_decision == "can_forward_validate":
        return {
            "bucket": "survivor",
            "bucketLabel": "幸存者",
            "gateDecision": "keep_for_forward_review",
            "gateLabel": "保留前向复核",
            "tone": "ok",
            "reasons": warnings or ["历史证据达到观察条件。"],
            "passedChecks": passes,
            "warnings": warnings,
            "mlReady": ml_status == "ml_dataset_ready",
            "labelReady": label_status in {"has_2r_and_win_loss_labels", "has_win_loss_labels"},
        }

    return {
        "bucket": "watchlist",
        "bucketLabel": "轻量观察",
        "gateDecision": "watch_only",
        "gateLabel": "只做轻量观察",
        "tone": "neutral",
        "reasons": warnings or ["历史证据尚可，但还不是前向优先级。"],
        "passedChecks": passes,
        "warnings": warnings,
    }


def _build_queue_row(item: dict[str, Any]) -> dict[str, Any]:
    gate = _queue_candidate_gate(item)
    return {
        "itemId": _candidate_id(item),
        "rank": item.get("rank"),
        "title": item.get("title") or item.get("strategyId") or item.get("artifactId"),
        "strategyId": item.get("strategyId"),
        "version": item.get("version"),
        "sourceFile": item.get("sourceFile"),
        "queueType": item.get("queueType"),
        "queueLabel": item.get("queueLabel"),
        "methodLabel": item.get("methodLabel"),
        "mlStatusLabel": item.get("mlStatusLabel"),
        "labelStatusLabel": item.get("labelStatusLabel"),
        "sampleCount": item.get("sampleCount"),
        "winRatePct": item.get("winRatePct"),
        "profitFactor": item.get("profitFactor"),
        "rewardRiskRatio": item.get("rewardRiskRatio"),
        "totalReturnPct": item.get("totalReturnPct"),
        "maxDrawdownPct": item.get("maxDrawdownPct"),
        "priorityScore": item.get("priorityScore"),
        "nextAction": item.get("nextAction"),
        "safetyNote": "策略晋级闸门只做本地研究分桶，不会创建订单。",
        **gate,
    }


def _forward_review_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    review = build_forward_review(payload)
    rows = _as_list(review.get("rows"))
    return {
        "reviewDateLabel": review.get("reviewDateLabel"),
        "summary": review.get("summary") if isinstance(review.get("summary"), dict) else {},
        "readyRows": [row for row in rows if row.get("reviewStatus") == "ready_for_manual_review"],
        "needsForwardRows": [row for row in rows if row.get("reviewStatus") == "needs_forward_data"],
        "blockedRows": [row for row in rows if row.get("reviewStatus") == "blocked_for_review"],
    }


def build_strategy_promotion_gate(payload: dict[str, Any]) -> dict[str, Any]:
    queue = payload.get("strategyCandidateQueue") if isinstance(payload.get("strategyCandidateQueue"), dict) else {}
    candidates = _as_list(queue.get("candidates"))
    queue_rows = [_build_queue_row(item) for item in candidates]
    top50_report = _read_top50_report()
    negative_top50 = [
        _negative_sample_from_top50(row)
        for row in _as_list((top50_report or {}).get("results"))
        if row.get("promotionGate") != "pass_research_gate"
    ]
    short_cycle_pool = build_short_cycle_candidate_pool(payload)
    forward_review = _forward_review_snapshot(payload)

    buckets = {
        "survivors": [row for row in queue_rows if row.get("bucket") == "survivor"],
        "watchlist": [row for row in queue_rows if row.get("bucket") == "watchlist"],
        "needsWork": [row for row in queue_rows if row.get("bucket") == "needs_work"],
        "archived": [row for row in queue_rows if row.get("bucket") == "archived"],
        "negativeSamples": negative_top50,
    }
    for key in ("survivors", "watchlist", "needsWork", "archived"):
        buckets[key].sort(
            key=lambda item: (
                -_safe_float(item.get("priorityScore")),
                -_safe_float(item.get("sampleCount")),
                str(item.get("title") or ""),
            )
        )
    buckets["negativeSamples"].sort(
        key=lambda item: (
            _safe_float(item.get("profitFactor")),
            _safe_float(item.get("maxDrawdownPct")),
        )
    )

    top_survivor = buckets["survivors"][0].get("title") if buckets["survivors"] else None
    promotion_blockers = []
    if not buckets["survivors"]:
        promotion_blockers.append("没有策略同时满足历史质量和前向优先条件。")
    if forward_review["summary"].get("manualForwardLogCount", 0) < MIN_FORWARD_LOGS:
        promotion_blockers.append("真实前向日志不足。")
    if forward_review["summary"].get("manualClosedSampleCount", 0) < MIN_MANUAL_CLOSED_SAMPLES:
        promotion_blockers.append("真实前向闭合样本不足。")

    return {
        "version": CONTROL_CONSOLE_VERSION,
        "generatedAt": now_iso(),
        "source": CONTROL_CONSOLE_SOURCE,
        "summary": {
            "totalCandidates": len(candidates),
            "survivorCount": len(buckets["survivors"]),
            "watchlistCount": len(buckets["watchlist"]),
            "needsWorkCount": len(buckets["needsWork"]),
            "archivedCount": len(buckets["archived"]),
            "negativeSampleCount": len(buckets["negativeSamples"]),
            "topSurvivorTitle": top_survivor,
            "top50ReportLoaded": top50_report is not None,
            "shortCycleCandidateCount": len(short_cycle_pool.get("candidates") or []),
            "forwardReviewReadyCount": len(forward_review["readyRows"]),
            "manualForwardLogCount": forward_review["summary"].get("manualForwardLogCount", 0),
            "manualClosedSampleCount": forward_review["summary"].get("manualClosedSampleCount", 0),
            "promotionBlocked": bool(promotion_blockers),
            "promotionBlockers": promotion_blockers,
            "nextAction": (
                "只保留幸存者进入轻量前向复核；Top50 失败短周期策略归档为负样本。"
                if buckets["survivors"]
                else "先做策略换代和因子组合，不要把失败策略继续送前向。"
            ),
        },
        "thresholds": {
            "minSampleCount": MIN_SAMPLE_COUNT,
            "minSurvivorSampleCount": MIN_SURVIVOR_SAMPLE_COUNT,
            "minProfitFactor": MIN_PROFIT_FACTOR,
            "minRewardRisk": MIN_REWARD_RISK,
            "strictRewardRisk": MIN_STRICT_REWARD_RISK,
            "maxDrawdownPct": MAX_DRAWDOWN_PCT,
            "minForwardLogs": MIN_FORWARD_LOGS,
            "minManualClosedSamples": MIN_MANUAL_CLOSED_SAMPLES,
        },
        "buckets": buckets,
        "forwardReviewSnapshot": forward_review,
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "promotionGateOnly": True,
            "createsOrders": False,
            "changesStrategyCode": False,
            "autoTrading": False,
            "negativeSamplesAreResearchOnly": True,
        },
        "safetyNotes": [
            "策略晋级闸门只做本地研究分桶，不是交易信号。",
            "负样本库只用于复盘和过滤器训练，不会创建订单。",
            "本版本不接 API Key、不接 Trade API、不接 Withdraw API、不读取真实账户、不创建订单。",
        ],
    }
