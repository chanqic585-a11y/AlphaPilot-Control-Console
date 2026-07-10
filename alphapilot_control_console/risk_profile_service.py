"""API-safe operations for versioned RiskProfiles."""

from __future__ import annotations

from typing import Any

from .risk_profile_store import (
    RISK_PROFILE_STORE_PATH,
    RiskProfileStore,
    build_risk_profile_status,
)


_SENSITIVE_PARTS = ("apikey", "secret", "passphrase", "password", "credential", "withdraw")


def _reject_sensitive(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            compact = str(key).replace("_", "").replace("-", "").lower()
            if any(part in compact for part in _SENSITIVE_PARTS):
                raise ValueError(f"Sensitive field is forbidden in RiskProfile input: {path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


def create_risk_profile_version(payload: dict[str, Any]) -> dict[str, Any]:
    _reject_sensitive(payload)
    store = RiskProfileStore(RISK_PROFILE_STORE_PATH)
    try:
        base_id = str(payload.get("baseRiskProfileId") or "")
        base = store.get_profile(base_id)["profile"] if base_id else {}
        overrides = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
        profile = {**base, **overrides}
        if not profile:
            raise ValueError("RiskProfile input is required")
        profile["schemaVersion"] = "risk_profile_v1"
        profile["version"] = None
        created = store.create_profile(profile, status="draft")
    finally:
        store.close()
    return {
        "ok": True,
        "createdProfile": created,
        "executionEnabled": False,
        "riskProfiles": build_risk_profile_status(RISK_PROFILE_STORE_PATH),
    }


def activate_risk_profile_version(payload: dict[str, Any]) -> dict[str, Any]:
    _reject_sensitive(payload)
    store = RiskProfileStore(RISK_PROFILE_STORE_PATH)
    try:
        result = store.activate(
            str(payload.get("riskProfileId") or ""),
            actor=str(payload.get("actor") or ""),
            confirmation=str(payload.get("confirmation") or ""),
            reason=str(payload.get("reason") or "manual_profile_activation"),
        )
    finally:
        store.close()
    return {
        "ok": True,
        **result,
        "riskProfiles": build_risk_profile_status(RISK_PROFILE_STORE_PATH),
    }


def rollback_risk_profile_version(payload: dict[str, Any]) -> dict[str, Any]:
    _reject_sensitive(payload)
    store = RiskProfileStore(RISK_PROFILE_STORE_PATH)
    try:
        result = store.rollback(
            str(payload.get("environment") or ""),
            actor=str(payload.get("actor") or ""),
            confirmation=str(payload.get("confirmation") or ""),
        )
    finally:
        store.close()
    return {
        "ok": True,
        **result,
        "riskProfiles": build_risk_profile_status(RISK_PROFILE_STORE_PATH),
    }
