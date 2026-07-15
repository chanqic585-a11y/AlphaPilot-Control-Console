"""Immutable, non-qualifying contract for explicit OKX Demo engineering smoke."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR


DEFAULT_CONTRACT_DIR = DATA_DIR / "demo_engineering_smoke_contracts"
_SENSITIVE_PARTS = ("apikey", "secretkey", "passphrase", "password", "credential", "accesstoken")


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
