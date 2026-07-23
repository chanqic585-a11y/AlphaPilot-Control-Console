"""Truthful matchability, forward evidence, and model-readiness projections."""

from __future__ import annotations

from typing import Any, Mapping


UNIVERSE_STAGES = (
    "requestedUniverse",
    "publicUniverse",
    "exchangeTradable",
    "eligibleUniverse",
    "componentCompatible",
    "lookbackReady",
    "dataReady",
    "evaluated",
)
SIGNAL_STAGES = (
    "rawSignals",
    "identityPassed",
    "cooldownRejected",
    "riskRejected",
    "orderEligible",
    "orders",
    "fills",
    "closedTrades",
)


def _count(value: object) -> int:
    number = int(value or 0)
    if number < 0:
        raise ValueError("matchability_stage_count_invalid")
    return number


def build_matchability_funnel(source: Mapping[str, Any]) -> dict[str, Any]:
    counts = {name: _count(source.get(name)) for name in (*UNIVERSE_STAGES, *SIGNAL_STAGES)}
    for parent, child in zip(UNIVERSE_STAGES, UNIVERSE_STAGES[1:]):
        if counts[child] > counts[parent]:
            raise ValueError("matchability_stage_count_invalid")
    if counts["identityPassed"] > counts["rawSignals"]:
        raise ValueError("matchability_stage_count_invalid")
    if counts["orderEligible"] > counts["identityPassed"]:
        raise ValueError("matchability_stage_count_invalid")
    if counts["orders"] > counts["orderEligible"]:
        raise ValueError("matchability_stage_count_invalid")
    if counts["fills"] > counts["orders"] or counts["closedTrades"] > counts["fills"]:
        raise ValueError("matchability_stage_count_invalid")

    if counts["evaluated"] < counts["dataReady"]:
        status = "evaluation_incomplete"
    elif counts["orders"] == 0:
        status = "complete_zero_order"
    elif counts["closedTrades"] < counts["fills"]:
        status = "positions_open_or_reconciliation_pending"
    else:
        status = "complete"
    return {
        "schemaVersion": "alphapilot_matchability_funnel_v1",
        **counts,
        "status": status,
        "zeroMatchIsEngineeringFailure": False,
        "executionAuthorized": False,
    }


def build_forward_task(
    *,
    task_id: str,
    release_id: str,
    release_hash: str,
    started_at: str,
    status: str,
    closed_trade_count: int,
    effective_sample_size: float,
    symbol_coverage: float,
    regime_coverage: float,
    cost_completeness: float,
) -> dict[str, Any]:
    count = max(0, int(closed_trade_count))
    if count >= 100:
        review_hint = "mature_review_available"
        next_hint = None
    elif count >= 50:
        review_hint = "expanded_review_available"
        next_hint = 100
    elif count >= 30:
        review_hint = "preliminary_review_available"
        next_hint = 50
    else:
        review_hint = "collecting"
        next_hint = 30
    blockers = []
    if cost_completeness < 1:
        blockers.append("cost_evidence_incomplete")
    if symbol_coverage <= 0:
        blockers.append("symbol_coverage_missing")
    if regime_coverage <= 0:
        blockers.append("regime_coverage_missing")
    return {
        "schemaVersion": "alphapilot_forward_task_v1",
        "taskId": task_id,
        "releaseId": release_id,
        "releaseHash": release_hash,
        "startedAt": started_at,
        "status": status,
        "closedTradeCount": count,
        "effectiveSampleSize": float(effective_sample_size),
        "symbolCoverage": float(symbol_coverage),
        "regimeCoverage": float(regime_coverage),
        "costCompleteness": float(cost_completeness),
        "reviewHint": review_hint,
        "nextReviewHintAt": next_hint,
        "blockers": blockers,
        "nextAction": "review_evidence" if review_hint != "collecting" else "continue_collecting",
        "automaticPromotionAllowed": False,
    }


def project_factor_model_readiness(source: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "factorRegistry",
        "realFactorBench",
        "trainingDataset",
        "purgedWalkForward",
        "qlibCampaign",
        "modelValidation",
        "driftMonitor",
        "rollback",
    )
    passed_values = {"completed", "passed", "ready"}
    missing = [name for name in required if str(source.get(name) or "not_run") not in passed_values]
    configured_mode = str(source.get("demoDecisionMode") or "observer_only")
    effective_mode = configured_mode if not missing and configured_mode in {"rank_only", "veto_only", "meta_label"} else "rule_only"
    live_eligible = not missing and effective_mode in {"rank_only", "veto_only", "meta_label"}
    return {
        "schemaVersion": "alphapilot_factor_model_readiness_v1",
        "status": "ready" if live_eligible else "not_ready",
        "checks": {name: str(source.get(name) or "not_run") for name in required},
        "missing": missing,
        "configuredDecisionMode": configured_mode,
        "effectiveDecisionMode": effective_mode,
        "liveEligible": live_eligible,
        "automaticModelPromotionAllowed": False,
        "riskMutationAllowed": False,
    }
