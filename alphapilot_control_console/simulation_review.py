from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .config import SAFETY_BOUNDARY
from .local_sandbox_runner import VIRTUAL_CAPITAL_PER_STRATEGY
from .sandbox_auto_runner import get_local_sandbox_auto_runner_status
from .state_store import list_local_sandbox_daily_reports, list_paper_observation_logs
from .usable_strategy_catalog import build_usable_strategy_catalog


CONTROL_CONSOLE_VERSION = "V13.7.46"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_46"

MIN_REVIEW_CLOSED_SAMPLES = 30
MIN_DRY_RUN_CLOSED_SAMPLES = 100
MIN_STABLE_CLOSED_SAMPLES = 300
MIN_PROMOTION_PROFIT_FACTOR = 1.05
MIN_DRY_RUN_PROFIT_FACTOR = 1.15
MAX_CONCENTRATION_SHARE = 0.70
MAX_REVIEW_DRAWDOWN_R = 10.0


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


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _extract_outcome_r(row: dict[str, Any]) -> float | None:
    if row.get("outcomeR") is not None:
        return _safe_float(row.get("outcomeR"))
    text = str(row.get("outcome") or "").strip().upper().replace(" ", "")
    if not text.endswith("R"):
        return None
    return _safe_float(text[:-1])


def _latest_daily_report() -> dict[str, Any]:
    reports = list_local_sandbox_daily_reports(1)
    return reports[0] if reports and isinstance(reports[0], dict) else {}


def _health_rows_by_task(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = report.get("strategyHealthRows") if isinstance(report.get("strategyHealthRows"), list) else []
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("taskId") or "").strip()
        if task_id:
            result[task_id] = row
    return result


def _strategy_task_id(item: dict[str, Any]) -> str:
    return str(
        item.get("taskId")
        or item.get("catalogId")
        or item.get("candidateId")
        or item.get("strategyId")
        or ""
    ).strip()


def _group_breakdown(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"sampleCount": 0})
    for row in rows:
        name = str(row.get(key) or "unknown")
        outcome_r = _extract_outcome_r(row)
        if outcome_r is None:
            continue
        grouped[name]["sampleCount"] += 1
    result = []
    for name, payload in grouped.items():
        sample_count = payload["sampleCount"]
        result.append({
            key: name,
            "sampleCount": sample_count,
            "sampleShare": round(sample_count / max(1, len(rows)), 4),
            "dataQuality": "raw_recent_log_distribution",
        })
    result.sort(key=lambda row: (-row["sampleCount"], str(row.get(key))))
    return result


def _max_consecutive_losses(values: list[float]) -> int:
    max_streak = 0
    current = 0
    for value in values:
        if value < 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _max_drawdown_r(values: list[float]) -> float:
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)
    return round(max_drawdown, 4)


def _concentration_warning(pair_breakdown: list[dict[str, Any]], total_closed: int) -> bool:
    if not pair_breakdown or total_closed <= 0:
        return False
    top_share = _safe_float(pair_breakdown[0].get("sampleShare"))
    return top_share >= MAX_CONCENTRATION_SHARE and total_closed >= 10


def _inactive_warning(latest_log_at: Any) -> bool:
    parsed = _parse_time(latest_log_at)
    if not parsed:
        return True
    return (datetime.now(timezone.utc) - parsed).days >= 7


def _build_review_row(item: dict[str, Any], health: dict[str, Any]) -> dict[str, Any]:
    task_id = _strategy_task_id(item)
    raw_logs = list_paper_observation_logs(task_id)
    logs = raw_logs if isinstance(raw_logs, list) else []
    closed_logs = [row for row in logs if isinstance(row, dict) and _extract_outcome_r(row) is not None]
    health_closed_count = _safe_int(health.get("closedPaperSampleCount"))
    total_closed = health_closed_count or len(closed_logs)
    review_logs = closed_logs[-total_closed:] if total_closed and total_closed < len(closed_logs) else closed_logs
    outcomes = [_extract_outcome_r(row) or 0.0 for row in review_logs]
    health_win_count = _safe_int(health.get("winCount"))
    health_loss_count = _safe_int(health.get("lossCount"))
    wins = [value for value in outcomes if value > 0]
    losses = [value for value in outcomes if value < 0]
    win_count = health_win_count if health_win_count or health_loss_count else len(wins)
    loss_count = health_loss_count if health_win_count or health_loss_count else len(losses)
    total_r = round(_safe_float(health.get("totalR"), sum(outcomes)), 4)
    # The local sandbox currently records fixed R outcomes. Use deduped daily
    # health counts for gates and derive coarse PF only when loss samples exist.
    gross_loss_r = float(loss_count)
    gross_profit_r = max(total_r + gross_loss_r, 0.0) if (win_count or loss_count) else sum(wins)
    profit_factor = round(gross_profit_r / gross_loss_r, 4) if gross_loss_r > 0 else None
    win_rate = round(win_count / total_closed * 100, 2) if total_closed else None
    average_win_r = round(gross_profit_r / win_count, 4) if win_count else None
    average_loss_r = round(gross_loss_r / loss_count, 4) if loss_count else None
    max_consecutive_losses = _max_consecutive_losses(outcomes)
    max_drawdown_r = _max_drawdown_r(outcomes)
    pair_breakdown = _group_breakdown(review_logs, "pair")
    direction_breakdown = _group_breakdown(review_logs, "direction")
    market_regime_breakdown = _group_breakdown(review_logs, "marketRegime")
    risk_warning_count = sum(1 for row in logs if isinstance(row, dict) and row.get("logType") == "risk_warning")
    invalidated_count = sum(1 for row in logs if isinstance(row, dict) and row.get("logType") == "invalidated")
    latest_log_at = health.get("latestLogAt") or (review_logs[-1].get("createdAt") if review_logs else None)

    warnings: list[str] = []
    if total_closed < MIN_REVIEW_CLOSED_SAMPLES:
        warnings.append("sample_size_below_review_threshold")
    if max_consecutive_losses >= 3:
        warnings.append("loss_streak_warning")
    if total_closed >= MIN_REVIEW_CLOSED_SAMPLES and profit_factor is not None and profit_factor < 0.8:
        warnings.append("demotion_review")
    if _concentration_warning(pair_breakdown, total_closed):
        warnings.append("concentration_risk")
    if _inactive_warning(latest_log_at):
        warnings.append("inactive_warning")
    if invalidated_count > 0:
        warnings.append("invalidated_samples_need_review")
    if risk_warning_count > 0:
        warnings.append("risk_warning_needs_review")

    sample_status = (
        "stable_sample_ready" if total_closed >= MIN_STABLE_CLOSED_SAMPLES
        else "dry_run_sample_ready" if total_closed >= MIN_DRY_RUN_CLOSED_SAMPLES
        else "review_sample_ready" if total_closed >= MIN_REVIEW_CLOSED_SAMPLES
        else "collecting_samples"
    )

    status = "collecting_samples"
    action = "继续收集样本"
    if total_closed >= MIN_REVIEW_CLOSED_SAMPLES:
        status = "under_review"
        action = "进入人工复核"
    if (
        total_closed >= MIN_REVIEW_CLOSED_SAMPLES
        and profit_factor is not None
        and profit_factor >= MIN_PROMOTION_PROFIT_FACTOR
        and max_drawdown_r <= MAX_REVIEW_DRAWDOWN_R
        and "concentration_risk" not in warnings
        and risk_warning_count == 0
        and invalidated_count == 0
    ):
        status = "promoted_candidate"
        action = "可列入晋级候选，继续人工复核"
    if total_closed >= MIN_REVIEW_CLOSED_SAMPLES and profit_factor is not None and profit_factor < 0.8:
        status = "demoted"
        action = "降级为参考或暂停观察"
    if risk_warning_count > 0 or invalidated_count > 0:
        status = "watchlist" if status == "promoted_candidate" else status
        action = "先复核风险或失效样本"

    strategy_name = item.get("name") or item.get("shortName") or item.get("strategyId") or task_id
    health_score = _safe_float(health.get("healthScore"))
    virtual_capital = _safe_float(health.get("virtualCapital"), VIRTUAL_CAPITAL_PER_STRATEGY)
    virtual_equity = _safe_float(
        health.get("virtualEquity"),
        virtual_capital + (total_r * virtual_capital * 0.01),
    )
    return {
        "strategyId": item.get("strategyId") or item.get("candidateId") or task_id,
        "taskId": task_id,
        "strategyName": strategy_name,
        "timeframe": item.get("timeframe") or health.get("timeframe"),
        "frequencyLabel": item.get("frequencyLabel"),
        "status": status,
        "statusLabel": {
            "collecting_samples": "样本收集中",
            "under_review": "进入复核",
            "promoted_candidate": "晋级候选",
            "watchlist": "观察名单",
            "demoted": "降级",
            "archived_reference": "归档参考",
        }.get(status, status),
        "recommendedAction": action,
        "sampleStatus": sample_status,
        "sampleGate": {
            "closedSamples": total_closed,
            "reviewMinimum": MIN_REVIEW_CLOSED_SAMPLES,
            "dryRunMinimum": MIN_DRY_RUN_CLOSED_SAMPLES,
            "stableMinimum": MIN_STABLE_CLOSED_SAMPLES,
            "isReviewReady": total_closed >= MIN_REVIEW_CLOSED_SAMPLES,
            "isDryRunSampleReady": total_closed >= MIN_DRY_RUN_CLOSED_SAMPLES,
        },
        "metrics": {
            "closedSamples": total_closed,
            "logCount": len(logs),
            "ruleMatchedCount": _safe_int(
                health.get("ruleMatchedCount"),
                sum(1 for row in logs if isinstance(row, dict) and row.get("ruleMatched")),
            ),
            "riskWarningCount": risk_warning_count,
            "invalidatedCount": invalidated_count,
            "virtualCapital": round(virtual_capital, 2),
            "virtualEquity": round(virtual_equity, 2),
            "virtualPnl": round(virtual_equity - virtual_capital, 2),
            "totalR": total_r,
            "winRate": win_rate,
            "profitFactor": profit_factor,
            "averageWinR": average_win_r,
            "averageLossR": average_loss_r,
            "maxConsecutiveLosses": max_consecutive_losses,
            "maxDrawdownR": max_drawdown_r,
            "healthScore": health_score,
        },
        "breakdowns": {
            "byPair": pair_breakdown,
            "byDirection": direction_breakdown,
            "byMarketRegime": market_regime_breakdown,
        },
        "costAndSlippage": {
            "feeEstimateAvailable": False,
            "slippageEstimateAvailable": False,
            "note": "Current local sandbox samples do not carry full fee or slippage estimates. This row is a review prompt, not a trading approval.",
        },
        "warnings": warnings,
        "latestLogAt": latest_log_at,
        "safetyNote": "Simulation review is local research only. It does not approve testnet, live trading, API keys, or orders.",
    }


def build_simulation_review() -> dict[str, Any]:
    catalog = build_usable_strategy_catalog()
    latest_report = _latest_daily_report()
    health_map = _health_rows_by_task(latest_report)
    strategies = catalog.get("strategies") if isinstance(catalog.get("strategies"), list) else []
    rows = [
        _build_review_row(item, health_map.get(_strategy_task_id(item), {}))
        for item in strategies
        if isinstance(item, dict) and _strategy_task_id(item)
    ]
    rows.sort(
        key=lambda row: (
            row.get("status") != "promoted_candidate",
            row.get("status") != "under_review",
            -_safe_int(row.get("metrics", {}).get("closedSamples")),
            -_safe_float(row.get("metrics", {}).get("profitFactor"), -1),
        )
    )
    summary = {
        "totalStrategies": len(rows),
        "totalClosedSamples": sum(_safe_int(row.get("metrics", {}).get("closedSamples")) for row in rows),
        "collectingStrategies": sum(1 for row in rows if row.get("status") == "collecting_samples"),
        "reviewReadyStrategies": sum(1 for row in rows if row.get("sampleGate", {}).get("isReviewReady")),
        "promotedCandidates": sum(1 for row in rows if row.get("status") == "promoted_candidate"),
        "demotedStrategies": sum(1 for row in rows if row.get("status") == "demoted"),
        "watchlistStrategies": sum(1 for row in rows if row.get("status") == "watchlist"),
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "reviewMinimumClosedSamples": MIN_REVIEW_CLOSED_SAMPLES,
        "dryRunMinimumClosedSamples": MIN_DRY_RUN_CLOSED_SAMPLES,
        "nextAction": "继续让本地沙盒运行，并优先把每条策略补到 30 个闭合样本。"
    }
    runner_payload = get_local_sandbox_auto_runner_status()
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "summary": summary,
        "queue": rows,
        "thresholds": {
            "reviewClosedSamples": MIN_REVIEW_CLOSED_SAMPLES,
            "dryRunClosedSamples": MIN_DRY_RUN_CLOSED_SAMPLES,
            "stableClosedSamples": MIN_STABLE_CLOSED_SAMPLES,
            "promotionProfitFactor": MIN_PROMOTION_PROFIT_FACTOR,
            "dryRunProfitFactor": MIN_DRY_RUN_PROFIT_FACTOR,
            "maxConcentrationShare": MAX_CONCENTRATION_SHARE,
        },
        "autoRunner": runner_payload.get("autoRunner") if isinstance(runner_payload.get("autoRunner"), dict) else {},
        "latestDailyReportId": latest_report.get("reportId"),
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "This endpoint ranks local simulation samples for human review only. It does not connect exchange APIs or create orders.",
    }


def build_simulation_review_strategy(strategy_id: str) -> dict[str, Any] | None:
    payload = build_simulation_review()
    wanted = str(strategy_id or "").strip()
    for row in payload.get("queue", []):
        if not isinstance(row, dict):
            continue
        if wanted in {str(row.get("taskId")), str(row.get("strategyId"))}:
            return {
                "version": payload["version"],
                "source": payload["source"],
                "strategy": row,
                "thresholds": payload["thresholds"],
                "dryRunApproved": False,
                "liveTradingApproved": False,
                "safetyBoundary": SAFETY_BOUNDARY,
            }
    return None
