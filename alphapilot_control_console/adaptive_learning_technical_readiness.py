"""Technical-only readiness gate for adaptive learning in Live releases."""

from __future__ import annotations

from typing import Any, Mapping

from .adaptive_learning_contracts import LIVE_DECISION_MODES


REQUIRED_TECHNICAL_EVIDENCE = (
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
    "modelReleaseBindingReady",
)


def _all_true(evidence: Mapping[str, Any], *keys: str) -> bool:
    return all(evidence.get(key) is True for key in keys)


def resolve_technical_evidence(evidence: Mapping[str, Any]) -> dict[str, bool]:
    """Resolve compatible technical names without reading human approval."""

    resolved = {
        key: evidence.get(key) is True
        for key in REQUIRED_TECHNICAL_EVIDENCE
    }
    resolved["factorProductionReady"] |= (
        evidence.get("productionFactorRegistryReady") is True
    )
    resolved["qlibOfflineCampaignReady"] |= evidence.get("qlibCampaignReady") is True
    resolved["adaptiveMlTrainingReady"] |= _all_true(
        evidence,
        "trainingDatasetReady",
        "purgedWalkForwardReady",
        "modelValidationReady",
    )
    resolved["modelRegistryReady"] |= _all_true(
        evidence,
        "modelArtifactFresh",
        "modelHashVerified",
    )
    resolved["modelDriftMonitoringReady"] |= evidence.get("driftWithinLimits") is True
    resolved["modelRollbackReady"] |= evidence.get("rollbackReady") is True
    resolved["liveFeaturePipelineReady"] |= (
        evidence.get("featurePipelineParityReady") is True
    )
    resolved["modelReleaseBindingReady"] |= _all_true(
        evidence,
        "modelHashVerified",
        "releaseHashBindsModelPolicy",
        "riskOverlayVerified",
    )
    return resolved


class AdaptiveLearningTechnicalReadinessGate:
    """Evaluate technical evidence without evaluating or requiring approval."""

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
        for key in (
            "modelHash",
            "modelPolicyHash",
            "featureSchemaHash",
            "factorRegistryHash",
        ):
            if not str(model_policy.get(key) or ""):
                blockers.append(f"model_policy_missing_{key}")
        if model_policy.get("lifecycleStatus") not in {
            "shadow_approved",
            "challenger",
            "champion",
        }:
            blockers.append("model_lifecycle_not_live_eligible")
        evidence_status = resolve_technical_evidence(evidence)
        blockers.extend(
            f"adaptive_evidence_not_ready:{key}"
            for key in REQUIRED_TECHNICAL_EVIDENCE
            if not evidence_status[key]
        )
        return {
            "schemaVersion": "adaptive_learning_technical_readiness_v1",
            "readinessContractVersion": "v3",
            "passed": not blockers,
            "modelMode": mode,
            "evidenceStatus": evidence_status,
            "blockers": blockers,
            "createsOrders": False,
            "changesRisk": False,
            "exactApprovalEvaluated": False,
            "exactApprovalRequiredAfterTechnicalReadiness": True,
        }
