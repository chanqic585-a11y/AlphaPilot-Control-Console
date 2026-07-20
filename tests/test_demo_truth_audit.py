from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from alphapilot_control_console.demo_truth_audit import generate_demo_truth_audit


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _release(path: Path, release_id: str, candidate_id: str, timeframe: str) -> None:
    payload = {
        "demoReleaseId": release_id,
        "releaseMode": "experimental_override",
        "strategyCandidateId": candidate_id,
        "strategy": {
            "marketDefinition": {
                "instrumentType": "SWAP",
                "settleCurrency": "USDT",
                "timeframe": timeframe,
                "universePolicy": {"mode": "okx_usdt_linear_perpetual_full_market"},
            }
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _runtime_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE AutoExecutionRuntime (
          environment TEXT PRIMARY KEY, desiredEnabled INTEGER, armedProcessId TEXT,
          status TEXT, lastHeartbeatAt TEXT, nextEvaluationAt TEXT,
          pauseReason TEXT, lastError TEXT, updatedAt TEXT
        );
        CREATE TABLE AutoExecutionCheckpoints (
          environment TEXT, releaseId TEXT, timeframe TEXT,
          closedCandleKey TEXT, evaluatedAt TEXT
        );
        CREATE TABLE AutoExecutionEvents (
          eventId INTEGER PRIMARY KEY AUTOINCREMENT, environment TEXT,
          eventType TEXT, payloadJson TEXT, createdAt TEXT
        );
        """
    )
    connection.execute(
        "INSERT INTO AutoExecutionRuntime VALUES (?,?,?,?,?,?,?,?,?)",
        ("okx_demo", 1, None, "disarmed", "2026-07-20T00:00:00Z", None, "process_arm_required", None, "2026-07-20T00:00:00Z"),
    )
    evaluation = {
        "evaluationAudit": {
            "closeSequenceId": "1h:1",
            "evaluatedReleaseCount": 2,
            "marketSummary": {
                "totalInstrumentCount": 100,
                "liquidityEligibleCount": 80,
                "deepScreenCount": 40,
            },
            "matchedSignalCount": 1,
            "orderAttemptCount": 1,
            "createdOrderCount": 1,
            "releaseAudits": [
                {"releaseId": "r1", "strategyId": "c1", "timeframe": "1h", "matchedSignalCount": 1},
                {"releaseId": "r2", "strategyId": "c2", "timeframe": "1h", "matchedSignalCount": 0},
            ],
        },
        "matchedSignalCount": 1,
        "createdOrderCount": 1,
    }
    connection.execute(
        "INSERT INTO AutoExecutionEvents(environment,eventType,payloadJson,createdAt) VALUES (?,?,?,?)",
        ("okx_demo", "heartbeat_completed", json.dumps(evaluation), "2026-07-20T01:00:01Z"),
    )
    connection.execute(
        "INSERT INTO AutoExecutionEvents(environment,eventType,payloadJson,createdAt) VALUES (?,?,?,?)",
        ("okx_demo", "heartbeat_blocked", json.dumps({"blockers": ["demo_runtime_paused"]}), "2026-07-20T01:01:00Z"),
    )
    connection.commit()
    connection.close()


def _universe_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE DemoInstrumentUniverseCache (
        environment TEXT, publicManifestHash TEXT, authenticatedInstrumentHash TEXT,
        projectionJson TEXT, generatedAt TEXT, cacheTtlSeconds INTEGER)"""
    )
    projection = {
        "status": "usable",
        "publicUniverseCount": 100,
        "demoAccountInstrumentCount": 90,
        "intersectionCount": 80,
        "eligibleInstrumentIds": ["BTC-USDT-SWAP", "ETH-USDT-SWAP"],
        "rawPrivatePayloadStored": False,
    }
    connection.execute(
        "INSERT INTO DemoInstrumentUniverseCache VALUES (?,?,?,?,?,?)",
        ("demo", "public_hash", "auth_hash", json.dumps(projection), "2026-07-20T00:00:00Z", 300),
    )
    connection.commit()
    connection.close()


def test_truth_audit_is_read_only_redacted_and_projects_legacy_releases(tmp_path: Path) -> None:
    releases = tmp_path / "releases"
    releases.mkdir()
    _release(releases / "r1.json", "r1", "c1", "1h")
    _release(releases / "r2.json", "r2", "c2", "1h")
    before = {path.name: _sha(path) for path in releases.iterdir()}
    runtime = tmp_path / "runtime.sqlite"
    universe = tmp_path / "universe.sqlite"
    _runtime_db(runtime)
    _universe_db(universe)

    result = generate_demo_truth_audit(
        release_dir=releases,
        runtime_db=runtime,
        universe_db=universe,
        output_dir=tmp_path / "out",
        credential_metadata={"supported": True, "stored": True, "status": "stored"},
        process_credential_injected=False,
        private_read_evidence={
            "status": "blocked_demo_credentials_not_injected",
            "networkRequestMade": False,
        },
        generated_at="2026-07-20T00:00:00Z",
    )

    assert result["legacyReleaseCount"] == 2
    assert before == {path.name: _sha(path) for path in releases.iterdir()}
    credential = json.loads((tmp_path / "out" / "demo_credential_source_audit.json").read_text())
    assert credential["credentialSource"] == "windows_credential_manager"
    assert credential["rawCredentialFilePersisted"] is False
    assert credential["rawCredentialDatabasePersisted"] is False
    assert "apiKey" not in json.dumps(credential)

    inventory = (tmp_path / "out" / "legacy_demo_release_inventory.csv").read_text(encoding="utf-8-sig")
    assert "legacy_experimental_override" in inventory
    assert "False" in inventory


def test_funnel_and_blockers_preserve_runtime_truth(tmp_path: Path) -> None:
    releases = tmp_path / "releases"
    releases.mkdir()
    _release(releases / "r1.json", "r1", "c1", "1h")
    runtime = tmp_path / "runtime.sqlite"
    universe = tmp_path / "universe.sqlite"
    _runtime_db(runtime)
    _universe_db(universe)

    generate_demo_truth_audit(
        release_dir=releases,
        runtime_db=runtime,
        universe_db=universe,
        output_dir=tmp_path / "out",
        credential_metadata={"supported": True, "stored": False, "status": "missing"},
        process_credential_injected=False,
        private_read_evidence=None,
        generated_at="2026-07-20T00:00:00Z",
    )

    funnel = (tmp_path / "out" / "release_scan_funnel.csv").read_text(encoding="utf-8-sig")
    assert "heartbeat_completed" in funnel
    assert ",100,80,40,1,1,1," in funnel
    blockers = (tmp_path / "out" / "demo_runtime_blocker_matrix.csv").read_text(encoding="utf-8-sig")
    assert "demo_runtime_paused" in blockers
    truth = json.loads((tmp_path / "out" / "demo_runtime_truth_audit.json").read_text())
    assert truth["runtime"]["status"] == "disarmed"
    assert truth["latestCompletedBatch"]["evaluatedReleaseCount"] == 2
