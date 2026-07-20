from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from alphapilot_control_console.strategy_validation_hashing import stable_hash
from alphapilot_control_console.top200_policy_bound_release import (
    RELEASE_FILE,
    build_policy_bound_release,
    write_policy_bound_release_artifacts,
)


def _source_release() -> dict:
    return {
        "schemaVersion": "provisional_research_demo_v1",
        "releaseId": "old-release",
        "releaseHash": "old-release-hash",
        "releasePurpose": "provisional_research_demo",
        "route": "blocked_waiting_exact_release_approval",
        "approvalRequired": True,
        "approved": False,
        "demoArm": False,
        "formalPass": False,
        "cleanHistoricalOosPass": False,
        "livePromotionEligible": False,
        "automaticLivePromotionAllowed": False,
        "riskOverlayHash": "risk-hash",
        "executionIntersectionHash": "intersection-hash",
        "dynamicUniversePolicyId": "top200-policy",
        "dynamicUniversePolicyHash": "policy-hash",
        "dynamicUniverseSnapshotHash": "snapshot-hash",
        "dynamicUniverseSnapshotUtcDate": "2026-07-20",
        "executionInstruments": ["BTC-USDT-SWAP", "ETH-USDT-SWAP"],
        "actualInstrumentCount": 2,
        "maximumInstrumentCount": 200,
    }


def _source_request() -> dict:
    return {
        "schemaVersion": "provisional_demo_exact_release_approval_request_v1",
        "requestType": "exact_provisional_research_demo_release_approval",
        "releaseId": "old-release",
        "releaseHash": "old-release-hash",
        "riskOverlayHash": "risk-hash",
        "executionIntersectionHash": "intersection-hash",
        "engineeringSmokeEvidenceHash": "smoke-evidence-hash",
        "engineeringSmokeContractHash": "smoke-contract-hash",
        "approvalGranted": False,
        "approved": False,
        "demoArm": False,
        "route": "blocked_waiting_exact_release_approval",
        "status": "blocked_waiting_exact_release_approval",
        "strategyOrderCount": 0,
        "orderCount": 0,
        "live": False,
        "withdraw": False,
        "generatedAt": "2026-07-20T00:00:00Z",
        "approvalChallenge": "old",
        "requestHash": "old-request-hash",
    }


def test_builds_final_policy_bound_release_without_mutating_sources() -> None:
    release = _source_release()
    request = _source_request()
    before_release = json.dumps(release, sort_keys=True)
    before_request = json.dumps(request, sort_keys=True)

    result = build_policy_bound_release(
        source_release=release,
        source_approval_request=request,
        generated_at="2026-07-21T00:00:00Z",
    )

    final_release = result["release"]
    final_request = result["approvalRequest"]
    assert json.dumps(release, sort_keys=True) == before_release
    assert json.dumps(request, sort_keys=True) == before_request
    assert final_release["snapshotBindingMode"] == "policy_bound_daily_snapshot"
    assert final_release["activationSnapshotHash"] == "snapshot-hash"
    assert final_release["executionInstrumentsAreActivationSnapshotOnly"] is True
    assert final_release["supersedesReleaseId"] == "old-release"
    assert final_release["supersedesReleaseHash"] == "old-release-hash"
    assert final_release["releaseId"] != "old-release"
    assert final_request["releaseId"] == final_release["releaseId"]
    assert final_request["releaseHash"] == final_release["releaseHash"]
    assert final_request["riskOverlayHash"] == "risk-hash"

    expected_release_hash = stable_hash(
        {key: value for key, value in final_release.items() if key != "releaseHash"},
        "provisional_demo_release",
    )
    expected_request_hash = stable_hash(
        {key: value for key, value in final_request.items() if key != "requestHash"},
        "exact_release_approval_request",
    )
    assert final_release["releaseHash"] == expected_release_hash
    assert final_request["requestHash"] == expected_request_hash
    assert result["hashAudit"]["status"] == "passed"


def test_writes_manifested_release_artifacts(tmp_path: Path) -> None:
    result = build_policy_bound_release(
        source_release=_source_release(),
        source_approval_request=_source_request(),
        generated_at="2026-07-21T00:00:00Z",
    )

    manifest = write_policy_bound_release_artifacts(tmp_path, result)

    assert manifest["artifactCount"] == 3
    assert {path.name for path in tmp_path.iterdir()} == {
        "final_superseding_provisional_release.json",
        "final_demo_approval_request.json",
        "final_release_hash_audit.json",
        "release_artifact_manifest.json",
    }
    assert len(manifest["artifacts"]) == 3


def test_builder_script_preserves_sources_and_writes_successor(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    release_path = tmp_path / "source_release.json"
    request_path = tmp_path / "source_request.json"
    release_path.write_text(json.dumps(_source_release()), encoding="utf-8")
    request_path.write_text(json.dumps(_source_request()), encoding="utf-8")
    release_before = release_path.read_bytes()
    request_before = request_path.read_bytes()
    output = tmp_path / "output"

    completed = subprocess.run(
        [
            sys.executable,
            str(repository_root / "scripts" / "build_top200_policy_bound_release.py"),
            "--release",
            str(release_path),
            "--approval-request",
            str(request_path),
            "--generated-at",
            "2026-07-21T00:00:00Z",
            "--output",
            str(output),
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert release_path.read_bytes() == release_before
    assert request_path.read_bytes() == request_before
    payload = json.loads((output / RELEASE_FILE).read_text(encoding="utf-8"))
    assert payload["snapshotBindingMode"] == "policy_bound_daily_snapshot"
