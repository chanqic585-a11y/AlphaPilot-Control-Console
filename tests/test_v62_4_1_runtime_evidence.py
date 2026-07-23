from __future__ import annotations

import sqlite3

import pytest

from alphapilot_control_console.v62_4_1_runtime_evidence import (
    build_broad_universe_audit,
    build_historical_shadow_parity,
    build_no_order_runtime_capture,
    build_zero_state_reconciliation,
    online_backup_sqlite,
)


def _heartbeat(
    *,
    timeframe: str,
    evaluated_release_count: int,
    market_count: int,
    liquidity_count: int,
    deep_count: int,
    matched_count: int = 0,
) -> dict[str, object]:
    return {
        "eventId": f"{timeframe}-event",
        "createdAt": "2026-07-22T10:00:08+00:00",
        "payload": {
            "closeSequenceId": f"{timeframe}:1784710800000",
            "evaluatedReleaseCount": evaluated_release_count,
            "matchedSignalCount": matched_count,
            "createdOrderCount": 0,
            "evaluationAudit": {
                "conservationPassed": True,
                "evaluatedReleaseCount": evaluated_release_count,
                "matchedSignalCount": matched_count,
                "createdOrderCount": 0,
                "orderAttemptCount": 0,
                "releaseAudits": [
                    {
                        "releaseId": f"{timeframe}-release-{index}",
                        "timeframe": timeframe,
                        "deepScreenCompleted": deep_count // evaluated_release_count,
                        "deepScreenRequired": deep_count // evaluated_release_count,
                        "matchedSignalCount": 0,
                    }
                    for index in range(evaluated_release_count)
                ],
                "funnel": {
                    "marketInstrumentCount": market_count,
                    "liquidityEligibleInstrumentCount": liquidity_count,
                    "componentInstrumentEvaluationCount": deep_count,
                    "matchedSignalCount": matched_count,
                    "demoTradableSignalCount": 0,
                    "arbitratedSignalCount": 0,
                    "latencyPassedSignalCount": 0,
                    "orderAttemptCount": 0,
                    "orderAcceptedCount": 0,
                    "filledOrderCount": 0,
                },
            },
        },
    }


def test_no_order_runtime_capture_has_no_execution_authority() -> None:
    result = build_no_order_runtime_capture(
        repository_commit="a" * 40,
        repository_tag="v13.27.1.62.4.1",
        module_hashes={"runtime.py": "sha256:" + "b" * 64},
        process_id=4312,
        captured_at="2026-07-23T08:00:00+00:00",
        source_runtime_online=False,
        source_runtime_rows=[
            {
                "environment": "okx_demo",
                "desiredEnabled": 1,
                "armedProcessId": None,
                "status": "disarmed",
                "pauseReason": "process_arm_required",
                "lastError": None,
            }
        ],
        active_execution_leases=[],
        observation_lease={
            "leaseId": "observation-v62-4-1",
            "leaseClass": "read_only_observation",
        },
    )

    assert result["status"] == "captured_no_order_observation"
    assert result["runtimeIdentity"]["repositoryCommit"] == "a" * 40
    assert result["runtimeIdentity"]["repositoryTag"] == "v13.27.1.62.4.1"
    assert result["runtimeIdentity"]["moduleHashes"]["runtime.py"].startswith("sha256:")
    assert result["runtimeIdentity"]["processId"] == 4312
    assert result["sourceRuntimeOnline"] is False
    assert result["executionAuthority"] is False
    assert result["newEntriesAllowed"] is False
    assert result["demoArm"] is False
    assert result["liveEnabled"] is False
    assert result["withdrawEnabled"] is False
    assert result["orderAttemptCount"] == 0
    assert result["activeExecutionLeaseCount"] == 0
    assert result["observationLease"]["exclusiveWriteAuthority"] is False


def test_no_order_runtime_capture_rejects_an_active_execution_lease() -> None:
    with pytest.raises(PermissionError, match="execution lease"):
        build_no_order_runtime_capture(
            repository_commit="a" * 40,
            repository_tag="v13.27.1.62.4.1",
            module_hashes={"runtime.py": "sha256:" + "b" * 64},
            process_id=4312,
            captured_at="2026-07-23T08:00:00+00:00",
            source_runtime_online=False,
            source_runtime_rows=[],
            active_execution_leases=[
                {
                    "environment": "okx_demo",
                    "ownerId": "production-runtime",
                }
            ],
            observation_lease={
                "leaseId": "observation-v62-4-1",
                "leaseClass": "read_only_observation",
            },
        )


def test_historical_shadow_parity_requires_real_1h_and_1d_batches() -> None:
    result = build_historical_shadow_parity(
        [
            _heartbeat(
                timeframe="1h",
                evaluated_release_count=1,
                market_count=426,
                liquidity_count=378,
                deep_count=7,
            ),
            _heartbeat(
                timeframe="1d",
                evaluated_release_count=5,
                market_count=423,
                liquidity_count=384,
                deep_count=255,
            ),
        ],
        expected_timeframes=("1h", "1d"),
    )

    assert result["status"] == "passed"
    assert result["parityRate"] == 1.0
    assert result["timeframesCovered"] == ["1d", "1h"]
    assert result["orderAccessDisabled"] is True
    assert result["orderAttemptCount"] == 0
    assert result["createdOrderCount"] == 0
    assert result["cutoverPerformed"] is False


def test_historical_shadow_parity_does_not_accept_missing_1d() -> None:
    result = build_historical_shadow_parity(
        [
            _heartbeat(
                timeframe="1h",
                evaluated_release_count=1,
                market_count=426,
                liquidity_count=378,
                deep_count=7,
            )
        ],
        expected_timeframes=("1h", "1d"),
    )

    assert result["status"] == "blocked_missing_timeframe_evidence"
    assert result["missingTimeframes"] == ["1d"]
    assert result["cutoverEligible"] is False


def test_historical_shadow_parity_accepts_legacy_event_after_independent_recompute() -> None:
    event = _heartbeat(
        timeframe="1d",
        evaluated_release_count=5,
        market_count=423,
        liquidity_count=384,
        deep_count=255,
    )
    del event["payload"]["evaluationAudit"]["conservationPassed"]  # type: ignore[index]

    result = build_historical_shadow_parity(
        [event],
        expected_timeframes=("1d",),
    )

    assert result["status"] == "passed"
    assert result["events"][0]["recordedConservationStatus"] == "legacy_absent"
    assert result["events"][0]["independentConservationPassed"] is True


def test_zero_state_reconciliation_is_historical_and_does_not_claim_live_rest_ws() -> None:
    result = build_zero_state_reconciliation(
        runtime_rows=[
            {
                "environment": "okx_demo",
                "status": "disarmed",
                "armedProcessId": None,
                "lastError": None,
                "updatedAt": "2026-07-22T23:13:22+00:00",
            }
        ],
        execution_records=[
            {
                "recordId": "record-1",
                "status": "rejected",
                "exchangeOrderId": None,
                "updatedAt": "2026-07-16T01:00:00+00:00",
            }
        ],
        account_snapshot={
            "source": "historical_sanitized_snapshot",
            "updatedAt": "2026-07-22T10:18:52+00:00",
            "positionCount": 0,
            "unknownOrderCount": 0,
            "partiallyFilledOrderCount": 0,
        },
    )

    assert result["status"] == "passed_historical_zero_state"
    assert result["currentPrivateRestWsStatus"] == "not_run_no_credentials"
    assert result["openPositionCount"] == 0
    assert result["unknownOrderCount"] == 0
    assert result["partiallyFilledOrderCount"] == 0
    assert result["newEntriesAllowed"] is False


def test_broad_universe_audit_keeps_short_observation_span_blocked() -> None:
    observations = [
        {
            "timestamp": "2026-07-13T00:00:00+00:00",
            "symbol": "BTC-USDT-SWAP",
            "timeframe": "1h",
            "signalMatched": 1,
            "wouldAttemptDemoOrder": 1,
        },
        {
            "timestamp": "2026-07-22T10:00:00+00:00",
            "symbol": "ETH-USDT-SWAP",
            "timeframe": "1h",
            "signalMatched": 0,
            "wouldAttemptDemoOrder": 0,
        },
    ]
    result = build_broad_universe_audit(
        observations=observations,
        heartbeat_events=[
            _heartbeat(
                timeframe="1h",
                evaluated_release_count=1,
                market_count=426,
                liquidity_count=378,
                deep_count=7,
            )
        ],
        as_of="2026-07-23T00:00:00+00:00",
    )

    assert result["source"] == "recorded_runtime_evidence"
    assert result["broadUniverse"]["maximumObservedMarketInstrumentCount"] == 426
    assert result["windows"]["30d"]["observationCount"] == 2
    assert result["windows"]["90d"]["observationCount"] == 2
    assert result["windows"]["30d"]["matchedSignalCount"] == 1
    assert result["observedSpanDays"] < 30
    assert result["status"] == "blocked_insufficient_observation_span"
    assert result["acceptedAs30d90dMatchability"] is False


def test_online_backup_sqlite_copies_a_consistent_database(tmp_path) -> None:
    source = tmp_path / "source.sqlite"
    destination = tmp_path / "snapshot.sqlite"
    connection = sqlite3.connect(source)
    connection.execute("create table Evidence(id integer primary key, value text)")
    connection.execute("insert into Evidence(value) values ('one')")
    connection.commit()
    connection.close()

    receipt = online_backup_sqlite(source, destination)

    snapshot = sqlite3.connect(f"file:{destination.as_posix()}?mode=ro", uri=True)
    assert snapshot.execute("pragma integrity_check").fetchone()[0] == "ok"
    assert snapshot.execute("select count(*) from Evidence").fetchone()[0] == 1
    snapshot.close()
    assert receipt["integrityCheck"] == "ok"
    assert receipt["sha256"].startswith("sha256:")
    assert receipt["tableCounts"] == {"Evidence": 1}
