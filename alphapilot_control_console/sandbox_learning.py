from __future__ import annotations

from typing import Any

from .state_store import now_iso, save_local_sandbox_learning_snapshot


CONTROL_CONSOLE_VERSION = "V13.7.33"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_33"
MIN_BASELINE_MODEL_SAMPLES = 100


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


def build_learning_snapshot(run: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    rows = report.get("strategyHealthRows") if isinstance(report.get("strategyHealthRows"), list) else []
    closed_count = _safe_int(summary.get("totalClosedSampleCount"))
    strategy_count = _safe_int(summary.get("strategyCount"), len(rows))
    average_health = _safe_float(summary.get("averageHealthScore"))
    total_r = _safe_float(summary.get("totalR"))
    positive_rows = sum(1 for row in rows if isinstance(row, dict) and _safe_float(row.get("totalR")) > 0)
    weak_rows = sum(1 for row in rows if isinstance(row, dict) and _safe_float(row.get("healthScore")) < 50)
    readiness = "ready_for_baseline_model" if closed_count >= MIN_BASELINE_MODEL_SAMPLES else "collecting_data"
    next_action = (
        "Samples are sufficient for a simple baseline learner, but this still must not create orders."
        if readiness == "ready_for_baseline_model"
        else "Keep collecting sandbox observations before training a model; current data is still too small for reliable ML."
    )
    snapshot = {
        "snapshotId": f"local_sandbox_learning::{report.get('dateKey') or 'unknown'}::{run.get('runId') or 'manual'}",
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "createdAt": now_iso(),
        "runId": run.get("runId"),
        "reportId": report.get("reportId"),
        "strategyCount": strategy_count,
        "sampleCount": sum(_safe_int(row.get("logCount")) for row in rows if isinstance(row, dict)),
        "closedSampleCount": closed_count,
        "minimumBaselineModelSamples": MIN_BASELINE_MODEL_SAMPLES,
        "mlReadiness": readiness,
        "averageHealthScore": average_health,
        "totalR": total_r,
        "positiveStrategyCount": positive_rows,
        "weakStrategyCount": weak_rows,
        "featureFamilies": [
            "strategy_family",
            "timeframe",
            "health_score",
            "sample_count",
            "rule_match_count",
            "risk_warning_count",
            "invalidated_count",
            "total_r",
            "daily_r",
        ],
        "labelFields": [
            "outcome_r",
            "health_status",
            "next_day_health_delta",
        ],
        "nextAction": next_action,
        "safetyNote": "Learning snapshot is dataset preparation only; it is not a predictive trading model and cannot create orders.",
    }
    return save_local_sandbox_learning_snapshot(snapshot)
