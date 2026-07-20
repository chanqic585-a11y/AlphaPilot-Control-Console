"""Build the final policy-bound successor to the frozen TOP200 Demo release."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .strategy_validation_hashing import canonical_bytes, stable_hash


RELEASE_FILE = "final_superseding_provisional_release.json"
APPROVAL_REQUEST_FILE = "final_demo_approval_request.json"
HASH_AUDIT_FILE = "final_release_hash_audit.json"
MANIFEST_FILE = "release_artifact_manifest.json"


def _without(payload: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    excluded = set(keys)
    return {key: value for key, value in payload.items() if key not in excluded}


def _release_id(source_release: Mapping[str, Any]) -> str:
    identity = {
        "supersedesReleaseHash": source_release.get("releaseHash"),
        "dynamicUniversePolicyHash": source_release.get("dynamicUniversePolicyHash"),
        "snapshotBindingMode": "policy_bound_daily_snapshot",
    }
    digest = stable_hash(identity).split("_", 1)[-1][:24]
    return f"provisional_research_demo_top200_policy_bound_{digest}"


def build_policy_bound_release(
    *,
    source_release: Mapping[str, Any],
    source_approval_request: Mapping[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Return new release/request objects without mutating the frozen sources."""
    release = _without(source_release, "releaseHash")
    release.update(
        {
            "releaseId": _release_id(source_release),
            "snapshotBindingMode": "policy_bound_daily_snapshot",
            "activationSnapshotHash": source_release.get("dynamicUniverseSnapshotHash"),
            "activationSnapshotUtcDate": source_release.get(
                "dynamicUniverseSnapshotUtcDate"
            ),
            "executionInstrumentsAreActivationSnapshotOnly": True,
            "dailySnapshotRequiresNewRelease": False,
            "supersedesReleaseId": source_release.get("releaseId"),
            "supersedesReleaseHash": source_release.get("releaseHash"),
            "generatedAt": generated_at,
            "route": "blocked_waiting_exact_release_approval",
            "approvalRequired": True,
            "approved": False,
            "demoArm": False,
            "livePromotionEligible": False,
            "automaticLivePromotionAllowed": False,
        }
    )
    release["releaseHash"] = stable_hash(release, "provisional_demo_release")

    request = _without(
        source_approval_request,
        "requestHash",
        "approvalRequestHash",
    )
    request.update(
        {
            "releaseId": release["releaseId"],
            "releaseHash": release["releaseHash"],
            "riskOverlayHash": release.get("riskOverlayHash"),
            "executionIntersectionHash": release.get("executionIntersectionHash"),
            "generatedAt": generated_at,
            "approvalChallenge": stable_hash(
                {
                    "releaseHash": release["releaseHash"],
                    "riskOverlayHash": release.get("riskOverlayHash"),
                    "executionIntersectionHash": release.get(
                        "executionIntersectionHash"
                    ),
                },
                "exact_release_approval_challenge",
            ),
            "approvalGranted": False,
            "approved": False,
            "demoArm": False,
            "route": "blocked_waiting_exact_release_approval",
            "status": "blocked_waiting_exact_release_approval",
            "strategyOrderCount": 0,
            "orderCount": 0,
            "live": False,
            "withdraw": False,
        }
    )
    request["requestHash"] = stable_hash(
        request,
        "exact_release_approval_request",
    )

    expected_release_hash = stable_hash(
        _without(release, "releaseHash"),
        "provisional_demo_release",
    )
    expected_request_hash = stable_hash(
        _without(request, "requestHash"),
        "exact_release_approval_request",
    )
    hash_audit = {
        "schemaVersion": "top200_policy_bound_release_hash_audit_v1",
        "status": "passed"
        if release["releaseHash"] == expected_release_hash
        and request["requestHash"] == expected_request_hash
        else "failed",
        "releaseId": release["releaseId"],
        "releaseHash": release["releaseHash"],
        "expectedReleaseHash": expected_release_hash,
        "approvalRequestHash": request["requestHash"],
        "expectedApprovalRequestHash": expected_request_hash,
        "sourceReleaseId": source_release.get("releaseId"),
        "sourceReleaseHash": source_release.get("releaseHash"),
        "snapshotBindingMode": release["snapshotBindingMode"],
        "generatedAt": generated_at,
    }
    return {
        "release": release,
        "approvalRequest": request,
        "hashAudit": hash_audit,
    }


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(canonical_bytes(payload) + b"\n")
    temporary.replace(path)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_policy_bound_release_artifacts(
    output_dir: Path | str,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Write a new artifact set; callers choose an empty successor directory."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    payloads = (
        (RELEASE_FILE, result["release"]),
        (APPROVAL_REQUEST_FILE, result["approvalRequest"]),
        (HASH_AUDIT_FILE, result["hashAudit"]),
    )
    for name, payload in payloads:
        _atomic_write(output / name, payload)

    artifacts = [
        {
            "path": name,
            "sha256": _file_sha256(output / name),
            "sizeBytes": (output / name).stat().st_size,
        }
        for name, _ in payloads
    ]
    manifest = {
        "schemaVersion": "top200_policy_bound_release_artifact_manifest_v1",
        "artifactCount": len(artifacts),
        "releaseId": result["release"]["releaseId"],
        "releaseHash": result["release"]["releaseHash"],
        "approvalRequestHash": result["approvalRequest"]["requestHash"],
        "artifacts": artifacts,
    }
    _atomic_write(output / MANIFEST_FILE, manifest)
    return manifest
