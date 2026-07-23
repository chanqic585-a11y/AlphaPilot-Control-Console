from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT


DEFAULT_POLICY_PATH = PROJECT_ROOT / "config" / "strategy_factory_v2.json"
REQUIRED_CLOSURE_SCHEMA = "strategy_factory_v2_real_trial_closure_v1"
_FORMAL_EVIDENCE_TYPES = ("job", "claim", "attempt", "result", "read")


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"strategy_factory_v2_json_object_required:{path}")
    return payload


def _resolve_receipt_path(policy_path: Path, value: object) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = Path(text)
    if candidate.is_absolute():
        return candidate
    return (policy_path.parent / candidate).resolve()


def evaluate_continuous_research_readiness(
    policy_path: Path = DEFAULT_POLICY_PATH,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    policy = _read_object(policy_path)
    continuous = policy.get("continuousResearch")
    if not isinstance(continuous, dict):
        raise ValueError("continuous_research_policy_missing")

    blockers: list[str] = []
    if not bool(continuous.get("enabled")):
        blockers.append("continuous_research_policy_disabled")

    receipt_path = _resolve_receipt_path(
        policy_path, continuous.get("closureReceiptPath")
    )
    receipt: dict[str, Any] | None = None
    if receipt_path is None or not receipt_path.is_file():
        if not blockers:
            blockers.append("real_trial_closure_receipt_missing")
    else:
        receipt = _read_object(receipt_path)
        if receipt.get("schemaVersion") != REQUIRED_CLOSURE_SCHEMA:
            blockers.append("real_trial_closure_schema_invalid")
        if receipt.get("acceptedRealTrialClosure") is not True:
            blockers.append("real_trial_closure_not_accepted")
        if int(receipt.get("completedTrialCount") or 0) <= 0:
            blockers.append("real_trial_closure_completed_trial_missing")
        formal = receipt.get("formalEvidence")
        if not isinstance(formal, dict) or any(
            int(formal.get(item) or 0) <= 0 for item in _FORMAL_EVIDENCE_TYPES
        ):
            blockers.append("real_trial_closure_formal_evidence_incomplete")
        source_hashes = receipt.get("sourceArtifactHashes")
        if not isinstance(source_hashes, list) or not source_hashes:
            blockers.append("real_trial_closure_source_hashes_missing")

    return {
        "schemaVersion": "strategy_factory_v2_continuous_readiness_v1",
        "allowed": not blockers,
        "blockers": blockers,
        "policyPath": str(policy_path.resolve()),
        "closureReceiptPath": str(receipt_path) if receipt_path else None,
        "completedTrialCount": int((receipt or {}).get("completedTrialCount") or 0),
        "formalEvidence": dict((receipt or {}).get("formalEvidence") or {}),
        "executionAuthorized": False,
    }


def require_continuous_research_enable(
    policy_path: Path = DEFAULT_POLICY_PATH,
) -> None:
    readiness = evaluate_continuous_research_readiness(policy_path)
    if not readiness["allowed"]:
        raise ValueError(
            "continuous_research_enable_blocked:"
            + ",".join(str(item) for item in readiness["blockers"])
        )
