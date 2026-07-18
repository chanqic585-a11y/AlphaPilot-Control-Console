from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: Any, prefix: str) -> str:
    return f"{prefix}_{hashlib.sha256(canonical_bytes(value)).hexdigest()}"


def make_risk_profile() -> dict[str, Any]:
    body = {
        "schemaVersion": "strategy_validation_demo_risk_v1",
        "riskPerTradeR": 0.25,
        "maximumConcurrentPositions": 2,
        "maximumOpenRiskR": 0.5,
        "maximumSingleSymbolRiskR": 0.25,
        "maximumCorrelatedClusterRiskR": 0.5,
        "maximumDailyLossR": 1.0,
        "maximumWeeklyLossR": 2.0,
        "maximumConsecutiveLosses": 3,
        "maximumDemoDrawdownPct": 5.0,
        "minimumTargetR": 2.0,
        "stopWideningAllowed": False,
        "addingToLossAllowed": False,
        "martingaleAllowed": False,
        "automaticParameterChangeAllowed": False,
    }
    return {**body, "riskConfigHash": stable_hash(body, "demo_risk")}


def make_release(*, candidate_id: str = "candidate-1") -> dict[str, Any]:
    risk_profile = make_risk_profile()
    body = {
        "schemaVersion": "strategy_validation_release_v1",
        "campaignId": "campaign-1",
        "candidateId": candidate_id,
        "strategyId": candidate_id,
        "strategyFamilyId": "family-1",
        "marketMechanismId": "mechanism-1",
        "strategyDefinitionHash": "strategy-definition-hash",
        "externalReferenceManifestHash": "external-reference-hash",
        "dataSnapshotHash": "data-snapshot-hash",
        "factorRegistryHash": "factor-registry-hash",
        "factorShortlistHash": "factor-shortlist-hash",
        "factorDefinitionHashes": ["factor-definition-hash"],
        "factorRoles": {"factor-1": "entry_filter"},
        "preregistrationHash": "preregistration-hash",
        "costModelHash": "cost-model-hash",
        "riskConfigHash": risk_profile["riskConfigHash"],
        "riskProfile": risk_profile,
        "backtestReportHash": "backtest-report-hash",
        "formalGateHash": "formal-gate-hash",
        "releasePurpose": "strategy_forward_validation",
        "evidenceClass": "demo_strategy_validation",
        "environment": "demo",
        "approvalRequired": True,
        "approved": False,
        "immutable": True,
        "createdAt": "2026-07-16T00:00:00+00:00",
    }
    release_hash = stable_hash(body, "strategy_validation_release")
    return {
        **body,
        "releaseId": stable_hash({"releaseHash": release_hash}, "validation_release"),
        "releaseHash": release_hash,
    }


def make_exit_policy(
    *,
    mode: str = "fixed_r",
    parameters: dict[str, Any] | None = None,
    initial_stop_may_widen: bool = False,
) -> dict[str, Any]:
    if parameters is None:
        parameters = {"targetR": 1.25}
    return {
        "version": "advisory_r_exit_policy_v1",
        "mode": mode,
        "maximumHoldBars": 48,
        "initialStopMayWiden": initial_stop_may_widen,
        "parameters": parameters,
    }


def make_advisory_release(
    *,
    strategy_id: str = "advisory-candidate-1",
    exit_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = exit_policy or make_exit_policy()
    body = {
        "schemaVersion": "strategy_validation_release_v2",
        "campaignId": "advisory-campaign-1",
        "strategyId": strategy_id,
        "familyId": "event_continuation",
        "strategyDefinitionHash": "strategy-definition-hash-v2",
        "exitPolicyVersion": policy.get("version"),
        "exitPolicyMode": policy.get("mode"),
        "exitPolicyHash": stable_hash(policy, "exit_policy"),
        "canonicalExitPolicy": policy,
        "dataSnapshotHash": "data-snapshot-hash-v2",
        "preregistrationHash": "preregistration-hash-v2",
        "trialLedgerHash": "trial-ledger-hash-v2",
        "statisticalAuditHash": "statistical-audit-hash-v2",
        "walkForwardHash": "walk-forward-hash-v2",
        "lockedOosHash": "locked-oos-hash-v2",
        "costModelHash": "cost-model-hash-v2",
        "riskConfigHash": "risk-config-hash-v2",
        "formalGateHash": "formal-gate-hash-v2",
        "environment": "demo",
        "approvalRequired": True,
        "approved": False,
        "liveEligible": False,
    }
    release_hash = stable_hash(body, "strategy_validation_release")
    return {
        **body,
        "releaseId": stable_hash({"releaseHash": release_hash}, "validation_release"),
        "releaseHash": release_hash,
    }
