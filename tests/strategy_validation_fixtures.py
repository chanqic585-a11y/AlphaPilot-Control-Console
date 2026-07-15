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
