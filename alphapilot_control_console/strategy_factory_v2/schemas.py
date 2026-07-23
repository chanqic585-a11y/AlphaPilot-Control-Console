from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import StrategyFactoryV2Error


STATES = (
    "hypothesis_draft",
    "hypothesis_validated",
    "data_readiness",
    "candidate_build",
    "trial_queued",
    "trial_running",
    "development_complete",
    "formal_queued",
    "formal_running",
    "formal_complete",
    "demo_release_draft",
    "archived",
    "blocked",
)

FAILURE_LAYERS = (
    "Implementation",
    "Data / PIT",
    "Signal Edge",
    "Cost / Capacity",
    "Stability / Regime",
    "Risk / Portfolio",
    "Promotion / Execution",
)

_HYPOTHESIS_REQUIRED = (
    "hypothesisId",
    "familyId",
    "familyFingerprint",
    "mechanism",
    "falsifiableHypothesis",
    "invalidationConditions",
    "timeframe",
    "direction",
    "requiredData",
    "exitPolicy",
)

_FAILURE_REQUIRED = (
    "failureLayer",
    "facts",
    "inferences",
    "repairability",
    "prohibitedRepair",
    "nextExperiment",
    "changedVariable",
    "parentStrategy",
    "familyFingerprint",
    "signalCorrelation",
)


def _require_nonempty_text(payload: Mapping[str, Any], field: str) -> None:
    if not str(payload.get(field) or "").strip():
        raise StrategyFactoryV2Error(f"{field}_required")


def validate_hypothesis(payload: Mapping[str, Any]) -> dict[str, Any]:
    for field in _HYPOTHESIS_REQUIRED:
        if field not in payload:
            raise StrategyFactoryV2Error(f"hypothesis_{field}_required")
    for field in (
        "hypothesisId",
        "familyId",
        "familyFingerprint",
        "mechanism",
        "falsifiableHypothesis",
        "timeframe",
        "direction",
    ):
        _require_nonempty_text(payload, field)
    if not isinstance(payload.get("invalidationConditions"), list) or not payload[
        "invalidationConditions"
    ]:
        raise StrategyFactoryV2Error("hypothesis_invalidation_conditions_required")
    if not isinstance(payload.get("requiredData"), list) or not payload["requiredData"]:
        raise StrategyFactoryV2Error("hypothesis_required_data_missing")
    exit_policy = payload.get("exitPolicy")
    if not isinstance(exit_policy, Mapping) or not str(
        exit_policy.get("policyId") or ""
    ).strip():
        raise StrategyFactoryV2Error("hypothesis_versioned_exit_policy_required")
    return dict(payload)


def validate_experiment(payload: Mapping[str, Any]) -> dict[str, Any]:
    for field in (
        "experimentId",
        "candidateId",
        "parentStrategyId",
        "changedVariable",
    ):
        _require_nonempty_text(payload, field)
    changed_variables = payload.get("changedVariables")
    if changed_variables is not None:
        if not isinstance(changed_variables, list) or len(changed_variables) != 1:
            raise StrategyFactoryV2Error("one_variable_at_a_time_required")
        if str(changed_variables[0]) != str(payload["changedVariable"]):
            raise StrategyFactoryV2Error("one_variable_at_a_time_mismatch")
    if bool(payload.get("lockedOosRead")):
        raise StrategyFactoryV2Error("locked_oos_tuning_forbidden")
    if bool(payload.get("gateRelaxation")):
        raise StrategyFactoryV2Error("post_result_gate_relaxation_forbidden")
    return dict(payload)


def validate_failure(payload: Mapping[str, Any]) -> dict[str, Any]:
    for field in _FAILURE_REQUIRED:
        if field not in payload:
            raise StrategyFactoryV2Error(f"failure_{field}_required")
    if payload.get("failureLayer") not in FAILURE_LAYERS:
        raise StrategyFactoryV2Error("failure_layer_invalid")
    for field in ("facts", "inferences", "prohibitedRepair"):
        if not isinstance(payload.get(field), list):
            raise StrategyFactoryV2Error(f"failure_{field}_invalid")
    if not payload["facts"]:
        raise StrategyFactoryV2Error("failure_facts_required")
    for field in (
        "repairability",
        "nextExperiment",
        "changedVariable",
        "parentStrategy",
        "familyFingerprint",
    ):
        _require_nonempty_text(payload, field)
    correlation = payload.get("signalCorrelation")
    if not isinstance(correlation, (int, float)) or not -1 <= correlation <= 1:
        raise StrategyFactoryV2Error("failure_signal_correlation_invalid")
    normalized = dict(payload)
    normalized["facts"] = [str(item) for item in payload["facts"]]
    normalized["inferences"] = [str(item) for item in payload["inferences"]]
    normalized["prohibitedRepair"] = sorted(
        {str(item) for item in payload["prohibitedRepair"] if str(item).strip()}
    )
    return normalized


HYPOTHESIS_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [*_HYPOTHESIS_REQUIRED, "sourceArtifactHashes"],
    "additionalProperties": False,
    "properties": {
        "hypothesisId": {"type": "string", "minLength": 1},
        "familyId": {"type": "string", "minLength": 1},
        "familyFingerprint": {"type": "string", "minLength": 1},
        "mechanism": {"type": "string", "minLength": 1},
        "falsifiableHypothesis": {"type": "string", "minLength": 1},
        "invalidationConditions": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        },
        "timeframe": {"type": "string", "enum": ["5m", "15m", "1h", "4h", "1d"]},
        "direction": {"type": "string", "enum": ["long", "short", "both", "market_neutral"]},
        "requiredData": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "exitPolicy": {"type": "object"},
        "sourceArtifactHashes": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        },
    },
}
FAILURE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [*_FAILURE_REQUIRED, "sourceArtifactHashes"],
    "additionalProperties": False,
    "properties": {
        "failureLayer": {"type": "string", "enum": list(FAILURE_LAYERS)},
        "facts": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "inferences": {"type": "array", "items": {"type": "string"}},
        "repairability": {"type": "string", "minLength": 1},
        "prohibitedRepair": {"type": "array", "items": {"type": "string"}},
        "nextExperiment": {"type": "string", "minLength": 1},
        "changedVariable": {"type": "string", "minLength": 1},
        "parentStrategy": {"type": "string", "minLength": 1},
        "familyFingerprint": {"type": "string", "minLength": 1},
        "signalCorrelation": {"type": "number", "minimum": -1, "maximum": 1},
        "sourceArtifactHashes": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        },
    },
}
