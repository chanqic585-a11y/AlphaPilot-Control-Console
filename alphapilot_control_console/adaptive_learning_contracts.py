"""Immutable contracts shared by Demo and Live adaptive-learning adapters."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


MODEL_MODES = frozenset({"observer", "rank_only", "veto_only", "meta_label", "risk_suggestion"})
LIVE_DECISION_MODES = frozenset({"rank_only", "veto_only", "meta_label"})
MODEL_LIFECYCLE_STATUSES = frozenset(
    {"draft", "shadow_candidate", "shadow_approved", "challenger", "champion", "archived"}
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def stable_hash(value: Any, *, prefix: str) -> str:
    return f"{prefix}_{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def build_feature_schema(factor_registry: Mapping[str, Any]) -> dict[str, Any]:
    rows = factor_registry.get("factors") if isinstance(factor_registry.get("factors"), list) else []
    features = [
        {
            "factorId": str(row["factorId"]),
            "dtype": "float64",
            "availableAtRule": str(row["availableAtRule"]),
            "missingValuePolicy": str(row["missingValuePolicy"]),
            "definitionHash": str(row["definitionHash"]),
            "implementationHash": str(row["implementationHash"]),
        }
        for row in rows
        if isinstance(row, dict) and row.get("pointInTimeReady") is True
    ]
    features.sort(key=lambda row: row["factorId"])
    core = {
        "schemaVersion": "production_feature_schema_v1",
        "factorRegistryHash": str(factor_registry.get("factorRegistryHash") or ""),
        "features": features,
        "featureNames": [row["factorId"] for row in features],
        "pointInTimeOnly": True,
    }
    return {**core, "featureSchemaHash": stable_hash(core, prefix="feature_schema")}


def build_model_policy(
    *,
    model_hash: str,
    feature_schema_hash: str,
    factor_registry_hash: str,
    model_mode: str,
    thresholds: Mapping[str, Any],
    lifecycle_status: str,
) -> dict[str, Any]:
    if model_mode not in MODEL_MODES:
        raise ValueError(f"Unsupported adaptive model mode: {model_mode}")
    if lifecycle_status not in MODEL_LIFECYCLE_STATUSES:
        raise ValueError(f"Unsupported model lifecycle status: {lifecycle_status}")
    required = (model_hash, feature_schema_hash, factor_registry_hash)
    if any(not str(value).strip() for value in required):
        raise ValueError("Model policy hash bindings must not be empty")
    core = {
        "schemaVersion": "adaptive_model_policy_v1",
        "modelHash": str(model_hash),
        "featureSchemaHash": str(feature_schema_hash),
        "factorRegistryHash": str(factor_registry_hash),
        "modelMode": model_mode,
        "thresholds": dict(thresholds),
        "lifecycleStatus": lifecycle_status,
        "selfApprovalAllowed": False,
        "automaticRiskIncreaseAllowed": False,
        "strategySourceMutationAllowed": False,
    }
    return {**core, "modelPolicyHash": stable_hash(core, prefix="model_policy")}


def build_observer_model_registry(feature_schema: Mapping[str, Any]) -> dict[str, Any]:
    artifact_core = {
        "schemaVersion": "adaptive_observer_model_v1",
        "algorithm": "deterministic_neutral_observer",
        "featureNames": list(feature_schema.get("featureNames") or []),
        "parameters": {"constantProbability": 0.5},
        "trainingStatus": "not_run",
        "decisionAuthority": "none",
        "createsOrders": False,
        "changesRisk": False,
    }
    model_hash = stable_hash(artifact_core, prefix="model")
    policy = build_model_policy(
        model_hash=model_hash,
        feature_schema_hash=str(feature_schema.get("featureSchemaHash") or ""),
        factor_registry_hash=str(feature_schema.get("factorRegistryHash") or ""),
        model_mode="observer",
        thresholds={"observationThreshold": 0.5},
        lifecycle_status="shadow_approved",
    )
    core = {
        "schemaVersion": "adaptive_model_registry_v1",
        "models": [
            {
                **artifact_core,
                "modelHash": model_hash,
                "status": "shadow_approved",
                "productionLiveEligible": False,
            }
        ],
        "activeDemoModelHash": model_hash,
        "activeDemoModelPolicy": policy,
        "activeLiveModelHash": None,
        "activeLiveModelPolicy": None,
    }
    return {**core, "modelRegistryHash": stable_hash(core, prefix="model_registry")}


def build_observer_sidecar_binding(
    *, release_id: str, release_hash: str, model_policy: Mapping[str, Any]
) -> dict[str, Any]:
    if model_policy.get("modelMode") != "observer":
        raise PermissionError("Only observer mode can bind without a successor release")
    core = {
        "schemaVersion": "adaptive_observer_sidecar_binding_v1",
        "releaseId": str(release_id),
        "releaseHash": str(release_hash),
        "modelHash": str(model_policy.get("modelHash") or ""),
        "modelPolicyHash": str(model_policy.get("modelPolicyHash") or ""),
        "altersOrderSemantics": False,
        "createsOrders": False,
        "changesRisk": False,
    }
    return {**core, "sidecarBindingHash": stable_hash(core, prefix="observer_sidecar")}


def build_successor_release_identity(
    *, release_id: str, release_hash: str, model_policy: Mapping[str, Any]
) -> dict[str, Any]:
    if model_policy.get("modelMode") == "observer":
        raise ValueError("Observer mode does not need a decision-changing successor release")
    core = {
        "schemaVersion": "adaptive_successor_release_identity_v1",
        "supersedesReleaseId": str(release_id),
        "supersedesReleaseHash": str(release_hash),
        "modelHash": str(model_policy.get("modelHash") or ""),
        "modelPolicyHash": str(model_policy.get("modelPolicyHash") or ""),
        "modelMode": str(model_policy.get("modelMode") or ""),
        "requiresExactHumanApproval": True,
        "approved": False,
        "armed": False,
    }
    content_hash = stable_hash(core, prefix="adaptive_release")
    return {
        **core,
        "releaseId": "adaptive_successor_" + content_hash.rsplit("_", 1)[-1][:24],
        "releaseHash": content_hash,
    }
