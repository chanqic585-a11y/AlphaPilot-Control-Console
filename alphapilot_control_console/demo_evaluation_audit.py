from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def _rows(value: object) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _bounded_counts(counter: Counter[str], limit: int = 10) -> dict[str, int]:
    return {
        key: int(count)
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    }


def _failed_rule_ids(rejection: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    for rule in _rows(rejection.get("rules")):
        if rule.get("matched") is not False:
            continue
        rule_id = str(rule.get("checkId") or rule.get("factorId") or "unknown_check")
        if rule_id and rule_id not in failed:
            failed.append(rule_id)
    return failed


def build_demo_evaluation_audit(
    batch: dict[str, Any],
    *,
    releases: Iterable[Any],
) -> dict[str, Any]:
    release_rows = list(releases)
    scans = batch.get("scans") if isinstance(batch.get("scans"), dict) else {}
    rejection_counts: Counter[str] = Counter()
    failed_check_counts: Counter[str] = Counter()
    near_misses: list[dict[str, Any]] = []
    release_audits: list[dict[str, Any]] = []
    market_totals: list[int] = []
    liquidity_totals: list[int] = []
    deep_screen_count = 0

    for release in release_rows:
        release_id = str(getattr(release, "releaseId", "") or "")
        strategy_id = str(getattr(release, "strategyId", "") or "")
        timeframe = str(getattr(release, "timeframe", "") or "")
        scan = scans.get(release_id) if isinstance(scans.get(release_id), dict) else {}
        universe = scan.get("universe") if isinstance(scan.get("universe"), dict) else {}
        progress = scan.get("progress") if isinstance(scan.get("progress"), dict) else {}
        total = int(universe.get("totalInstrumentCount") or 0)
        liquidity = int(universe.get("liquidityEligibleCount") or 0)
        completed = int(progress.get("completed") or 0)
        required = int(progress.get("required") or universe.get("screeningPoolCount") or 0)
        market_totals.append(total)
        liquidity_totals.append(liquidity)
        deep_screen_count += completed
        release_rejections = _rows(scan.get("rejections"))
        for rejection in release_rejections:
            reason = str(rejection.get("reason") or "unknown")
            rejection_counts[reason] += 1
            failed = _failed_rule_ids(rejection)
            failed_check_counts.update(failed)
            if reason == "frozen_rules_not_matched" and failed:
                near_misses.append({
                    "releaseId": release_id,
                    "strategyId": strategy_id,
                    "instId": str(rejection.get("instId") or ""),
                    "failedCheckCount": len(failed),
                    "failedChecks": failed[:6],
                })
        release_audits.append({
            "releaseId": release_id,
            "strategyId": strategy_id,
            "timeframe": timeframe,
            "marketInstrumentCount": total,
            "liquidityEligibleCount": liquidity,
            "deepScreenCompleted": completed,
            "deepScreenRequired": required,
            "matchedSignalCount": len(_rows(scan.get("signals"))),
            "rejectionReasonCounts": _bounded_counts(Counter(
                str(row.get("reason") or "unknown") for row in release_rejections
            )),
        })

    execution_rejections = _rows(batch.get("rejectedSignals"))
    execution_rejection_counts = Counter(
        str(row.get("reason") or "unknown") for row in execution_rejections
    )
    matched = int(batch.get("matchedSignalCount") or 0)
    created = int(batch.get("createdOrderCount") or 0)
    outcomes = _rows(batch.get("orderOutcomes"))
    attempts = int(batch.get("orderAttemptCount") or len(outcomes))
    exchange_codes = Counter(
        str(row.get("exchangeCode"))
        for row in outcomes
        if row.get("exchangeCode") is not None and str(row.get("exchangeCode"))
    )
    if created:
        state = "order_submitted"
    elif matched:
        state = "matched_rejected"
    else:
        state = "evaluated_zero_matches"

    latency = batch.get("latencyMetrics") if isinstance(batch.get("latencyMetrics"), dict) else {}
    durations = latency.get("stageDurationsMs") if isinstance(latency.get("stageDurationsMs"), dict) else {}
    safe_durations = {
        str(key): value
        for key, value in durations.items()
        if isinstance(value, (int, float))
    }
    near_misses.sort(key=lambda row: (row["failedCheckCount"], row["releaseId"], row["instId"]))
    return {
        "state": state,
        "evaluatedReleaseCount": len(release_rows),
        "matchedSignalCount": matched,
        "createdOrderCount": created,
        "orderAttemptCount": attempts,
        "marketSummary": {
            "totalInstrumentCount": max(market_totals, default=0),
            "liquidityEligibleCount": max(liquidity_totals, default=0),
            "deepScreenCount": deep_screen_count,
        },
        "rejectionReasonCounts": _bounded_counts(rejection_counts),
        "failedCheckCounts": _bounded_counts(failed_check_counts),
        "executionRejectionReasonCounts": _bounded_counts(execution_rejection_counts),
        "exchangeCodeCounts": _bounded_counts(exchange_codes),
        "nearMisses": near_misses[:5],
        "releaseAudits": release_audits,
        "stageDurationsMs": safe_durations,
    }
