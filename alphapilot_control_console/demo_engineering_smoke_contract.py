"""Immutable, non-qualifying contract for explicit OKX Demo engineering smoke."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from .config import DATA_DIR


DEFAULT_CONTRACT_DIR = DATA_DIR / "demo_engineering_smoke_contracts"
_SENSITIVE_PARTS = ("apikey", "secretkey", "passphrase", "password", "credential", "accesstoken")
_V41_INSTRUMENT_FIELDS = ("instId", "tickSz", "lotSz", "minSz", "ctVal", "ctType", "state")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unsigned(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in contract.items() if key not in {"releaseId", "releaseHash"}}


def _reject_sensitive(value: Any, path: str = "engineeringSmokeContract") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            compact = str(key).replace("_", "").replace("-", "").lower()
            if any(part in compact for part in _SENSITIVE_PARTS):
                raise ValueError(f"Sensitive field is forbidden in engineering smoke contract: {path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


def validate_demo_engineering_smoke_contract(contract: dict[str, Any]) -> None:
    _reject_sensitive(contract)
    if contract.get("schemaVersion") != "alphapilot_demo_engineering_smoke_v1":
        raise ValueError("Unsupported Demo engineering smoke contract schema")
    required_exact = {
        "demoPurpose": "engineering_smoke",
        "evidenceClass": "demo_engineering_smoke",
        "strategyQualification": False,
        "promotionEligible": False,
        "forwardPerformanceEligible": False,
        "environment": "demo",
        "liveExecutionAllowed": False,
        "withdrawAllowed": False,
        "maximumConcurrentPositions": 1,
        "maximumAttempts": 3,
        "minimumOrderOnly": True,
    }
    for field, expected in required_exact.items():
        if contract.get(field) != expected:
            error = PermissionError if field in {
                "strategyQualification",
                "promotionEligible",
                "forwardPerformanceEligible",
                "environment",
                "liveExecutionAllowed",
                "withdrawAllowed",
            } else ValueError
            raise error(f"Invalid engineering smoke boundary: {field}")
    expected_hash = hashlib.sha256(_canonical(_unsigned(contract)).encode("utf-8")).hexdigest()
    if contract.get("releaseHash") != expected_hash:
        raise ValueError("Demo engineering smoke contract checksum mismatch")
    if contract.get("releaseId") != f"demo-engineering-smoke-{expected_hash[:20]}":
        raise ValueError("Demo engineering smoke contract id mismatch")


def build_demo_engineering_smoke_contract(
    *,
    createdAt: str,
    outputDir: Path = DEFAULT_CONTRACT_DIR,
) -> dict[str, Any]:
    unsigned: dict[str, Any] = {
        "schemaVersion": "alphapilot_demo_engineering_smoke_v1",
        "createdAt": str(createdAt),
        "demoPurpose": "engineering_smoke",
        "evidenceClass": "demo_engineering_smoke",
        "strategyQualification": False,
        "promotionEligible": False,
        "forwardPerformanceEligible": False,
        "environment": "demo",
        "liveExecutionAllowed": False,
        "withdrawAllowed": False,
        "maximumConcurrentPositions": 1,
        "maximumAttempts": 3,
        "minimumOrderOnly": True,
    }
    release_hash = hashlib.sha256(_canonical(unsigned).encode("utf-8")).hexdigest()
    contract = {
        **unsigned,
        "releaseId": f"demo-engineering-smoke-{release_hash[:20]}",
        "releaseHash": release_hash,
    }
    validate_demo_engineering_smoke_contract(contract)
    outputDir.mkdir(parents=True, exist_ok=True)
    path = outputDir / f"{release_hash}.json"
    serialized = json.dumps(contract, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != contract:
            raise RuntimeError("Refusing to overwrite a differing hash-addressed engineering smoke contract")
        return contract
    path.write_text(serialized, encoding="utf-8", newline="\n")
    return contract


def _v41_unsigned(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in contract.items() if key != "contractHash"}


def _positive_decimal(value: Any, field: str) -> None:
    try:
        if Decimal(str(value)) <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        raise ValueError(f"V41-V45 engineering smoke field must be positive: {field}") from None


def validate_v41_v45_engineering_smoke_contract(contract: dict[str, Any]) -> None:
    """Validate the exact, strategy-ineligible contract used by the V41-V45 smoke."""

    _reject_sensitive(contract)
    if contract.get("schemaVersion") != "alphapilot_v41_v45_engineering_smoke_contract_v1":
        raise ValueError("Unsupported V41-V45 engineering smoke contract schema")
    required_exact = {
        "purpose": "engineering_only",
        "environment": "demo",
        "xSimulatedTrading": "1",
        "maximumConcurrentPositions": 1,
        "maximumOpenPositions": 1,
        "noAdding": True,
        "noAveraging": True,
        "noMartingale": True,
        "releaseQualification": False,
        "strategyQualification": False,
        "formalPass": False,
        "promotionEvidenceEligible": False,
        "livePromotionEligible": False,
        "liveExecutionAllowed": False,
        "withdrawAllowed": False,
    }
    for field, expected in required_exact.items():
        if contract.get(field) != expected:
            raise PermissionError(f"Invalid V41-V45 engineering smoke boundary: {field}")

    instrument = contract.get("instrument")
    if not isinstance(instrument, dict) or set(instrument) != set(_V41_INSTRUMENT_FIELDS):
        raise ValueError("V41-V45 engineering smoke contract requires exact instrument metadata")
    for field in _V41_INSTRUMENT_FIELDS:
        if not str(instrument.get(field) or "").strip():
            raise ValueError(f"Missing V41-V45 engineering smoke instrument field: {field}")
    if not str(instrument["instId"]).endswith("-USDT-SWAP"):
        raise ValueError("V41-V45 engineering smoke instrument must be an exact USDT SWAP")
    if instrument["state"] != "live":
        raise ValueError("V41-V45 engineering smoke instrument must be live")
    for field in ("tickSz", "lotSz", "minSz", "ctVal"):
        _positive_decimal(instrument[field], f"instrument.{field}")
    if contract.get("instId") != instrument["instId"]:
        raise ValueError("V41-V45 engineering smoke instId does not match instrument metadata")
    if contract.get("maximumSize") != instrument["minSz"]:
        raise ValueError("V41-V45 engineering smoke maximumSize must equal minSz")
    if not str(contract.get("accountMode") or "").strip():
        raise ValueError("V41-V45 engineering smoke accountMode is required")
    if contract.get("positionMode") not in {"net_mode", "long_short_mode"}:
        raise ValueError("Unsupported V41-V45 engineering smoke positionMode")

    expected_hash = hashlib.sha256(_canonical(_v41_unsigned(contract)).encode("utf-8")).hexdigest()
    if contract.get("contractHash") != expected_hash:
        raise ValueError("V41-V45 engineering smoke contract checksum mismatch")


def build_v41_v45_engineering_smoke_contract(
    *,
    createdAt: str,
    instrument: Mapping[str, Any],
    accountMode: str,
    positionMode: str,
) -> dict[str, Any]:
    """Freeze the exact Demo instrument and one-minimum-order safety boundary."""

    exact_instrument = {field: str(instrument.get(field) or "").strip() for field in _V41_INSTRUMENT_FIELDS}
    unsigned: dict[str, Any] = {
        "schemaVersion": "alphapilot_v41_v45_engineering_smoke_contract_v1",
        "createdAt": str(createdAt),
        "purpose": "engineering_only",
        "environment": "demo",
        "xSimulatedTrading": "1",
        "instrument": exact_instrument,
        "instId": exact_instrument["instId"],
        "accountMode": str(accountMode),
        "positionMode": str(positionMode),
        "maximumSize": exact_instrument["minSz"],
        "maximumConcurrentPositions": 1,
        "maximumOpenPositions": 1,
        "noAdding": True,
        "noAveraging": True,
        "noMartingale": True,
        "releaseQualification": False,
        "strategyQualification": False,
        "formalPass": False,
        "promotionEvidenceEligible": False,
        "livePromotionEligible": False,
        "liveExecutionAllowed": False,
        "withdrawAllowed": False,
    }
    contract = {
        **unsigned,
        "contractHash": hashlib.sha256(_canonical(unsigned).encode("utf-8")).hexdigest(),
    }
    validate_v41_v45_engineering_smoke_contract(contract)
    return contract


def build_v41_v45_engineering_smoke_approval_overlay(
    contract: dict[str, Any],
    *,
    environment: Mapping[str, str],
) -> dict[str, Any]:
    """Approve only an exact contract hash from the current process environment."""

    validate_v41_v45_engineering_smoke_contract(contract)
    expected = str(contract["contractHash"])
    supplied = str(environment.get("ALPHAPILOT_ENGINEERING_SMOKE_APPROVED") or "").strip()
    if supplied != expected:
        raise PermissionError("V41-V45 engineering smoke approval hash is missing or does not match")
    return {
        "schemaVersion": "alphapilot_v41_v45_engineering_smoke_approval_overlay_v1",
        "status": "approved",
        "environment": "demo",
        "approvedContractHash": expected,
        "processOnly": True,
        "credentialsPersisted": False,
        "strategyQualification": False,
        "promotionEvidenceEligible": False,
        "liveExecutionAllowed": False,
        "withdrawAllowed": False,
    }
