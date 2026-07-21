"""Strict local validation for immutable Advisory-R exit policies."""

from __future__ import annotations

import math
from typing import Any, Mapping

from .strategy_validation_hashing import stable_hash


POLICY_VERSION = "advisory_r_exit_policy_v1"
POLICY_FIELDS = {
    "version",
    "mode",
    "maximumHoldBars",
    "initialStopMayWiden",
    "parameters",
}
SUPPORTED_MODES = {
    "fixed_r",
    "partial_then_trailing",
    "structure_or_time",
    "hybrid",
    "trend_following_exit",
}
STRUCTURE_RULE_FIELDS = {
    "residual_neutral_zone": {"kind", "absoluteZscoreMaximum"},
    "correlation_recovery": {"kind", "minimumCorrelation"},
    "trend_invalidation": {"kind", "fastWindow", "slowWindow"},
    "session_end": {"kind", "utcHour"},
    "beta_rank_exit": {"kind", "maximumRankPercentile"},
    "event_reversal": {"kind", "confirmationBars"},
}


def _number(value: Any, name: str, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return result


def _exact_fields(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing or unknown:
        raise ValueError(
            f"invalid {name} fields; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )


def _validate_structure_rule(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("structureRule must be a declarative object")
    kind = str(value.get("kind") or "")
    expected = STRUCTURE_RULE_FIELDS.get(kind)
    if expected is None:
        raise ValueError(f"unsupported structure rule: {kind or '<missing>'}")
    _exact_fields(value, expected, "structureRule")
    if kind == "residual_neutral_zone":
        _number(value["absoluteZscoreMaximum"], "absoluteZscoreMaximum", minimum=0.01, maximum=5.0)
    elif kind == "correlation_recovery":
        _number(value["minimumCorrelation"], "minimumCorrelation", minimum=-1.0, maximum=1.0)
    elif kind == "trend_invalidation":
        fast = _number(value["fastWindow"], "fastWindow", minimum=2, maximum=500)
        slow = _number(value["slowWindow"], "slowWindow", minimum=3, maximum=1_000)
        if not fast.is_integer() or not slow.is_integer() or fast >= slow:
            raise ValueError("trend windows must be integers with fastWindow below slowWindow")
    elif kind == "session_end":
        if not _number(value["utcHour"], "utcHour", minimum=0, maximum=23).is_integer():
            raise ValueError("utcHour must be an integer")
    elif kind == "beta_rank_exit":
        _number(value["maximumRankPercentile"], "maximumRankPercentile", minimum=0.01, maximum=1.0)
    elif kind == "event_reversal":
        if not _number(value["confirmationBars"], "confirmationBars", minimum=1, maximum=100).is_integer():
            raise ValueError("confirmationBars must be an integer")


def _validate_partial(parameters: Mapping[str, Any]) -> None:
    _number(parameters["partialAtR"], "partialAtR", minimum=0.01, maximum=20.0)
    fraction = _number(parameters["partialFraction"], "partialFraction", minimum=0.000001, maximum=0.999999)
    if not 0.0 < fraction < 1.0:
        raise ValueError("partialFraction must be strictly between zero and one")


def validate_canonical_exit_policy(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("exit policy must be an object")
    _exact_fields(payload, POLICY_FIELDS, "exit policy")
    if payload.get("version") != POLICY_VERSION:
        raise ValueError("unsupported exit-policy version")
    mode = str(payload.get("mode") or "")
    if mode not in SUPPORTED_MODES:
        raise ValueError("unsupported exit-policy mode")
    hold_bars = payload.get("maximumHoldBars")
    if isinstance(hold_bars, bool) or not isinstance(hold_bars, int) or not 1 <= hold_bars <= 10_000:
        raise ValueError("maximumHoldBars must be an integer between 1 and 10000")
    if payload.get("initialStopMayWiden") is not False:
        raise ValueError("initial stop may not widen")
    parameters = payload.get("parameters")
    if not isinstance(parameters, Mapping):
        raise ValueError("exit policy parameters must be an object")

    if mode == "fixed_r":
        _exact_fields(parameters, {"targetR"}, "exit-policy parameters")
        _number(parameters["targetR"], "targetR", minimum=0.01, maximum=20.0)
    elif mode == "partial_then_trailing":
        _exact_fields(
            parameters,
            {"partialAtR", "partialFraction", "trailingAtrMultiple"},
            "exit-policy parameters",
        )
        _validate_partial(parameters)
        _number(parameters["trailingAtrMultiple"], "trailingAtrMultiple", minimum=0.01, maximum=20.0)
    elif mode == "structure_or_time":
        _exact_fields(parameters, {"structureRule"}, "exit-policy parameters")
        _validate_structure_rule(parameters["structureRule"])
    elif mode == "hybrid":
        remainder_mode = str(parameters.get("remainderMode") or "")
        if remainder_mode == "trailing":
            _exact_fields(
                parameters,
                {"partialAtR", "partialFraction", "remainderMode", "trailingAtrMultiple"},
                "exit-policy parameters",
            )
            _number(parameters["trailingAtrMultiple"], "trailingAtrMultiple", minimum=0.01, maximum=20.0)
        elif remainder_mode == "structure":
            _exact_fields(
                parameters,
                {"partialAtR", "partialFraction", "remainderMode", "structureRule"},
                "exit-policy parameters",
            )
            _validate_structure_rule(parameters["structureRule"])
        else:
            raise ValueError("remainderMode must be trailing or structure")
        _validate_partial(parameters)
    else:
        _exact_fields(
            parameters,
            {"trailingAtrMultiple", "trendRule"},
            "exit-policy parameters",
        )
        _number(
            parameters["trailingAtrMultiple"],
            "trailingAtrMultiple",
            minimum=0.01,
            maximum=20.0,
        )
        _validate_structure_rule(parameters["trendRule"])
    return dict(payload)


def exit_policy_hash(payload: Mapping[str, Any]) -> str:
    return stable_hash(validate_canonical_exit_policy(payload), "exit_policy")


def is_advisory_definition(definition: Mapping[str, Any]) -> bool:
    return str(definition.get("schemaVersion") or "").endswith("_v2") or any(
        key in definition for key in ("exitPolicy", "canonicalExitPolicy", "exitPolicyHash")
    )


def validate_definition_exit_policy(definition: Mapping[str, Any]) -> dict[str, Any]:
    policy = definition.get("exitPolicy") or definition.get("canonicalExitPolicy")
    normalized = validate_canonical_exit_policy(policy)
    expected_hash = str(definition.get("exitPolicyHash") or "")
    if not expected_hash:
        raise ValueError("exit policy hash is required")
    if exit_policy_hash(normalized) != expected_hash:
        raise ValueError("exit policy hash mismatch")
    return normalized


def advisory_target_r(policy: Mapping[str, Any]) -> float | None:
    normalized = validate_canonical_exit_policy(policy)
    parameters = normalized["parameters"]
    if normalized["mode"] == "fixed_r":
        return float(parameters["targetR"])
    if normalized["mode"] in {"partial_then_trailing", "hybrid"}:
        return float(parameters["partialAtR"])
    return None
