"""Build sanitized, read-only evidence used by the V62.4 acceptance UI."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any


class UiEvidenceError(RuntimeError):
    pass


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise UiEvidenceError(f"invalid JSON evidence: {path}") from error
    if not isinstance(payload, dict):
        raise UiEvidenceError(f"evidence must be a JSON object: {path}")
    return payload


def _file_hash(path: Path) -> str:
    return f"sha256:{sha256(path.read_bytes()).hexdigest()}"


def _candidate_ids(rows: object) -> list[str]:
    if not isinstance(rows, list):
        return []
    return [
        str(row["candidateId"])
        for row in rows
        if isinstance(row, dict) and row.get("candidateId")
    ]


def build_current_pilot_projection(
    campaign_summary_path: Path,
    formal_handoff_path: Path,
    *,
    formal_result_receipt_path: Path | None = None,
) -> dict[str, Any]:
    campaign_summary_path = Path(campaign_summary_path)
    formal_handoff_path = Path(formal_handoff_path)
    summary = _read_object(campaign_summary_path)
    handoff = _read_object(formal_handoff_path)
    campaign_id = str(summary.get("campaignId") or "")
    if not campaign_id or campaign_id != str(handoff.get("campaignId") or ""):
        raise UiEvidenceError("campaign summary and formal handoff identities differ")
    ready_ids = _candidate_ids(handoff.get("readyCandidates"))
    blocked_ids = _candidate_ids(handoff.get("blockedCandidates"))
    ready_count = int(summary.get("formalReadyCandidateCount") or 0)
    blocked_count = int(summary.get("formalBlockedCandidateCount") or 0)
    if ready_count != len(ready_ids) or blocked_count != len(blocked_ids):
        raise UiEvidenceError("formal candidate counts do not match handoff rows")
    if int(summary.get("formalRunCount") or 0) != int(
        handoff.get("formalRunCount") or 0
    ):
        raise UiEvidenceError("formal run counts differ")
    if int(summary.get("resultReadCount") or 0) != int(
        handoff.get("resultReadCount") or 0
    ):
        raise UiEvidenceError("formal result read counts differ")
    projection = {
        "schemaVersion": "alphapilot_v62_4_current_pilot_projection_v1",
        "authority": "current_v62_4_acceptance_pilot",
        "campaignId": campaign_id,
        "status": summary.get("status"),
        "candidateCount": int(summary.get("candidateCount") or 0),
        "trialCount": int(summary.get("trialCount") or 0),
        "stableSelectionCount": int(summary.get("stableSelectionCount") or 0),
        "formalReadyCandidateCount": ready_count,
        "formalBlockedCandidateCount": blocked_count,
        "formalRunCount": int(summary.get("formalRunCount") or 0),
        "resultReadCount": int(summary.get("resultReadCount") or 0),
        "formalReadyCandidateIds": ready_ids,
        "formalBlockedCandidateIds": blocked_ids,
        "sourceHashes": {
            "campaignSummary": _file_hash(campaign_summary_path),
            "formalHandoff": _file_hash(formal_handoff_path),
        },
        "readOnly": True,
        "approvalGranted": False,
        "demoArm": False,
        "strategyOrderCount": 0,
    }
    if formal_result_receipt_path is None:
        return projection

    receipt_path = Path(formal_result_receipt_path)
    receipt = _read_object(receipt_path)
    formal_candidate_id = str(receipt.get("candidateId") or "")
    if not formal_candidate_id or formal_candidate_id not in ready_ids:
        raise UiEvidenceError(
            "formal result receipt candidate is not a formal-ready pilot candidate"
        )
    run_count = int(receipt.get("formalRunCount") or 0)
    read_count = int(receipt.get("resultReadCount") or 0)
    if run_count != 1 or read_count != 1:
        raise UiEvidenceError("formal result receipt must prove exactly one run and read")
    result_fields = receipt.get("selectedResultFields") or {}
    if not isinstance(result_fields, dict):
        result_fields = {}
    formal_pass_values = {
        value
        for value in result_fields.get("formalPass") or []
        if isinstance(value, bool)
    }
    if len(formal_pass_values) != 1:
        raise UiEvidenceError("formal result receipt has ambiguous formalPass evidence")
    formal_pass = formal_pass_values.pop()
    projection.update(
        {
            "status": (
                "formal_completed_passed"
                if formal_pass
                else "formal_completed_not_passed"
            ),
            "formalRunCount": run_count,
            "resultReadCount": read_count,
            "formalCampaignId": str(receipt.get("campaignId") or ""),
            "formalCandidateId": formal_candidate_id,
            "formalPass": formal_pass,
            "formalRoute": receipt.get("route"),
            "releaseCount": int(receipt.get("releaseCount") or 0),
            "demoArm": bool(receipt.get("demoArm")),
            "strategyOrderCount": int(receipt.get("orderCount") or 0),
        }
    )
    projection["sourceHashes"]["formalResultReadReceipt"] = _file_hash(receipt_path)
    return projection


def build_provider_smoke_summary(source_path: Path) -> dict[str, Any]:
    source_path = Path(source_path)
    source = _read_object(source_path)
    worker = source.get("aiWorkerIdentity") or {}
    if not isinstance(worker, dict):
        worker = {}
    unsafe = (
        bool(source.get("executionAuthorized"))
        or bool(source.get("runtimeArmed"))
        or bool(source.get("withdrawEnabled"))
        or bool(worker.get("exchangePrivateCredentialsPresent"))
        or bool(worker.get("executionAuthority"))
    )
    if unsafe:
        raise UiEvidenceError("provider smoke source violates the research-only boundary")
    safe_checks: list[dict[str, Any]] = []
    for check in source.get("checks") or []:
        if not isinstance(check, dict):
            continue
        if bool(check.get("executionAuthorized")):
            raise UiEvidenceError("provider smoke check has execution authority")
        safe_checks.append(
            {
                "taskType": check.get("taskType"),
                "routeMode": check.get("routeMode"),
                "status": check.get("status"),
                "executionAuthorized": False,
            }
        )
    return {
        "schemaVersion": "alphapilot_v62_4_provider_smoke_summary_v1",
        "status": source.get("status") or "not_available",
        "providerSmokeInputHash": source.get("providerSmokeInputHash"),
        "checks": safe_checks,
        "executionAuthorized": False,
        "credentialsPersisted": False,
        "runtimeArmed": False,
        "withdrawEnabled": False,
        "sourceHash": _file_hash(source_path),
    }
