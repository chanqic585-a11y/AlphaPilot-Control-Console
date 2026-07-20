"""Versioned latency policy for Demo and future Live order hot paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .config import DATA_DIR
from .strategy_validation_hashing import stable_hash


DEFAULT_PROFILE_PATH = DATA_DIR / "v54_v60" / "latency" / "execution_latency_profile_v1.json"
_ALLOWED_TRANSPORT_MODES = {"auto", "websocket", "rest"}


def _load_default_profile(path: Path = DEFAULT_PROFILE_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("execution latency profile is unavailable or invalid") from error
    if not isinstance(value, dict):
        raise ValueError("execution latency profile must be an object")
    return value


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be a positive integer") from error
    if parsed <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return parsed


def build_execution_latency_profile(
    overrides: Mapping[str, Any] | None = None,
    *,
    source_path: Path = DEFAULT_PROFILE_PATH,
) -> dict[str, Any]:
    """Load, validate, and hash an immutable latency profile candidate."""

    profile = _load_default_profile(source_path)
    if overrides:
        profile.update(dict(overrides))
    profile.pop("executionLatencyProfileHash", None)

    version = str(profile.get("executionLatencyProfileVersion") or "").strip()
    if not version:
        raise ValueError("executionLatencyProfileVersion is required")
    profile["executionLatencyProfileVersion"] = version
    for field in (
        "signalToOrderSendTargetMs",
        "signalToOrderSendSoftWarnMs",
        "maximumSignalAgeMs",
        "exchangeAckTimeoutMs",
        "orderRequestExpiryMs",
        "criticalLatencyFailureMs",
    ):
        profile[field] = _positive_int(profile.get(field), field)

    if profile["signalToOrderSendTargetMs"] > profile["signalToOrderSendSoftWarnMs"]:
        raise ValueError("signal target cannot exceed the soft warning threshold")
    if profile["signalToOrderSendSoftWarnMs"] > profile["maximumSignalAgeMs"]:
        raise ValueError("signal soft warning cannot exceed maximum signal age")
    if profile["maximumSignalAgeMs"] > 20_000:
        raise ValueError("maximumSignalAgeMs cannot exceed the critical boundary")
    if profile["orderRequestExpiryMs"] > profile["maximumSignalAgeMs"]:
        raise ValueError("orderRequestExpiryMs cannot exceed maximumSignalAgeMs")
    if profile["criticalLatencyFailureMs"] != 20_000:
        raise ValueError("criticalLatencyFailureMs is a non-adjustable safety boundary")

    mode = str(profile.get("orderTransportMode") or "").strip().lower()
    if mode not in _ALLOWED_TRANSPORT_MODES:
        raise ValueError("orderTransportMode must be auto, websocket, or rest")
    profile["orderTransportMode"] = mode
    profile["executionLatencyProfileHash"] = stable_hash(
        profile,
        "execution_latency_profile",
    )
    return profile
