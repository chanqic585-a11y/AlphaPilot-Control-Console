"""Build a truthful, versioned view of every V59 adaptive-learning gate."""

from __future__ import annotations

from typing import Any, Mapping

from .adaptive_learning_contracts import stable_hash
from .adaptive_learning_live_readiness import (
    REQUIRED_EVIDENCE,
    AdaptiveLearningLiveReadinessGate,
)


REQUIRED_CAPABILITIES = REQUIRED_EVIDENCE

_NEXT_ACTIONS = {
    "factorProductionReady": "Freeze a point-in-time production factor registry.",
    "realFactorBenchReady": "Complete a formal factor bench on registered market data.",
    "alpha101Ready": "Validate the bounded Alpha101-compatible subset on crypto data.",
    "alpha191CompatibilityReady": "Complete formula and numeric compatibility validation.",
    "validatedCryptoFactorSubsetReady": "Select factors that survive formal stability and cost gates.",
    "boundedFactorMiningReady": "Finish the preregistered bounded factor-mining budget.",
    "adaptiveMlTrainingReady": "Train and validate a decision-participating model with purged walk-forward.",
    "qlibOfflineCampaignReady": "Close Qlib data readiness and run the frozen offline campaign.",
    "modelRegistryReady": "Register a hash-bound model with a Live-eligible lifecycle.",
    "continuousLearningDatasetReady": "Freeze a lineage-complete learning dataset.",
    "demoOutcomeToTrainingSampleReady": "Record reconciled closed Demo outcomes as eligible samples.",
    "shadowInferenceReady": "Run deterministic shadow inference without changing orders.",
    "demoDecisionModeValidated": "Validate rank, veto, or meta-label behavior in Demo.",
    "modelDriftMonitoringReady": "Run and freeze model and feature drift thresholds.",
    "modelRollbackReady": "Rehearse exact champion-to-predecessor rollback.",
    "onlineInferenceLatencyReady": "Measure preloaded online inference latency.",
    "liveFeaturePipelineReady": "Prove Demo and Live feature pipeline parity.",
    "liveModelInferenceReady": "Prove deterministic Live inference with no order authority.",
    "exactModelReleaseApprovalReady": "Generate a successor Release and obtain exact user approval.",
}

_READY_STATUSES = {"completed", "passed", "ready", "validated"}


def _artifact_status(source: Mapping[str, Any] | None) -> tuple[str, bool, str | None]:
    payload = dict(source or {})
    raw_status = str(payload.get("status") or "not_run")
    ready = payload.get("passed") is True and raw_status in _READY_STATUSES
    if ready:
        status = "ready"
    elif raw_status == "not_run":
        status = "not_run"
    else:
        status = "blocked"
    evidence_ref = str(payload.get("evidenceRef") or "") or None
    return status, ready, evidence_ref


def build_adaptive_learning_readiness_snapshot(
    *,
    generated_at: str,
    model_policy: Mapping[str, Any],
    factor_registry: Mapping[str, Any],
    registry_audit: Mapping[str, Any],
    offline_evidence: Mapping[str, Any],
    artifact_evidence: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Combine immutable evidence into a fail-closed 19-capability matrix."""

    artifacts = dict(artifact_evidence or {})
    offline_flags = dict(offline_evidence.get("evidence") or {})
    alpha191 = dict(factor_registry.get("alpha191Compatibility") or {})
    alpha191_reviewed = int(alpha191.get("formulaReviewedCount") or 0)
    derived: dict[str, bool] = {
        "factorProductionReady": bool(factor_registry.get("factorRegistryHash"))
        and factor_registry.get("pointInTimeOnly") is True
        and bool(factor_registry.get("factors")),
        "realFactorBenchReady": offline_flags.get("realFactorBenchReady") is True
        and int(registry_audit.get("formalFactorRunCount") or 0) > 0,
        "alpha191CompatibilityReady": bool(alpha191.get("allFactorsProductionValidated"))
        or (
            int(alpha191.get("catalogCount") or 0) == 191
            and alpha191_reviewed > 0
            and int(alpha191.get("numericCrossvalidatedCount") or 0) >= alpha191_reviewed
        ),
        "validatedCryptoFactorSubsetReady": offline_flags.get(
            "validatedCryptoFactorSubsetReady"
        )
        is True
        and int(offline_evidence.get("eligibleFactorCount") or 0) > 0,
        "qlibOfflineCampaignReady": offline_flags.get("qlibCampaignReady") is True,
        "modelRegistryReady": int(registry_audit.get("liveEligibleModelCount") or 0) > 0,
    }

    rows: list[dict[str, Any]] = []
    evidence_flags: dict[str, bool] = {}
    for capability in REQUIRED_CAPABILITIES:
        source_status, source_ready, evidence_ref = _artifact_status(artifacts.get(capability))
        if capability in derived:
            ready = derived[capability] and (
                source_ready if capability in artifacts else True
            )
            if ready:
                status = "ready"
            elif source_status == "not_run" and capability in artifacts:
                status = "not_run"
            else:
                status = "blocked"
        else:
            ready = source_ready
            status = source_status
        evidence_flags[capability] = ready
        refs = [item for item in (
            evidence_ref,
            str(registry_audit.get("auditHash") or "") or None
            if capability in {"realFactorBenchReady", "modelRegistryReady"}
            else None,
            str(offline_evidence.get("offlineEvidenceHash") or "") or None
            if capability in {
                "realFactorBenchReady",
                "validatedCryptoFactorSubsetReady",
                "qlibOfflineCampaignReady",
            }
            else None,
        ) if item]
        rows.append(
            {
                "capability": capability,
                "status": status,
                "ready": ready,
                "evidenceRefs": refs,
                "nextAction": None if ready else _NEXT_ACTIONS[capability],
            }
        )

    gate = AdaptiveLearningLiveReadinessGate().evaluate(
        model_policy=model_policy,
        evidence=evidence_flags,
    )
    ready_count = sum(row["ready"] for row in rows)
    core = {
        "schemaVersion": "adaptive_learning_readiness_snapshot_v1",
        "readinessContractVersion": "v2",
        "status": "ready_for_exact_release_approval" if gate["passed"] else "blocked_not_ready",
        "passed": gate["passed"],
        "readyCount": ready_count,
        "totalCount": len(rows),
        "capabilities": rows,
        "evidence": evidence_flags,
        "blockers": list(gate["blockers"]),
        "modelMode": gate["modelMode"],
        "grantsLiveAuthority": False,
        "createsOrders": False,
        "changesRisk": False,
    }
    return {
        **core,
        "generatedAt": generated_at,
        "readinessHash": stable_hash(core, prefix="adaptive_readiness_snapshot"),
    }
