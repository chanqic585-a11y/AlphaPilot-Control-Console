"""Fail-closed readiness gate for adaptive learning in Live releases."""

from __future__ import annotations

from typing import Any, Mapping

from .adaptive_learning_contracts import LIVE_DECISION_MODES


_REQUIRED_EVIDENCE = (
    "productionFactorRegistryReady",
    "realFactorBenchReady",
    "alpha191CompatibilityReady",
    "validatedCryptoFactorSubsetReady",
    "trainingDatasetReady",
    "purgedWalkForwardReady",
    "modelValidationReady",
    "qlibCampaignReady",
    "featurePipelineParityReady",
    "driftWithinLimits",
    "rollbackReady",
    "modelArtifactFresh",
    "modelHashVerified",
    "releaseHashBindsModelPolicy",
    "exactHumanApproval",
    "riskOverlayVerified",
)


class AdaptiveLearningLiveReadinessGate:
    def evaluate(
        self,
        *,
        model_policy: Mapping[str, Any],
        evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        blockers: list[str] = []
        mode = str(model_policy.get("modelMode") or "")
        if mode not in LIVE_DECISION_MODES:
            blockers.append("live_model_mode_not_decision_participating")
        for key in ("modelHash", "modelPolicyHash", "featureSchemaHash", "factorRegistryHash"):
            if not str(model_policy.get(key) or ""):
                blockers.append(f"model_policy_missing_{key}")
        if model_policy.get("lifecycleStatus") not in {"shadow_approved", "challenger", "champion"}:
            blockers.append("model_lifecycle_not_live_eligible")
        blockers.extend(
            f"adaptive_evidence_not_ready:{key}"
            for key in _REQUIRED_EVIDENCE
            if evidence.get(key) is not True
        )
        return {
            "schemaVersion": "adaptive_learning_live_readiness_v1",
            "passed": not blockers,
            "modelMode": mode,
            "blockers": blockers,
            "createsOrders": False,
            "changesRisk": False,
            "exactApprovalRequired": True,
        }
