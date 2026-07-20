"""Fail-closed admission helpers for provisional research-only Demo releases."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable, Mapping


def _parse_timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def classify_legacy_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    legacy = str(contract.get("releaseMode") or "") == "experimental_override"
    return {
        "classification": (
            "legacy_experimental_override" if legacy else "non_legacy_release"
        ),
        "executionEnabled": False if legacy else None,
        "forwardEvidenceEligible": False if legacy else None,
        "livePromotionEligible": False if legacy else None,
    }


def validate_exact_provisional_approval(
    release: Mapping[str, Any], approval: Mapping[str, Any]
) -> dict[str, Any]:
    if release.get("schemaVersion") != "provisional_research_demo_v1":
        raise ValueError("unsupported provisional release")
    forbidden_true = (
        "formalPass",
        "cleanHistoricalOosPass",
        "livePromotionEligible",
        "automaticLivePromotionAllowed",
        "approved",
        "demoArm",
    )
    if any(release.get(field) is not False for field in forbidden_true):
        raise PermissionError("provisional release claims forbidden qualification")
    if release.get("route") != "blocked_waiting_exact_release_approval":
        raise PermissionError("provisional release is not waiting for exact approval")
    if approval.get("releaseHash") != release.get("releaseHash"):
        raise PermissionError("exact release hash approval required")
    if approval.get("riskOverlayHash") != release.get("riskOverlayHash"):
        raise PermissionError("exact risk overlay hash approval required")
    return {
        "status": "approved_not_armed",
        "releaseId": release["releaseId"],
        "releaseHash": release["releaseHash"],
        "riskOverlayHash": release["riskOverlayHash"],
        "demoArm": False,
        "livePromotionEligible": False,
    }


def count_forward_evidence(
    records: Iterable[Mapping[str, Any]],
    *,
    release_id: str,
    release_hash: str,
    approved_at: str,
) -> dict[str, Any]:
    approved = _parse_timestamp(approved_at)
    eligible = 0
    excluded = 0
    pre_approval = 0
    engineering_smoke = 0
    reasons: dict[str, int] = {}

    def reject(reason: str) -> None:
        nonlocal excluded, pre_approval, engineering_smoke
        excluded += 1
        reasons[reason] = reasons.get(reason, 0) + 1
        if reason == "pre_approval":
            pre_approval += 1
        if reason == "engineering_smoke":
            engineering_smoke += 1

    for record in records:
        evidence_class = str(record.get("evidenceClass") or "")
        purpose = str(record.get("executionPurpose") or "")
        if evidence_class == "demo_engineering_smoke" or purpose == "connectivity_smoke_only":
            reject("engineering_smoke")
            continue
        if str(record.get("environment") or "") != "okx_demo":
            reject("non_demo_environment")
            continue
        if (
            str(record.get("releaseId") or "") != release_id
            or str(record.get("releaseHash") or "") != release_hash
        ):
            reject("release_identity_mismatch")
            continue
        if str(record.get("status") or "") != "closed":
            reject("not_closed")
            continue
        if purpose not in {"", "strategy_execution", "automatic_strategy_execution"}:
            reject("non_strategy_execution")
            continue
        try:
            entry_at = _parse_timestamp(record.get("entryAt"))
        except (TypeError, ValueError):
            reject("invalid_entry_timestamp")
            continue
        if entry_at <= approved:
            reject("pre_approval")
            continue
        eligible += 1

    return {
        "schemaVersion": "provisional_demo_forward_evidence_count_v1",
        "releaseId": release_id,
        "releaseHash": release_hash,
        "approvedAt": approved.isoformat(),
        "eligibleClosedTradeCount": eligible,
        "excludedRecordCount": excluded,
        "preApprovalExcludedCount": pre_approval,
        "engineeringSmokeExcludedCount": engineering_smoke,
        "exclusionReasons": dict(sorted(reasons.items())),
    }
