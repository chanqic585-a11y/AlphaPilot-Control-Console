"""Fail-closed readiness gate for adaptive learning in Live releases."""

from __future__ import annotations

from typing import Any, Mapping

from .adaptive_learning_contracts import LIVE_DECISION_MODES


REQUIRED_EVIDENCE = (
    "factorProductionReady",
    "realFactorBenchReady",
    "alpha101Ready",
    "alpha191CompatibilityReady",
    "validatedCryptoFactorSubsetReady",
    "boundedFactorMiningReady",
    "adaptiveMlTrainingReady",
    "qlibOfflineCampaignReady",
    "modelRegistryReady",
    "continuousLearningDatasetReady",
    "demoOutcomeToTrainingSampleReady",
    "shadowInferenceReady",
    "demoDecisionModeValidated",
    "modelDriftMonitoringReady",
    "modelRollbackReady",
    "onlineInferenceLatencyReady",
    "liveFeaturePipelineReady",
    "liveModelInferenceReady",
    "exactModelReleaseApprovalReady",
)

# Backward-compatible private alias for callers that imported the original name.
_REQUIRED_EVIDENCE = REQUIRED_EVIDENCE


def _all_true(evidence: Mapping[str, Any], *keys: str) -> bool:
    return all(evidence.get(key) is True for key in keys)


def _resolved_evidence(evidence: Mapping[str, Any]) -> dict[str, bool]:
    """Resolve renamed V55 fields without treating them as new V59 capabilities."""

    explicit = {key: evidence.get(key) is True for key in _REQUIRED_EVIDENCE}
    explicit["factorProductionReady"] |= evidence.get("productionFactorRegistryReady") is True
    explicit["qlibOfflineCampaignReady"] |= evidence.get("qlibCampaignReady") is True
    explicit["adaptiveMlTrainingReady"] |= _all_true(
        evidence,
        "trainingDatasetReady",
        "purgedWalkForwardReady",
        "modelValidationReady",
    )
    explicit["modelRegistryReady"] |= _all_true(
        evidence,
        "modelArtifactFresh",
        "modelHashVerified",
    )
    explicit["modelDriftMonitoringReady"] |= evidence.get("driftWithinLimits") is True
    explicit["modelRollbackReady"] |= evidence.get("rollbackReady") is True
    explicit["liveFeaturePipelineReady"] |= evidence.get("featurePipelineParityReady") is True
    explicit["exactModelReleaseApprovalReady"] |= _all_true(
        evidence,
        "modelHashVerified",
        "releaseHashBindsModelPolicy",
        "exactHumanApproval",
        "riskOverlayVerified",
    )
    return explicit


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
        evidence_status = _resolved_evidence(evidence)
        blockers.extend(
            f"adaptive_evidence_not_ready:{key}"
            for key in _REQUIRED_EVIDENCE
            if not evidence_status[key]
        )
        return {
            "schemaVersion": "adaptive_learning_live_readiness_v1",
            "readinessContractVersion": "v2",
            "passed": not blockers,
            "modelMode": mode,
            "evidenceStatus": evidence_status,
            "blockers": blockers,
            "createsOrders": False,
            "changesRisk": False,
            "exactApprovalRequired": True,
        }
