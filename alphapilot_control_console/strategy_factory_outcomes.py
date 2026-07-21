from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence


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
    releases = _load_releases(
        receipt=receipt,
        campaign_id=campaign_id,
        output_root=output_root,
    )
    configured_candidates = [str(value) for value in candidate_ids]
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
    failure_reason = str(receipt.get("status") or "research_not_release_eligible")
    archived = [
        {
            "candidateId": candidate_id,
            "reason": failure_reason if not survivors else "not_release_eligible",
            "status": "archived_research_failure",
        }
        for candidate_id in configured_candidates
        if candidate_id not in survivor_ids
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
        "archivedFailureCount": len(archived),
        "survivors": survivors,
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
            "archivedFailureCount": 0,
            "candidateInventoryPath": None,
            "candidateReviewRequestPath": None,
            "failureArchivePath": None,
        }
    return _read_object(path)
