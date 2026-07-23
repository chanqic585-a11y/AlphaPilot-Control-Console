from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.v62_4_1_runtime_evidence import (
    build_broad_universe_audit,
    build_historical_shadow_parity,
    build_no_order_runtime_capture,
    build_zero_state_reconciliation,
    online_backup_sqlite,
)


SNAPSHOT_NAMES = (
    "unified_auto_execution.sqlite",
    "evolution_demo_execution.sqlite",
    "shadow_observations.sqlite",
    "execution_runtime_lease.sqlite",
)

MODULE_PATHS = (
    "alphapilot_control_console/unified_auto_execution.py",
    "alphapilot_control_console/demo_release_scanner.py",
    "alphapilot_control_console/execution_runtime_lease.py",
    "alphapilot_control_console/runtime_identity.py",
    "alphapilot_control_console/execution_shadow_parity.py",
    "alphapilot_control_console/okx_demo_private_reconciliation.py",
    "alphapilot_control_console/v62_4_1_runtime_evidence.py",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.strip()


def _readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    return connection


def _safe_heartbeat(row: sqlite3.Row) -> dict[str, object]:
    payload = json.loads(str(row["payloadJson"]))
    audit = payload.get("evaluationAudit")
    if not isinstance(audit, dict):
        audit = {}
    funnel = audit.get("funnel")
    if not isinstance(funnel, dict):
        market = audit.get("marketSummary")
        market = market if isinstance(market, dict) else {}
        funnel = {
            "marketInstrumentCount": int(market.get("totalInstrumentCount") or 0),
            "liquidityEligibleInstrumentCount": int(
                market.get("liquidityEligibleCount") or 0
            ),
            "componentInstrumentEvaluationCount": int(
                market.get("deepScreenCount") or 0
            ),
            "matchedSignalCount": int(audit.get("matchedSignalCount") or 0),
            "demoTradableSignalCount": 0,
            "arbitratedSignalCount": 0,
            "latencyPassedSignalCount": 0,
            "orderAttemptCount": int(audit.get("orderAttemptCount") or 0),
            "orderAcceptedCount": 0,
            "filledOrderCount": int(audit.get("createdOrderCount") or 0),
        }
    return {
        "eventId": int(row["eventId"]),
        "createdAt": str(row["createdAt"]),
        "payload": {
            "closeSequenceId": payload.get("closeSequenceId"),
            "evaluatedReleaseCount": int(payload.get("evaluatedReleaseCount") or 0),
            "matchedSignalCount": int(payload.get("matchedSignalCount") or 0),
            "createdOrderCount": int(payload.get("createdOrderCount") or 0),
            "evaluationAudit": {
                "conservationPassed": audit.get("conservationPassed"),
                "evaluatedReleaseCount": int(
                    audit.get("evaluatedReleaseCount") or 0
                ),
                "matchedSignalCount": int(audit.get("matchedSignalCount") or 0),
                "createdOrderCount": int(audit.get("createdOrderCount") or 0),
                "orderAttemptCount": int(audit.get("orderAttemptCount") or 0),
                "releaseAudits": audit.get("releaseAudits")
                if isinstance(audit.get("releaseAudits"), list)
                else [],
                "funnel": funnel,
                "stageDurationsMs": audit.get("stageDurationsMs")
                if isinstance(audit.get("stageDurationsMs"), dict)
                else {},
                "state": audit.get("state"),
            },
        },
    }


def _latest_heartbeat(connection: sqlite3.Connection, timeframe: str) -> dict[str, object]:
    rows = connection.execute(
        "select eventId,payloadJson,createdAt from AutoExecutionEvents "
        "where eventType='heartbeat_completed' order by eventId desc"
    )
    prefix = timeframe + ":"
    for row in rows:
        payload = json.loads(str(row["payloadJson"]))
        if str(payload.get("closeSequenceId") or "").startswith(prefix):
            return _safe_heartbeat(row)
    raise RuntimeError(f"no heartbeat_completed evidence for {timeframe}")


def _runtime_rows(connection: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "environment": str(row["environment"]),
            "desiredEnabled": bool(row["desiredEnabled"]),
            "armedProcessId": row["armedProcessId"],
            "status": str(row["status"]),
            "lastHeartbeatAt": row["lastHeartbeatAt"],
            "nextEvaluationAt": row["nextEvaluationAt"],
            "pauseReason": row["pauseReason"],
            "lastError": row["lastError"],
            "updatedAt": row["updatedAt"],
        }
        for row in connection.execute(
            "select environment,desiredEnabled,armedProcessId,status,"
            "lastHeartbeatAt,nextEvaluationAt,pauseReason,lastError,updatedAt "
            "from AutoExecutionRuntime order by environment"
        )
    ]


def _lease_rows(connection: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "environment": str(row["environment"]),
            "ownerId": str(row["ownerId"]),
            "acquiredAt": str(row["acquiredAt"]),
            "heartbeatAt": str(row["heartbeatAt"]),
            "expiresAt": str(row["expiresAt"]),
        }
        for row in connection.execute(
            "select environment,ownerId,acquiredAt,heartbeatAt,expiresAt "
            "from ExecutionRuntimeLeases order by environment"
        )
    ]


def _execution_records(connection: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "recordId": str(row["recordId"]),
            "status": str(row["status"]),
            "exchangeOrderId": row["exchangeOrderId"],
            "updatedAt": str(row["updatedAt"]),
        }
        for row in connection.execute(
            "select recordId,status,exchangeOrderId,updatedAt "
            "from DemoExecutionRecords order by createdAt"
        )
    ]


def _account_snapshot(connection: sqlite3.Connection) -> dict[str, object]:
    row = connection.execute(
        "select valueJson,updatedAt from DemoRuntimeState "
        "where stateKey='lastPortfolioSnapshot'"
    ).fetchone()
    if row is None:
        return {
            "source": "historical_sanitized_snapshot",
            "updatedAt": None,
            "positionCount": -1,
            "unknownOrderCount": -1,
            "partiallyFilledOrderCount": -1,
        }
    value = json.loads(str(row["valueJson"]))
    return {
        "source": "historical_sanitized_snapshot",
        "upstreamSource": value.get("source"),
        "updatedAt": value.get("updatedAt") or row["updatedAt"],
        "positionCount": int(value.get("openPositionCount") or 0),
        "unknownOrderCount": int(value.get("unknownOrderCount") or 0),
        "partiallyFilledOrderCount": int(
            value.get("partiallyFilledOrderCount") or 0
        ),
        "rawExchangePayloadExcluded": bool(
            value.get("rawExchangePayloadExcluded", True)
        ),
    }


def _observations(connection: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {
            "timestamp": str(row["timestamp"]),
            "symbol": str(row["symbol"]),
            "timeframe": str(row["timeframe"]),
            "signalMatched": int(row["signalMatched"] or 0),
            "wouldAttemptDemoOrder": int(row["wouldAttemptDemoOrder"] or 0),
        }
        for row in connection.execute(
            "select timestamp,symbol,timeframe,signalMatched,wouldAttemptDemoOrder "
            "from ShadowObservations order by timestamp"
        )
    ]


def build_evidence(repo: Path, data_root: Path, output: Path) -> dict[str, object]:
    captured_at = datetime.now(timezone.utc).isoformat()
    snapshot_root = output / "source_snapshots"
    receipts = []
    for name in SNAPSHOT_NAMES:
        receipts.append(
            online_backup_sqlite(data_root / name, snapshot_root / name)
        )
    _write_json(output / "sqlite_backup_receipts.json", receipts)

    unified = _readonly(snapshot_root / "unified_auto_execution.sqlite")
    demo = _readonly(snapshot_root / "evolution_demo_execution.sqlite")
    shadow = _readonly(snapshot_root / "shadow_observations.sqlite")
    leases = _readonly(snapshot_root / "execution_runtime_lease.sqlite")
    try:
        runtime_rows = _runtime_rows(unified)
        active_leases = _lease_rows(leases)
        heartbeats = [
            _latest_heartbeat(unified, "1h"),
            _latest_heartbeat(unified, "1d"),
        ]
        records = _execution_records(demo)
        account = _account_snapshot(demo)
        observations = _observations(shadow)
    finally:
        leases.close()
        shadow.close()
        demo.close()
        unified.close()

    module_hashes = {
        relative: _sha256(repo / relative)
        for relative in MODULE_PATHS
        if (repo / relative).exists()
    }
    capture = build_no_order_runtime_capture(
        repository_commit=_git(repo, "rev-parse", "HEAD"),
        repository_tag=_git(repo, "describe", "--tags", "--always", "--dirty"),
        module_hashes=module_hashes,
        process_id=os.getpid(),
        captured_at=captured_at,
        source_runtime_online=False,
        source_runtime_rows=runtime_rows,
        active_execution_leases=active_leases,
        observation_lease={
            "leaseId": "v62-4-1-observation-" + captured_at,
            "leaseClass": "read_only_observation",
        },
    )
    parity = build_historical_shadow_parity(heartbeats)
    reconciliation = build_zero_state_reconciliation(
        runtime_rows=runtime_rows,
        execution_records=records,
        account_snapshot=account,
    )
    matchability = build_broad_universe_audit(
        observations=observations,
        heartbeat_events=heartbeats,
        as_of=captured_at,
    )
    _write_json(output / "runtime_identity_capture.json", capture)
    _write_json(output / "historical_shadow_parity_1h_1d.json", parity)
    _write_json(output / "zero_state_reconciliation.json", reconciliation)
    _write_json(output / "matchability_recorded_runtime_audit.json", matchability)

    summary = {
        "schemaVersion": "v62_4_1_runtime_evidence_bundle_v1",
        "capturedAt": captured_at,
        "runtimeCaptureStatus": capture["status"],
        "historicalShadowParityStatus": parity["status"],
        "zeroStateReconciliationStatus": reconciliation["status"],
        "matchabilityStatus": matchability["status"],
        "sourceRuntimeOnline": False,
        "demoArm": False,
        "newEntriesAllowed": False,
        "orderAttemptCount": 0,
        "liveEnabled": False,
        "withdrawEnabled": False,
        "limitations": [
            "Current private REST and WebSocket reconciliation was not run because no credentials were requested.",
            "Recorded matchability evidence spans less than 30 days and is not accepted as 30d/90d coverage.",
            "Historical closed-batch parity is evidence of prior execution semantics, not proof that the runtime is currently online.",
        ],
    }
    summary["artifactHash"] = "sha256:" + hashlib.sha256(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    _write_json(output / "runtime_evidence_summary.json", summary)
    (output / "runtime_evidence_summary.md").write_text(
        "\n".join(
            [
                "# V62.4.1 Runtime Evidence Summary",
                "",
                f"- Captured at: `{captured_at}`",
                f"- No-order capture: `{capture['status']}`",
                f"- Historical 1h/1d shadow parity: `{parity['status']}`",
                f"- Historical zero-state reconciliation: `{reconciliation['status']}`",
                f"- Matchability: `{matchability['status']}`",
                "- Runtime online: `false`",
                "- Demo ARM: `false`",
                "- New entries allowed: `false`",
                "- Live: `false`",
                "- Withdraw: `false`",
                "",
                "The capture is intentionally read-only. It does not claim current private REST/WS reconciliation or accepted 30d/90d matchability coverage.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(r"D:\Codex-Workspace\AlphaPilot-Control-Console\data"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = build_evidence(
        args.repo_root.resolve(),
        args.data_root.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
