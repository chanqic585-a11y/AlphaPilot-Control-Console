from __future__ import annotations

import json
import runpy
from pathlib import Path

from alphapilot_control_console.v62_4_2_delta_closeout import (
    build_authoritative_closeout_projection,
    build_verifier_scripts,
    classify_matchability_evidence,
    verify_final_runtime_source_identity,
)


def test_runtime_builder_resolves_bundled_git_when_path_has_no_git(
    tmp_path: Path,
) -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "build_v62_4_1_runtime_evidence.py"
    )
    namespace = runpy.run_path(str(script_path))
    bundled_git = (
        tmp_path
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "native"
        / "git"
        / "cmd"
        / "git.exe"
    )
    bundled_git.parent.mkdir(parents=True)
    bundled_git.write_bytes(b"fixture")

    resolved = namespace["_resolve_git_executable"](
        search_path="",
        home=tmp_path,
    )

    assert resolved == str(bundled_git)
from alphapilot_control_console.v62_4_1_independent_verifiers import (
    verify_sqlite_snapshots,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def test_sqlite_verifier_resolves_snapshot_relative_to_receipt(
    tmp_path: Path,
) -> None:
    import hashlib
    import sqlite3

    snapshot = tmp_path / "source_snapshots" / "runtime.sqlite"
    snapshot.parent.mkdir(parents=True)
    connection = sqlite3.connect(snapshot)
    connection.execute("CREATE TABLE Events(id INTEGER PRIMARY KEY, value TEXT)")
    connection.execute("INSERT INTO Events(value) VALUES ('safe')")
    connection.commit()
    connection.close()
    digest = "sha256:" + hashlib.sha256(snapshot.read_bytes()).hexdigest()
    receipts = tmp_path / "sqlite_backup_receipts.json"
    _write_json(
        receipts,
        [
            {
                "sourcePath": "redacted/runtime.sqlite",
                "snapshotPath": "source_snapshots/runtime.sqlite",
                "sizeBytes": snapshot.stat().st_size,
                "sha256": digest,
                "integrityCheck": "ok",
                "tableCounts": {"Events": 1},
            }
        ],
    )

    result = verify_sqlite_snapshots(receipts)

    assert result["passed"] is True
    assert result["snapshots"][0]["snapshotPath"] == str(snapshot.resolve())


def test_matchability_is_truthfully_classified_as_diagnostic_only() -> None:
    result = classify_matchability_evidence(
        {
            "actualInstrumentCount": 82,
            "historicalReplayInstrumentCount": 50,
            "requestedUniverseSize": 200,
            "top200HistoricalReplayStatus": "not_run_snapshot_limited_to_50",
            "successorCandidateId": None,
            "successorDefinitionHash": None,
        }
    )

    assert result["status"] == "matchability_diagnostic_ready"
    assert result["broadUniverseSuccessorStatus"] == (
        "broad_universe_successor_not_created"
    )
    assert result["top200HistoricalPitStatus"] == "top200_historical_pit_not_proven"
    assert result["matchabilityProblemSolved"] is False
    assert result["releaseCount"] == 0
    assert result["orderCount"] == 0


def test_top_level_projection_uses_authoritative_child_evidence() -> None:
    result = build_authoritative_closeout_projection(
        formal={
            "formalRunCount": 1,
            "resultReadCount": 1,
            "candidateId": "v35_tsmom_crypto_adaptation",
            "formalPass": False,
            "route": "archive_s01_current_version",
            "baseMetrics": {
                "profitFactor": 0.4892523859,
                "averageNetR": -0.360215062,
                "maximumDrawdownR": 19.289520256,
                "tradeCount": 36,
            },
        },
        runtime={
            "passed": True,
            "sourceRuntimeOnline": False,
            "privateReconciliationStatus": "not_run_credentials_unavailable",
            "activeExecutionLeaseCount": 0,
        },
        quality={
            "fullTestSuite": "passed",
            "mutationMatrix": "passed",
            "disconnectTests": "passed",
            "playwright": "passed",
        },
        failure_critic={
            "status": "accepted",
            "caseCount": 4,
            "acceptedCaseCount": 4,
        },
        matchability={
            "status": "matchability_diagnostic_ready",
            "broadUniverseSuccessorStatus": (
                "broad_universe_successor_not_created"
            ),
            "top200HistoricalPitStatus": "top200_historical_pit_not_proven",
        },
    )

    assert result["status"] == "v62_4_2_delta_closeout_completed"
    assert result["formal"]["formalRunCount"] == 1
    assert result["formal"]["resultReadCount"] == 1
    assert result["formal"]["formalPass"] is False
    assert result["formal"]["route"] == "archive_s01_current_version"
    assert result["failureCritic"]["caseCount"] == 4
    assert result["runtime"]["privateReconciliationStatus"] == (
        "not_run_credentials_unavailable"
    )
    assert result["releaseCount"] == 0
    assert result["orderCount"] == 0
    assert result["demoArm"] is False
    assert result["liveArm"] is False
    assert result["withdrawEnabled"] is False
    assert result["automaticApproval"] is False


def test_each_delivered_verifier_directly_calls_its_domain_function(
    tmp_path: Path,
) -> None:
    generated = build_verifier_scripts(tmp_path)
    scripts = {path.name: path.read_text(encoding="utf-8") for path in generated}

    assert set(scripts) == {
        "verify_acceptance_package.py",
        "verify_ai_router.py",
        "verify_hashes.py",
        "verify_runtime_identity.py",
        "verify_sqlite_snapshots.py",
        "verify_trial_ledger.py",
        "verify_ui_data_sources.py",
    }
    expected_calls = {
        "verify_acceptance_package.py": "verify_delta_acceptance_package(",
        "verify_ai_router.py": "verify_ai_orchestration(",
        "verify_hashes.py": "verify_artifact_manifest(",
        "verify_runtime_identity.py": "verify_final_runtime_source_identity(",
        "verify_sqlite_snapshots.py": "verify_sqlite_snapshots(",
        "verify_trial_ledger.py": "verify_trial_evidence(",
        "verify_ui_data_sources.py": "verify_ui_endpoint(",
    }
    for filename, call in expected_calls.items():
        assert call in scripts[filename]
        if filename != "verify_acceptance_package.py":
            assert "verify_acceptance_package(" not in scripts[filename]


def test_runtime_identity_checks_commit_tag_modules_and_zero_execution_lease(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    repository = tmp_path / "repository"
    evidence.mkdir()
    repository.mkdir()
    module = repository / "alphapilot_control_console" / "module.py"
    module.parent.mkdir(parents=True)
    module.write_text("VALUE = 1\n", encoding="utf-8")

    import hashlib

    module_hash = "sha256:" + hashlib.sha256(module.read_bytes()).hexdigest()
    identity = {
        "repositoryCommit": "abc123",
        "repositoryTag": "v62.4.2",
        "moduleHashes": {
            "alphapilot_control_console/module.py": module_hash,
        },
    }
    from alphapilot_control_console.v62_4_1_independent_verifiers import canonical_hash

    capture = {
        "runtimeIdentity": identity,
        "runtimeIdentityHash": canonical_hash(identity),
        "executionAuthority": False,
        "activeExecutionLeaseCount": 0,
        "observationLease": {
            "leaseClass": "read_only_observation",
            "executionAuthority": False,
            "exclusiveWriteAuthority": False,
        },
        "newEntriesAllowed": False,
        "demoArm": False,
        "liveEnabled": False,
        "withdrawEnabled": False,
        "orderAttemptCount": 0,
        "status": "captured_no_order_observation",
    }
    summary = {
        "runtimeCaptureStatus": "captured_no_order_observation",
        "historicalShadowParityStatus": "passed",
        "zeroStateReconciliationStatus": "passed_historical_zero_state",
        "newEntriesAllowed": False,
        "demoArm": False,
        "liveEnabled": False,
        "withdrawEnabled": False,
        "orderAttemptCount": 0,
    }
    parity = {
        "status": "passed",
        "parityRate": 1.0,
        "timeframesCovered": ["1h", "1d"],
        "orderAccessDisabled": True,
        "orderAttemptCount": 0,
        "createdOrderCount": 0,
        "events": [
            {
                "timeframe": "1h",
                "passed": True,
                "independentConservationPassed": True,
                "orderAttemptCount": 0,
                "createdOrderCount": 0,
            },
            {
                "timeframe": "1d",
                "passed": True,
                "independentConservationPassed": True,
                "orderAttemptCount": 0,
                "createdOrderCount": 0,
            },
        ],
    }
    zero = {
        "status": "passed_historical_zero_state",
        "newEntriesAllowed": False,
        "demoArm": False,
        "liveEnabled": False,
        "withdrawEnabled": False,
        "unknownOrderCount": 0,
        "partiallyFilledOrderCount": 0,
        "openPositionCount": 0,
        "unresolvedExecutionRecordIds": [],
    }
    for name, payload in (
        ("runtime_identity_capture.json", capture),
        ("runtime_evidence_summary.json", summary),
        ("historical_shadow_parity_1h_1d.json", parity),
        ("zero_state_reconciliation.json", zero),
    ):
        payload["artifactHash"] = canonical_hash(payload)
        _write_json(evidence / name, payload)

    result = verify_final_runtime_source_identity(
        evidence,
        repository,
        expected_commit="abc123",
        expected_tag="v62.4.2",
    )

    assert result["passed"] is True
    assert result["repositoryCommit"] == "abc123"
    assert result["repositoryTag"] == "v62.4.2"
    assert result["moduleHashesVerified"] == 1
    assert result["activeExecutionLeaseCount"] == 0
