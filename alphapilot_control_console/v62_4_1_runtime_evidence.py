from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_no_order_runtime_capture(
    *,
    repository_commit: str,
    repository_tag: str,
    module_hashes: Mapping[str, str],
    process_id: int,
    captured_at: str,
    source_runtime_online: bool,
    source_runtime_rows: Sequence[Mapping[str, object]],
    active_execution_leases: Sequence[Mapping[str, object]],
    observation_lease: Mapping[str, object],
) -> dict[str, object]:
    """Build a read-only capture identity that can never imply execution authority."""

    if active_execution_leases:
        raise PermissionError("no-order capture cannot coexist with an execution lease")
    if observation_lease.get("leaseClass") != "read_only_observation":
        raise ValueError("observation lease must be read_only_observation")
    if not repository_commit or not repository_tag or not module_hashes:
        raise ValueError("repository identity and module hashes are required")

    identity = {
        "repositoryCommit": repository_commit,
        "repositoryTag": repository_tag,
        "moduleHashes": dict(sorted(module_hashes.items())),
        "processId": int(process_id),
        "capturedAt": captured_at,
        "processRole": "v62_4_1_no_order_observer",
    }
    lease = {
        "leaseId": str(observation_lease.get("leaseId") or ""),
        "leaseClass": "read_only_observation",
        "exclusiveWriteAuthority": False,
        "executionAuthority": False,
    }
    capture = {
        "schemaVersion": "v62_4_1_no_order_runtime_capture_v1",
        "status": "captured_no_order_observation",
        "runtimeIdentity": identity,
        "runtimeIdentityHash": _canonical_hash(identity),
        "sourceRuntimeOnline": bool(source_runtime_online),
        "sourceRuntimeStates": [dict(row) for row in source_runtime_rows],
        "activeExecutionLeaseCount": 0,
        "observationLease": lease,
        "executionAuthority": False,
        "newEntriesAllowed": False,
        "demoArm": False,
        "liveEnabled": False,
        "withdrawEnabled": False,
        "orderAttemptCount": 0,
    }
    capture["artifactHash"] = _canonical_hash(capture)
    return capture


def _event_timeframe(event: Mapping[str, object]) -> str:
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        return ""
    sequence = str(payload.get("closeSequenceId") or "")
    return sequence.split(":", 1)[0] if ":" in sequence else ""


def _event_parity(event: Mapping[str, object]) -> dict[str, object]:
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        return {
            "eventId": event.get("eventId"),
            "passed": False,
            "reasonCodes": ["payload_missing"],
        }
    audit = payload.get("evaluationAudit")
    if not isinstance(audit, Mapping):
        return {
            "eventId": event.get("eventId"),
            "passed": False,
            "reasonCodes": ["evaluation_audit_missing"],
        }

    reasons: list[str] = []
    evaluated = int(payload.get("evaluatedReleaseCount") or 0)
    release_audits = audit.get("releaseAudits")
    release_rows = list(release_audits) if isinstance(release_audits, list) else []
    if evaluated <= 0:
        reasons.append("no_release_evaluated")
    if len(release_rows) != evaluated:
        reasons.append("release_count_mismatch")
    if any(
        int(row.get("deepScreenCompleted") or 0)
        != int(row.get("deepScreenRequired") or 0)
        for row in release_rows
        if isinstance(row, Mapping)
    ):
        reasons.append("deep_screen_incomplete")

    funnel = audit.get("funnel")
    if not isinstance(funnel, Mapping):
        reasons.append("funnel_missing")
        funnel = {}
    ordered_counts = [
        int(funnel.get("matchedSignalCount") or 0),
        int(funnel.get("demoTradableSignalCount") or 0),
        int(funnel.get("arbitratedSignalCount") or 0),
        int(funnel.get("latencyPassedSignalCount") or 0),
        int(funnel.get("orderAttemptCount") or 0),
        int(funnel.get("orderAcceptedCount") or 0),
        int(funnel.get("filledOrderCount") or 0),
    ]
    if any(left < right for left, right in zip(ordered_counts, ordered_counts[1:])):
        reasons.append("funnel_conservation_failed")
    if int(payload.get("matchedSignalCount") or 0) != ordered_counts[0]:
        reasons.append("matched_signal_count_mismatch")
    if int(payload.get("createdOrderCount") or 0) != int(
        audit.get("createdOrderCount") or 0
    ):
        reasons.append("created_order_count_mismatch")
    recorded_conservation = audit.get("conservationPassed")
    if recorded_conservation is False:
        reasons.append("recorded_conservation_not_passed")
    recorded_conservation_status = (
        "passed"
        if recorded_conservation is True
        else "failed"
        if recorded_conservation is False
        else "legacy_absent"
    )

    return {
        "eventId": event.get("eventId"),
        "createdAt": event.get("createdAt"),
        "closeSequenceId": payload.get("closeSequenceId"),
        "timeframe": _event_timeframe(event),
        "evaluatedReleaseCount": evaluated,
        "marketInstrumentCount": int(funnel.get("marketInstrumentCount") or 0),
        "liquidityEligibleInstrumentCount": int(
            funnel.get("liquidityEligibleInstrumentCount") or 0
        ),
        "deepEvaluationCount": int(
            funnel.get("componentInstrumentEvaluationCount") or 0
        ),
        "matchedSignalCount": ordered_counts[0],
        "orderAttemptCount": ordered_counts[4],
        "createdOrderCount": int(payload.get("createdOrderCount") or 0),
        "recordedConservationStatus": recorded_conservation_status,
        "independentConservationPassed": not any(
            reason
            in {
                "release_count_mismatch",
                "deep_screen_incomplete",
                "funnel_conservation_failed",
                "matched_signal_count_mismatch",
                "created_order_count_mismatch",
            }
            for reason in reasons
        ),
        "passed": not reasons,
        "reasonCodes": reasons,
    }


def build_historical_shadow_parity(
    heartbeat_events: Sequence[Mapping[str, object]],
    *,
    expected_timeframes: Sequence[str] = ("1h", "1d"),
) -> dict[str, object]:
    """Recompute recorded closed-batch invariants without order access."""

    latest_by_timeframe: dict[str, Mapping[str, object]] = {}
    for event in heartbeat_events:
        timeframe = _event_timeframe(event)
        if not timeframe:
            continue
        previous = latest_by_timeframe.get(timeframe)
        if previous is None or str(event.get("createdAt") or "") > str(
            previous.get("createdAt") or ""
        ):
            latest_by_timeframe[timeframe] = event

    missing = sorted(set(expected_timeframes) - set(latest_by_timeframe))
    parity_rows = [
        _event_parity(latest_by_timeframe[timeframe])
        for timeframe in sorted(set(expected_timeframes) & set(latest_by_timeframe))
    ]
    passed_count = sum(1 for row in parity_rows if row["passed"])
    parity_rate = passed_count / len(parity_rows) if parity_rows else 0.0
    status = (
        "blocked_missing_timeframe_evidence"
        if missing
        else "passed"
        if parity_rate == 1.0
        else "failed_parity_mismatch"
    )
    result = {
        "schemaVersion": "v62_4_1_historical_shadow_parity_v1",
        "status": status,
        "evidenceClass": "historical_recorded_closed_batches",
        "timeframesCovered": sorted(latest_by_timeframe),
        "missingTimeframes": missing,
        "parityRate": parity_rate,
        "events": parity_rows,
        "orderAccessDisabled": True,
        "orderAttemptCount": sum(int(row["orderAttemptCount"]) for row in parity_rows),
        "createdOrderCount": sum(int(row["createdOrderCount"]) for row in parity_rows),
        "cutoverPerformed": False,
        "cutoverEligible": status == "passed",
    }
    result["artifactHash"] = _canonical_hash(result)
    return result


def build_zero_state_reconciliation(
    *,
    runtime_rows: Sequence[Mapping[str, object]],
    execution_records: Sequence[Mapping[str, object]],
    account_snapshot: Mapping[str, object],
) -> dict[str, object]:
    """Reconcile persisted zero state without claiming a current private API read."""

    terminal_statuses = {
        "rejected",
        "canceled",
        "cancelled",
        "closed",
        "filled_and_closed",
    }
    unresolved_records = [
        str(row.get("recordId") or "")
        for row in execution_records
        if str(row.get("status") or "").lower() not in terminal_statuses
    ]
    open_positions = int(account_snapshot.get("positionCount") or 0)
    unknown_orders = int(account_snapshot.get("unknownOrderCount") or 0)
    partial_orders = int(account_snapshot.get("partiallyFilledOrderCount") or 0)
    source = str(account_snapshot.get("source") or "")
    passed = (
        source == "historical_sanitized_snapshot"
        and open_positions == 0
        and unknown_orders == 0
        and partial_orders == 0
        and not unresolved_records
    )
    result = {
        "schemaVersion": "v62_4_1_zero_state_reconciliation_v1",
        "status": (
            "passed_historical_zero_state"
            if passed
            else "blocked_nonzero_or_unresolved_state"
        ),
        "evidenceClass": source or "unknown",
        "snapshotAt": account_snapshot.get("updatedAt"),
        "currentPrivateRestWsStatus": "not_run_no_credentials",
        "runtimeStates": [dict(row) for row in runtime_rows],
        "executionRecordCount": len(execution_records),
        "unresolvedExecutionRecordIds": unresolved_records,
        "openPositionCount": open_positions,
        "unknownOrderCount": unknown_orders,
        "partiallyFilledOrderCount": partial_orders,
        "newEntriesAllowed": False,
        "demoArm": False,
        "liveEnabled": False,
        "withdrawEnabled": False,
    }
    result["artifactHash"] = _canonical_hash(result)
    return result


def _window_summary(
    observations: Sequence[Mapping[str, object]],
    *,
    start_at: datetime,
    end_at: datetime,
) -> dict[str, object]:
    rows = [
        row
        for row in observations
        if row.get("timestamp")
        and start_at <= _parse_time(str(row["timestamp"])) <= end_at
    ]
    return {
        "observationCount": len(rows),
        "uniqueSymbolCount": len({str(row.get("symbol") or "") for row in rows}),
        "timeframes": sorted({str(row.get("timeframe") or "") for row in rows}),
        "matchedSignalCount": sum(int(row.get("signalMatched") or 0) for row in rows),
        "wouldAttemptDemoOrderCount": sum(
            int(row.get("wouldAttemptDemoOrder") or 0) for row in rows
        ),
    }


def build_broad_universe_audit(
    *,
    observations: Sequence[Mapping[str, object]],
    heartbeat_events: Sequence[Mapping[str, object]],
    as_of: str,
) -> dict[str, object]:
    as_of_time = _parse_time(as_of)
    observation_times = [
        _parse_time(str(row["timestamp"]))
        for row in observations
        if row.get("timestamp")
    ]
    observed_span_days = (
        (max(observation_times) - min(observation_times)).total_seconds() / 86400
        if len(observation_times) >= 2
        else 0.0
    )
    parity_rows = [_event_parity(event) for event in heartbeat_events]
    maximum_market_count = max(
        (int(row["marketInstrumentCount"]) for row in parity_rows),
        default=0,
    )
    maximum_liquidity_count = max(
        (int(row["liquidityEligibleInstrumentCount"]) for row in parity_rows),
        default=0,
    )
    maximum_deep_count = max(
        (int(row["deepEvaluationCount"]) for row in parity_rows),
        default=0,
    )
    accepted = observed_span_days >= 90 and maximum_market_count >= 100
    result = {
        "schemaVersion": "v62_4_1_broad_universe_audit_v1",
        "source": "recorded_runtime_evidence",
        "status": (
            "passed_30d_90d_broad_universe"
            if accepted
            else "blocked_insufficient_observation_span"
        ),
        "asOf": as_of,
        "observedFrom": (
            min(observation_times).isoformat() if observation_times else None
        ),
        "observedTo": (
            max(observation_times).isoformat() if observation_times else None
        ),
        "observedSpanDays": observed_span_days,
        "windows": {
            "30d": _window_summary(
                observations,
                start_at=as_of_time - timedelta(days=30),
                end_at=as_of_time,
            ),
            "90d": _window_summary(
                observations,
                start_at=as_of_time - timedelta(days=90),
                end_at=as_of_time,
            ),
        },
        "broadUniverse": {
            "maximumObservedMarketInstrumentCount": maximum_market_count,
            "maximumObservedLiquidityEligibleCount": maximum_liquidity_count,
            "maximumObservedDeepEvaluationCount": maximum_deep_count,
            "broadUniverseThreshold": 100,
        },
        "acceptedAs30d90dMatchability": accepted,
        "newEntriesAllowed": False,
        "orderAccessDisabled": True,
    }
    result["artifactHash"] = _canonical_hash(result)
    return result


def online_backup_sqlite(source: str | Path, destination: str | Path) -> dict[str, object]:
    source_path = Path(source).resolve()
    destination_path = Path(destination).resolve()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists():
        destination_path.unlink()

    source_connection = sqlite3.connect(
        f"file:{source_path.as_posix()}?mode=ro",
        uri=True,
    )
    destination_connection = sqlite3.connect(destination_path)
    try:
        source_connection.backup(destination_connection)
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()

    verification = sqlite3.connect(
        f"file:{destination_path.as_posix()}?mode=ro",
        uri=True,
    )
    try:
        integrity = str(verification.execute("pragma integrity_check").fetchone()[0])
        tables = [
            str(row[0])
            for row in verification.execute(
                "select name from sqlite_master "
                "where type='table' and name not like 'sqlite_%' order by name"
            )
        ]
        table_counts = {
            table: int(
                verification.execute(
                    f'SELECT COUNT(*) FROM "{table.replace(chr(34), chr(34) * 2)}"'
                ).fetchone()[0]
            )
            for table in tables
        }
    finally:
        verification.close()

    return {
        "sourcePath": str(source_path),
        "snapshotPath": str(destination_path),
        "capturedByProcessId": os.getpid(),
        "integrityCheck": integrity,
        "tableCounts": table_counts,
        "sha256": _file_hash(destination_path),
        "sizeBytes": destination_path.stat().st_size,
    }
