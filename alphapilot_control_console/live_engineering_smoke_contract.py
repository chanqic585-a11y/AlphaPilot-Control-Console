"""Immutable contract and exact approval gate for one OKX Live engineering smoke."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .config import PROJECT_ROOT


_SCHEMA_VERSION = "alphapilot_live_engineering_smoke_contract_v1"
_APPROVAL_SCHEMA_VERSION = "alphapilot_live_engineering_smoke_approval_request_v1"
V58_EVIDENCE_ROOT = PROJECT_ROOT / "reports" / "v54_v60" / "v58_live_engineering_smoke"
LIVE_ENGINEERING_SMOKE_CONTRACT_PATH = V58_EVIDENCE_ROOT / "live_engineering_smoke_contract.json"
LIVE_ENGINEERING_SMOKE_APPROVAL_REQUEST_PATH = V58_EVIDENCE_ROOT / "live_engineering_smoke_approval_request.json"
LIVE_ENGINEERING_SMOKE_STATUS_PATH = V58_EVIDENCE_ROOT / "live_engineering_smoke_status.json"


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_live_engineering_smoke_contract(
    *,
    created_at: str,
    maximum_notional_usdt: float,
) -> dict[str, Any]:
    if not str(created_at or "").strip():
        raise ValueError("created_at is required")
    maximum_notional = float(maximum_notional_usdt)
    if not 0 < maximum_notional <= 10:
        raise ValueError("Live engineering smoke maximum notional must be in (0, 10] USDT")
    core: dict[str, Any] = {
        "schemaVersion": _SCHEMA_VERSION,
        "createdAt": str(created_at),
        "environment": "okx_live",
        "purpose": "connectivity_and_order_lifecycle_engineering_smoke_only",
        "maximumAttempts": 1,
        "maximumConcurrentPositions": 1,
        "maximumNotionalUsdt": maximum_notional,
        "sizePolicy": "exchange_minimum_size",
        "side": "buy",
        "orderType": "limit",
        "limitOffsetBps": 1000,
        "marginMode": "isolated",
        "maximumLeverage": 1,
        "leverageRequirement": "account_preconfigured_1x",
        "attachedProtectionRequired": True,
        "mandatoryCancel": True,
        "finalZeroOpenOrderRequired": True,
        "finalZeroPositionRequired": True,
        "strategyQualification": False,
        "promotionEligible": False,
        "liveCanaryEvidenceEligible": False,
        "rawCredentialStorageAllowed": False,
        "privateAccountValuesPersisted": False,
        "withdrawAllowed": False,
        "transferAllowed": False,
    }
    digest = hashlib.sha256(_canonical_json(core)).hexdigest()
    contract = {**core, "contractHash": f"live_engineering_smoke_{digest}"}
    validate_live_engineering_smoke_contract(contract)
    return contract


def validate_live_engineering_smoke_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schemaVersion": _SCHEMA_VERSION,
        "environment": "okx_live",
        "maximumAttempts": 1,
        "maximumConcurrentPositions": 1,
        "sizePolicy": "exchange_minimum_size",
        "side": "buy",
        "orderType": "limit",
        "limitOffsetBps": 1000,
        "marginMode": "isolated",
        "maximumLeverage": 1,
        "mandatoryCancel": True,
        "finalZeroOpenOrderRequired": True,
        "finalZeroPositionRequired": True,
        "strategyQualification": False,
        "promotionEligible": False,
        "liveCanaryEvidenceEligible": False,
        "rawCredentialStorageAllowed": False,
        "privateAccountValuesPersisted": False,
        "withdrawAllowed": False,
        "transferAllowed": False,
    }
    mismatches = [key for key, value in expected.items() if contract.get(key) != value]
    if mismatches:
        raise ValueError("Unsafe or invalid Live engineering smoke contract: " + ",".join(mismatches))
    maximum_notional = float(contract.get("maximumNotionalUsdt") or 0)
    if not 0 < maximum_notional <= 10:
        raise ValueError("Live engineering smoke notional exceeds the bounded smoke limit")
    supplied_hash = str(contract.get("contractHash") or "")
    core = {key: value for key, value in contract.items() if key != "contractHash"}
    expected_hash = "live_engineering_smoke_" + hashlib.sha256(_canonical_json(core)).hexdigest()
    if supplied_hash != expected_hash:
        raise ValueError("Live engineering smoke contract hash mismatch")
    return dict(contract)


def build_live_engineering_smoke_approval_request(
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    validated = validate_live_engineering_smoke_contract(contract)
    contract_hash = str(validated["contractHash"])
    return {
        "schemaVersion": _APPROVAL_SCHEMA_VERSION,
        "status": "blocked_waiting_exact_live_smoke_approval",
        "environment": "okx_live",
        "contractHash": contract_hash,
        "maximumAttempts": 1,
        "maximumNotionalUsdt": validated["maximumNotionalUsdt"],
        "requiredConfirmation": f"APPROVE_OKX_LIVE_ENGINEERING_SMOKE {contract_hash}",
        "approvalScope": "one_engineering_smoke_attempt_only",
        "strategyQualification": False,
        "liveCanaryEvidenceEligible": False,
        "withdrawAllowed": False,
    }


def validate_live_engineering_smoke_approval(
    contract: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> dict[str, Any]:
    validated = validate_live_engineering_smoke_contract(contract)
    request = build_live_engineering_smoke_approval_request(validated)
    if str(approval.get("actor") or "") != "user_explicit":
        raise PermissionError("Explicit user approval is required for the Live engineering smoke")
    if str(approval.get("contractHash") or "") != str(validated["contractHash"]):
        raise PermissionError("Live engineering smoke approval contract hash mismatch")
    if str(approval.get("confirmation") or "") != str(request["requiredConfirmation"]):
        raise PermissionError("Exact Live engineering smoke confirmation is required")
    return {
        "status": "approved",
        "actor": "user_explicit",
        "contractHash": validated["contractHash"],
        "approvalScope": "one_engineering_smoke_attempt_only",
    }


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def build_live_engineering_smoke_readiness_status(
    root: Path | str = V58_EVIDENCE_ROOT,
) -> dict[str, Any]:
    evidence_root = Path(root)
    contract = _load_json(evidence_root / LIVE_ENGINEERING_SMOKE_CONTRACT_PATH.name)
    if contract is None:
        return {
            "schemaVersion": "alphapilot_live_engineering_smoke_readiness_v1",
            "status": "not_prepared",
            "environment": "okx_live",
            "approved": False,
            "orderAttemptCount": 0,
            "strategyQualification": False,
            "liveCanaryEvidenceEligible": False,
            "withdrawAllowed": False,
        }
    validated = validate_live_engineering_smoke_contract(contract)
    request = _load_json(evidence_root / LIVE_ENGINEERING_SMOKE_APPROVAL_REQUEST_PATH.name)
    if request is None:
        request = build_live_engineering_smoke_approval_request(validated)
    status_payload = _load_json(evidence_root / LIVE_ENGINEERING_SMOKE_STATUS_PATH.name) or {}
    return {
        "schemaVersion": "alphapilot_live_engineering_smoke_readiness_v1",
        "status": str(
            status_payload.get("status")
            or "blocked_waiting_exact_live_smoke_approval"
        ),
        "environment": "okx_live",
        "contractHash": validated["contractHash"],
        "contract": validated,
        "approvalRequest": request,
        "approved": False,
        "orderAttemptCount": 0,
        "strategyQualification": False,
        "promotionEligible": False,
        "liveCanaryEvidenceEligible": False,
        "rawCredentialStorageAllowed": False,
        "withdrawAllowed": False,
    }
