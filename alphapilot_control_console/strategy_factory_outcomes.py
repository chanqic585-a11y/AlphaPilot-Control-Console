from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence


_FORMAL_HANDOFF_ZERO_COUNTERS = (
    "formalRunCount",
    "formalInputReadCount",
    "resultReadCount",
    "lockedOosAccessCount",
    "releaseCount",
    "approvalCount",
    "orderCount",
)


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stable_hash(prefix: str, payload: object) -> str:
    digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("strategy_factory_artifact_must_be_object")
    return payload


def _write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _artifact_manifest(root: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(
        item for item in root.glob("*.json") if item.name != "artifact_manifest.json"
    ):
        artifacts.append(
            {
                "relativePath": path.name,
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "sizeBytes": path.stat().st_size,
            }
        )
    core = {
        "schemaVersion": "strategy_factory_outcome_manifest_v1",
        "artifactCount": len(artifacts),
        "artifacts": artifacts,
    }
    return {**core, "manifestHash": _stable_hash("strategy_factory_outcome_manifest", core)}


def _load_releases(
    *,
    receipt: Mapping[str, Any],
    campaign_id: str,
    output_root: Path,
) -> list[dict[str, Any]]:
    release_count = int(receipt.get("releaseCount") or 0)
    if release_count == 0:
        return []
    supplied = str(receipt.get("artifactPath") or "").strip()
    if not supplied:
        raise ValueError("strategy_factory_release_artifact_missing")
    summary_path = Path(supplied)
    if not _inside(summary_path, output_root):
        raise ValueError("strategy_factory_artifact_path_outside_run")
    release_path = summary_path.parent / "immutable_releases.json"
    if not release_path.is_file():
        raise ValueError("strategy_factory_immutable_releases_missing")
    bundle = _read_object(release_path)
    if str(bundle.get("campaignId") or "") != campaign_id:
        raise ValueError("strategy_factory_release_campaign_mismatch")
    releases = bundle.get("releases")
    if not isinstance(releases, list) or len(releases) != release_count:
        raise ValueError("strategy_factory_release_count_mismatch")
    if bool(bundle.get("approved")) or bool(bundle.get("demoArm")) or int(bundle.get("orders") or 0):
        raise ValueError("strategy_factory_release_execution_boundary_crossed")
    return [dict(item) for item in releases if isinstance(item, Mapping)]


def _load_formal_validation_candidates(
    *,
    receipt: Mapping[str, Any],
    campaign_id: str,
    output_root: Path,
    configured_candidates: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if str(receipt.get("status") or "") != "awaiting_formal_validation":
        return [], {
            "formalHandoffStatus": None,
            "formalHandoffHash": None,
            "formalReadyCandidateCount": 0,
            "formalBlockedCandidateCount": 0,
        }
    supplied = str(receipt.get("artifactPath") or "").strip()
    if not supplied:
        raise ValueError("strategy_factory_selection_artifact_missing")
    summary_path = Path(supplied)
    if not _inside(summary_path, output_root):
        raise ValueError("strategy_factory_artifact_path_outside_run")
    selection_path = summary_path.parent / "neighborhood_selection.json"
    if not selection_path.is_file():
        raise ValueError("strategy_factory_neighborhood_selection_missing")
    bundle = _read_object(selection_path)
    if str(bundle.get("campaignId") or "") != campaign_id:
        raise ValueError("strategy_factory_selection_campaign_mismatch")
    selections = bundle.get("selections")
    if not isinstance(selections, list):
        raise ValueError("strategy_factory_selections_invalid")

    configured = set(configured_candidates)
    selected: dict[str, dict[str, Any]] = {}
    for selection in selections:
        if not isinstance(selection, Mapping) or not bool(selection.get("eligible")):
            continue
        candidate_id = str(selection.get("candidateId") or "").strip()
        trial_id = str(selection.get("selectedTrialId") or "").strip()
        if candidate_id not in configured:
            raise ValueError("strategy_factory_selection_candidate_mismatch")
        if not trial_id or candidate_id in selected:
            raise ValueError("strategy_factory_selection_identity_invalid")
        selected[candidate_id] = {
            "candidateId": candidate_id,
            "trialId": trial_id,
            "reason": str(
                selection.get("reason") or "stable_parameter_neighborhood"
            ),
            "status": "awaiting_formal_validation",
        }

    handoff_path = summary_path.parent / "formal_handoff.json"
    if not handoff_path.is_file():
        return list(selected.values()), {
            "formalHandoffStatus": "awaiting_external_readiness",
            "formalHandoffHash": None,
            "formalReadyCandidateCount": 0,
            "formalBlockedCandidateCount": 0,
        }

    handoff = _read_object(handoff_path)
    if str(handoff.get("campaignId") or "") != campaign_id:
        raise ValueError("strategy_factory_formal_handoff_campaign_mismatch")
    handoff_status = str(handoff.get("status") or "").strip()
    handoff_hash = str(handoff.get("handoffHash") or "").strip()
    if handoff_status not in {
        "awaiting_external_readiness",
        "ready_to_freeze",
        "partially_ready_to_freeze",
        "blocked_before_freeze",
    }:
        raise ValueError("strategy_factory_formal_handoff_status_invalid")
    if not handoff_hash:
        raise ValueError("strategy_factory_formal_handoff_hash_missing")
    for field in _FORMAL_HANDOFF_ZERO_COUNTERS:
        if int(handoff.get(field) or 0) != 0:
            raise ValueError(f"strategy_factory_formal_handoff_nonzero:{field}")
    if bool(handoff.get("demoArm")):
        raise ValueError("strategy_factory_formal_handoff_demo_arm_forbidden")

    ready_rows = handoff.get("readyCandidates")
    blocked_rows = handoff.get("blockedCandidates")
    if not isinstance(ready_rows, list) or not isinstance(blocked_rows, list):
        raise ValueError("strategy_factory_formal_handoff_candidates_invalid")
    if int(handoff.get("formalReadyCandidateCount") or 0) != len(ready_rows):
        raise ValueError("strategy_factory_formal_ready_count_mismatch")
    if int(handoff.get("blockedCandidateCount") or 0) != len(blocked_rows):
        raise ValueError("strategy_factory_formal_blocked_count_mismatch")

    pending: list[dict[str, Any]] = []
    disposition_ids: set[str] = set()
    for rows, expected_readiness, candidate_status in (
        (ready_rows, "ready", "ready_to_freeze"),
        (
            blocked_rows,
            "blocked",
            (
                "awaiting_external_readiness"
                if handoff_status == "awaiting_external_readiness"
                else "blocked_before_freeze"
            ),
        ),
    ):
        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError("strategy_factory_formal_candidate_invalid")
            candidate_id = str(row.get("candidateId") or "").strip()
            trial_id = str(row.get("selectedTrialId") or "").strip()
            selection = selected.get(candidate_id)
            if (
                selection is None
                or trial_id != selection["trialId"]
                or candidate_id in disposition_ids
            ):
                raise ValueError("strategy_factory_formal_identity_mismatch")
            readiness_status = str(row.get("readinessStatus") or "").strip()
            blockers = sorted({str(value) for value in row.get("blockers") or []})
            if readiness_status != expected_readiness:
                raise ValueError("strategy_factory_formal_readiness_mismatch")
            if expected_readiness == "ready" and blockers:
                raise ValueError("strategy_factory_formal_ready_has_blockers")
            if expected_readiness == "blocked" and not blockers:
                raise ValueError("strategy_factory_formal_blocked_without_reason")
            disposition_ids.add(candidate_id)
            pending.append(
                {
                    **selection,
                    "status": candidate_status,
                    "readinessStatus": readiness_status,
                    "blockers": blockers,
                    "formalHandoffHash": handoff_hash,
                }
            )
    if disposition_ids != set(selected):
        raise ValueError("strategy_factory_formal_disposition_incomplete")
    return pending, {
        "formalHandoffStatus": handoff_status,
        "formalHandoffHash": handoff_hash,
        "formalReadyCandidateCount": len(ready_rows),
        "formalBlockedCandidateCount": len(blocked_rows),
    }


def build_strategy_factory_outcome(
    *,
    run_id: str,
    campaign_id: str,
    candidate_ids: Sequence[str],
    receipt: Mapping[str, Any],
    output_root: Path,
    outcome_root: Path,
    created_at: str,
) -> dict[str, Any]:
    if receipt.get("campaignId") not in (None, "", campaign_id):
        raise ValueError("strategy_factory_receipt_campaign_mismatch")
    configured_candidates = [str(value) for value in candidate_ids]
    releases = _load_releases(
        receipt=receipt,
        campaign_id=campaign_id,
        output_root=output_root,
    )
    formal_validation_candidates, formal_handoff = _load_formal_validation_candidates(
        receipt=receipt,
        campaign_id=campaign_id,
        output_root=output_root,
        configured_candidates=configured_candidates,
    )
    survivors: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for release in releases:
        candidate_id = str(release.get("candidateId") or "").strip()
        release_hash = str(release.get("immutableReleaseHash") or "").strip()
        if candidate_id not in configured_candidates:
            raise ValueError("strategy_factory_release_candidate_mismatch")
        if not release_hash or release_hash in seen_hashes:
            raise ValueError("strategy_factory_release_hash_invalid")
        if (
            bool(release.get("approved"))
            or bool(release.get("demoArm"))
            or int(release.get("orders") or 0)
        ):
            raise ValueError("strategy_factory_release_execution_boundary_crossed")
        seen_hashes.add(release_hash)
        survivors.append(
            {
                "candidateId": candidate_id,
                "trialId": str(release.get("trialId") or ""),
                "outcome": str(release.get("outcome") or ""),
                "immutableReleaseHash": release_hash,
                "status": "pending_human_review",
            }
        )

    survivor_ids = {item["candidateId"] for item in survivors}
    formal_validation_ids = {
        item["candidateId"] for item in formal_validation_candidates
    }
    if survivor_ids & formal_validation_ids:
        raise ValueError("strategy_factory_candidate_disposition_overlap")
    failure_reason = str(receipt.get("status") or "research_not_release_eligible")
    archived = [
        {
            "candidateId": candidate_id,
            "reason": failure_reason if not survivors else "not_release_eligible",
            "status": "archived_research_failure",
        }
        for candidate_id in configured_candidates
        if candidate_id not in survivor_ids
        and candidate_id not in formal_validation_ids
    ]
    requests = []
    for survivor in survivors:
        request_core = {
            "schemaVersion": "strategy_factory_candidate_review_request_v1",
            "requestType": "review_immutable_research_candidate",
            "runId": run_id,
            "campaignId": campaign_id,
            "candidateId": survivor["candidateId"],
            "immutableReleaseHash": survivor["immutableReleaseHash"],
            "requiredConfirmation": (
                "REVIEW_STRATEGY_FACTORY_CANDIDATE "
                + survivor["immutableReleaseHash"]
            ),
            "status": "pending_human_review",
            "approvalRequestActionable": True,
            "automaticApprovalAllowed": False,
            "demoReleaseCreated": False,
            "approvalCount": 0,
            "demoArm": False,
            "orderCount": 0,
            "createdAt": created_at,
        }
        requests.append(
            {
                **request_core,
                "requestHash": _stable_hash(
                    "strategy_factory_candidate_review_request", request_core
                ),
            }
        )

    inventory = {
        "schemaVersion": "strategy_factory_candidate_inventory_v1",
        "runId": run_id,
        "campaignId": campaign_id,
        "candidateCount": len(configured_candidates),
        "survivorCount": len(survivors),
        "formalValidationCandidateCount": len(formal_validation_candidates),
        **formal_handoff,
        "archivedFailureCount": len(archived),
        "survivors": survivors,
        "formalValidationCandidates": formal_validation_candidates,
        "archivedCandidates": archived,
        "createdAt": created_at,
    }
    request_bundle = {
        "schemaVersion": "strategy_factory_candidate_review_requests_v1",
        "runId": run_id,
        "requestCount": len(requests),
        "requests": requests,
        "automaticApprovalAllowed": False,
        "approvalCount": 0,
        "demoArm": False,
        "orderCount": 0,
    }
    archive_bundle = {
        "schemaVersion": "strategy_factory_failure_archive_v1",
        "runId": run_id,
        "campaignId": campaign_id,
        "archivedFailureCount": len(archived),
        "archivedCandidates": archived,
    }
    inventory_path = outcome_root / "candidate_inventory.json"
    request_path = outcome_root / "candidate_review_requests.json"
    archive_path = outcome_root / "failure_archive.json"
    _write_json_atomic(inventory_path, inventory)
    _write_json_atomic(request_path, request_bundle)
    _write_json_atomic(archive_path, archive_bundle)
    summary = {
        "schemaVersion": "strategy_factory_outcome_summary_v1",
        "runId": run_id,
        "campaignId": campaign_id,
        "candidateReviewRequestCount": len(requests),
        "formalValidationCandidateCount": len(formal_validation_candidates),
        **formal_handoff,
        "archivedFailureCount": len(archived),
        "candidateInventoryPath": str(inventory_path),
        "candidateReviewRequestPath": str(request_path),
        "failureArchivePath": str(archive_path),
        "approvalCount": 0,
        "demoArm": False,
        "orderCount": 0,
        "updatedAt": created_at,
    }
    _write_json_atomic(outcome_root / "outcome_summary.json", summary)
    _write_json_atomic(outcome_root / "artifact_manifest.json", _artifact_manifest(outcome_root))
    return summary


def read_strategy_factory_outcome(outcome_root: Path) -> dict[str, Any]:
    path = outcome_root / "outcome_summary.json"
    if not path.is_file():
        return {
            "candidateReviewRequestCount": 0,
            "formalValidationCandidateCount": 0,
            "formalHandoffStatus": None,
            "formalHandoffHash": None,
            "formalReadyCandidateCount": 0,
            "formalBlockedCandidateCount": 0,
            "archivedFailureCount": 0,
            "candidateInventoryPath": None,
            "candidateReviewRequestPath": None,
            "failureArchivePath": None,
        }
    return _read_object(path)
