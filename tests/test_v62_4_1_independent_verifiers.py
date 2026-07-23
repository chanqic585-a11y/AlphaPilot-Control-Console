from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from alphapilot_control_console.v62_4_1_independent_verifiers import (
    canonical_hash,
    verify_ai_orchestration,
    verify_artifact_manifest,
    verify_runtime_evidence,
    verify_sqlite_snapshots,
    verify_trial_evidence,
    verify_ui_projection,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _with_artifact_hash(payload: dict[str, object]) -> dict[str, object]:
    result = dict(payload)
    result["artifactHash"] = canonical_hash(result)
    return result


def test_sqlite_verifier_opens_snapshot_and_recomputes_receipt(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.sqlite"
    connection = sqlite3.connect(snapshot)
    connection.execute("CREATE TABLE Events (sequenceId INTEGER PRIMARY KEY, status TEXT)")
    connection.executemany(
        "INSERT INTO Events(sequenceId, status) VALUES (?, ?)",
        [(1, "ok"), (2, "ok")],
    )
    connection.commit()
    connection.close()
    digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    receipt = [
        {
            "sourcePath": "source.sqlite",
            "snapshotPath": str(snapshot),
            "sizeBytes": snapshot.stat().st_size,
            "sha256": f"sha256:{digest}",
            "integrityCheck": "ok",
            "tableCounts": {"Events": 2},
        }
    ]
    receipt_path = tmp_path / "sqlite_backup_receipts.json"
    _write_json(receipt_path, receipt)

    passed = verify_sqlite_snapshots(receipt_path)
    assert passed["passed"] is True
    assert passed["snapshots"][0]["tableCounts"] == {"Events": 2}
    assert passed["snapshots"][0]["maxSequenceByTable"] == {"Events": 2}

    receipt[0]["tableCounts"] = {"Events": 3}
    _write_json(receipt_path, receipt)
    failed = verify_sqlite_snapshots(receipt_path)
    assert failed["passed"] is False
    assert "table_count_mismatch:Events" in failed["snapshots"][0]["findings"]


def test_runtime_verifier_recomputes_hashes_and_rejects_execution_authority(
    tmp_path: Path,
) -> None:
    identity = {
        "repositoryCommit": "a" * 40,
        "repositoryTag": "v-test",
        "moduleHashes": {"runtime.py": "sha256:" + "b" * 64},
        "processId": 42,
        "capturedAt": "2026-07-23T00:00:00Z",
        "processRole": "v62_4_1_no_order_observer",
    }
    capture = _with_artifact_hash(
        {
            "schemaVersion": "v62_4_1_no_order_runtime_capture_v1",
            "status": "captured_no_order_observation",
            "runtimeIdentity": identity,
            "runtimeIdentityHash": canonical_hash(identity),
            "sourceRuntimeOnline": False,
            "sourceRuntimeStates": [
                {
                    "environment": "okx_demo",
                    "status": "disarmed",
                    "desiredEnabled": True,
                },
                {
                    "environment": "okx_live",
                    "status": "disabled",
                    "desiredEnabled": False,
                },
            ],
            "activeExecutionLeaseCount": 0,
            "observationLease": {
                "leaseClass": "read_only_observation",
                "executionAuthority": False,
                "exclusiveWriteAuthority": False,
            },
            "executionAuthority": False,
            "newEntriesAllowed": False,
            "demoArm": False,
            "liveEnabled": False,
            "withdrawEnabled": False,
            "orderAttemptCount": 0,
        }
    )
    parity = _with_artifact_hash(
        {
            "schemaVersion": "v62_4_1_historical_shadow_parity_v1",
            "status": "passed",
            "timeframesCovered": ["1d", "1h"],
            "missingTimeframes": [],
            "parityRate": 1.0,
            "events": [
                {
                    "timeframe": timeframe,
                    "passed": True,
                    "independentConservationPassed": True,
                    "orderAttemptCount": 0,
                    "createdOrderCount": 0,
                }
                for timeframe in ("1d", "1h")
            ],
            "orderAccessDisabled": True,
            "orderAttemptCount": 0,
            "createdOrderCount": 0,
            "cutoverPerformed": False,
        }
    )
    zero_state = _with_artifact_hash(
        {
            "schemaVersion": "v62_4_1_zero_state_reconciliation_v1",
            "status": "passed_historical_zero_state",
            "unknownOrderCount": 0,
            "partiallyFilledOrderCount": 0,
            "openPositionCount": 0,
            "unresolvedExecutionRecordIds": [],
            "newEntriesAllowed": False,
            "demoArm": False,
            "liveEnabled": False,
            "withdrawEnabled": False,
        }
    )
    summary = _with_artifact_hash(
        {
            "schemaVersion": "v62_4_1_runtime_evidence_bundle_v1",
            "runtimeCaptureStatus": "captured_no_order_observation",
            "historicalShadowParityStatus": "passed",
            "zeroStateReconciliationStatus": "passed_historical_zero_state",
            "sourceRuntimeOnline": False,
            "newEntriesAllowed": False,
            "demoArm": False,
            "liveEnabled": False,
            "withdrawEnabled": False,
            "orderAttemptCount": 0,
        }
    )
    _write_json(tmp_path / "runtime_identity_capture.json", capture)
    _write_json(tmp_path / "historical_shadow_parity_1h_1d.json", parity)
    _write_json(tmp_path / "zero_state_reconciliation.json", zero_state)
    _write_json(tmp_path / "runtime_evidence_summary.json", summary)

    assert verify_runtime_evidence(tmp_path)["passed"] is True

    capture["executionAuthority"] = True
    capture["artifactHash"] = canonical_hash(
        {key: value for key, value in capture.items() if key != "artifactHash"}
    )
    _write_json(tmp_path / "runtime_identity_capture.json", capture)
    failed = verify_runtime_evidence(tmp_path)
    assert failed["passed"] is False
    assert "execution_authority_present" in failed["findings"]


def test_trial_verifier_recomputes_candidate_trial_and_formal_counts(
    tmp_path: Path,
) -> None:
    candidate_ids = ["candidate-a", "candidate-b"]
    preregistration = {
        "campaignId": "campaign-1",
        "candidateCount": 2,
        "candidateIds": candidate_ids,
        "trialCount": 4,
        "trialsByCandidate": {
            candidate_id: [
                {"trialId": f"{candidate_id}-1"},
                {"trialId": f"{candidate_id}-2"},
            ]
            for candidate_id in candidate_ids
        },
        "lockedOosReadCount": 0,
    }
    campaign_summary = {
        "campaignId": "campaign-1",
        "candidateCount": 2,
        "trialCount": 4,
        "completedTrialCount": 4,
        "stableSelectionCount": 2,
        "formalReadyCandidateCount": 1,
        "formalBlockedCandidateCount": 1,
        "formalRunCount": 0,
        "resultReadCount": 0,
        "releaseCount": 0,
        "approvalCount": 0,
        "orderCount": 0,
        "demoArm": False,
    }
    projections = {
        "campaignId": "campaign-1",
        "projectionCount": 4,
        "projections": [
            {"candidateId": candidate_id, "trialId": f"{candidate_id}-{index}"}
            for candidate_id in candidate_ids
            for index in (1, 2)
        ],
    }
    handoff = {
        "campaignId": "campaign-1",
        "selectedCandidateCount": 2,
        "formalReadyCandidateCount": 1,
        "blockedCandidateCount": 1,
        "readyCandidates": [{"candidateId": "candidate-a"}],
        "blockedCandidates": [{"candidateId": "candidate-b"}],
        "formalRunCount": 0,
        "resultReadCount": 0,
        "releaseCount": 0,
        "approvalCount": 0,
        "orderCount": 0,
        "demoArm": False,
    }
    formal_route = {
        "campaignId": "campaign-1",
        "formalRunCount": 0,
        "resultReadCount": 0,
        "releaseCount": 0,
        "approvalCount": 0,
        "orderCount": 0,
        "demoArm": False,
        "formalOutcomes": [],
        "immutableReleases": [],
    }
    for filename, payload in {
        "preregistration.json": preregistration,
        "campaign_summary.json": campaign_summary,
        "development_projection.json": projections,
        "formal_handoff.json": handoff,
        "formal_route.json": formal_route,
    }.items():
        _write_json(tmp_path / filename, payload)

    assert verify_trial_evidence(tmp_path)["passed"] is True

    campaign_summary["trialCount"] = 5
    _write_json(tmp_path / "campaign_summary.json", campaign_summary)
    failed = verify_trial_evidence(tmp_path)
    assert failed["passed"] is False
    assert "campaign_trial_count_mismatch" in failed["findings"]


def test_ai_verifier_checks_real_router_registry_and_execution_boundaries(
    tmp_path: Path,
) -> None:
    smoke = {
        "status": "provider_smoke_passed",
        "providers": {
            "deepseek": {"status": "accepted"},
            "gemini": {"status": "accepted"},
            "dual": {"status": "accepted"},
        },
        "executionAuthority": False,
        "exchangePrivateCredentialsPresent": False,
        "demoArm": False,
        "liveArm": False,
        "withdrawEnabled": False,
    }
    smoke_path = tmp_path / "provider_smoke_summary.json"
    _write_json(smoke_path, smoke)
    repository_root = Path(__file__).resolve().parents[1]

    passed = verify_ai_orchestration(repository_root, smoke_path)
    assert passed["passed"] is True
    assert passed["routeMatrix"]["strategy_hypothesis"]["mode"] == "dual"
    assert passed["forbiddenTaskChecks"]["order_submission"] == "blocked"
    assert passed["directProviderImports"] == []
    assert passed["executionPathAiImports"] == []

    smoke["executionAuthority"] = True
    _write_json(smoke_path, smoke)
    failed = verify_ai_orchestration(repository_root, smoke_path)
    assert failed["passed"] is False
    assert "provider_smoke_has_execution_authority" in failed["findings"]


def test_ui_verifier_checks_current_pilot_fields_and_authority() -> None:
    pilot = {
        "authority": "current_v62_4_pilot",
        "campaignId": "campaign-1",
        "candidateCount": 4,
        "trialCount": 12,
        "stableSelectionCount": 2,
        "formalReadyCandidateCount": 1,
        "formalBlockedCandidateCount": 1,
        "formalRunCount": 0,
        "resultReadCount": 0,
    }
    payload = {"strategy": {"currentPilot": pilot}}
    html = " ".join(
        [
            'id="strategyCurrentPilot"',
            'id="strategyPilotCampaign"',
            'id="strategyPilotCandidateTrials"',
            'id="strategyPilotStable"',
            'id="strategyPilotFormalReady"',
            'id="strategyPilotFormalBlocked"',
        ]
    )
    passed = verify_ui_projection(payload, html, expected_campaign_id="campaign-1")
    assert passed["passed"] is True

    payload["strategy"]["currentPilot"]["authority"] = "historical_release"
    failed = verify_ui_projection(payload, html, expected_campaign_id="campaign-1")
    assert failed["passed"] is False
    assert "current_pilot_authority_mismatch" in failed["findings"]


def test_hash_verifier_recomputes_each_manifest_entry(tmp_path: Path) -> None:
    artifact = tmp_path / "evidence" / "summary.json"
    _write_json(artifact, {"status": "passed"})
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest_path = tmp_path / "artifact_manifest.json"
    _write_json(
        manifest_path,
        {
            "artifacts": [
                {
                    "relativePath": "evidence/summary.json",
                    "sizeBytes": artifact.stat().st_size,
                    "sha256": f"sha256:{digest}",
                }
            ]
        },
    )

    assert verify_artifact_manifest(tmp_path, manifest_path)["passed"] is True

    artifact.write_text('{"status":"tampered"}\n', encoding="utf-8")
    failed = verify_artifact_manifest(tmp_path, manifest_path)
    assert failed["passed"] is False
    assert failed["artifacts"][0]["status"] == "hash_mismatch"


def test_hash_verifier_accepts_acceptance_handoff_list_manifest(tmp_path: Path) -> None:
    artifact = tmp_path / "evidence" / "summary.json"
    _write_json(artifact, {"status": "passed"})
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest_path = tmp_path / "artifact_manifest.json"
    _write_json(
        manifest_path,
        [
            {
                "relativePath": "evidence/summary.json",
                "sizeBytes": artifact.stat().st_size,
                "sha256": digest,
            }
        ],
    )

    result = verify_artifact_manifest(tmp_path, manifest_path)

    assert result["passed"] is True
    assert result["artifacts"][0]["status"] == "verified"
