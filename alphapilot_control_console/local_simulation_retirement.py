from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FULL_LOCAL_SIMULATION_ENABLED = False
LOCAL_VIRTUAL_POSITION_ENABLED = False
LOCAL_VIRTUAL_EQUITY_ENABLED = False
LOCAL_SIMULATION_LIFECYCLE_ENABLED = False
SIMULATION_LEARNING_ENABLED = False

RETIRED_LOCAL_SIMULATION_POST_ROUTES = frozenset(
    {
        "/api/local-sandbox/run",
        "/api/local-sandbox/build-daily-report",
        "/api/local-sandbox/auto-runner",
        "/api/local-sandbox/auto-runner/run-now",
        "/api/strategy-stage/return-sandbox",
        "/api/paper-observation-task",
        "/api/paper-observation-log",
    }
)

_RETIRED_WORKFLOW_STATES = frozenset(
    {
        "local_forward",
        "local_sandbox",
        "local_simulation_running",
        "local_simulation_passed",
    }
)


class LocalSimulationRetiredError(RuntimeError):
    pass


def retired_write_response() -> dict[str, Any]:
    return {
        "status": "retired",
        "code": "local_simulation_retired",
        "historicalDataPreserved": True,
        "nextAction": "Use formal backtest and OKX Demo validation.",
    }


def legacy_read_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "deprecated": True,
        "readOnly": True,
        "evidenceSource": "legacy_local_observation",
    }


def raise_local_simulation_retired() -> None:
    raise LocalSimulationRetiredError(
        "local_simulation_retired: use formal backtest and OKX Demo validation"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_state(data_dir: Path) -> dict[str, Any]:
    state_path = data_dir / "console_state.json"
    if not state_path.exists():
        return {}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _list_count(state: dict[str, Any], key: str, fallback: str | None = None) -> int:
    value = state.get(key)
    if not isinstance(value, list) and fallback:
        value = state.get(fallback)
    return len(value) if isinstance(value, list) else 0


def _closed_sample_count(state: dict[str, Any]) -> int:
    logs = state.get("paperObservationLogs")
    if not isinstance(logs, dict):
        return 0
    return sum(
        1
        for rows in logs.values()
        if isinstance(rows, list)
        for row in rows
        if isinstance(row, dict) and str(row.get("outcome") or "").strip()
    )


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _count_retired_workflow_rows(data_dir: Path) -> int:
    total = 0
    for database_path in sorted(data_dir.glob("*.sqlite")):
        try:
            connection = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
        except sqlite3.Error:
            continue
        try:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            for (table_name,) in tables:
                columns = {
                    str(row[1])
                    for row in connection.execute(
                        f"PRAGMA table_info({_quote_identifier(str(table_name))})"
                    ).fetchall()
                }
                state_columns = [name for name in ("stage", "status") if name in columns]
                if not state_columns:
                    continue
                predicates = " OR ".join(
                    f"LOWER({_quote_identifier(column)}) IN ({','.join('?' for _ in _RETIRED_WORKFLOW_STATES)})"
                    for column in state_columns
                )
                parameters = tuple(
                    state
                    for _column in state_columns
                    for state in sorted(_RETIRED_WORKFLOW_STATES)
                )
                row = connection.execute(
                    f"SELECT COUNT(*) FROM {_quote_identifier(str(table_name))} WHERE {predicates}",
                    parameters,
                ).fetchone()
                total += int(row[0] if row else 0)
        except sqlite3.Error:
            continue
        finally:
            connection.close()
    return total


def capture_local_history_snapshot(data_dir: Path) -> dict[str, Any]:
    root = Path(data_dir).expanduser().resolve()
    state = _read_state(root)
    files = []
    for path in sorted(root.iterdir()) if root.exists() else []:
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".sqlite"}:
            continue
        files.append(
            {
                "name": path.name,
                "sizeBytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return {
        "dataDirectory": str(root),
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "localRuns": _list_count(state, "localSandboxRuns"),
            "virtualOrders": _list_count(state, "virtualOrders", "testnetSimulatedOrders"),
            "virtualFills": _list_count(state, "virtualFills"),
            "virtualPositions": _list_count(state, "virtualPositions"),
            "equitySnapshots": _list_count(state, "equitySnapshots"),
            "closedSamples": _closed_sample_count(state),
            "learningSamples": _list_count(state, "localSandboxLearningSnapshots"),
            "dailyReports": _list_count(state, "localSandboxDailyReports"),
            "workflowRowsInRetiredStates": _count_retired_workflow_rows(root),
        },
        "files": files,
    }


def _backup_sqlite(source: Path, destination: Path) -> None:
    source_connection = sqlite3.connect(str(source))
    destination_connection = sqlite3.connect(str(destination))
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def backup_local_history(
    data_dir: Path,
    *,
    backup_root: Path | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    source_root = Path(data_dir).expanduser().resolve()
    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination_root = (
        Path(backup_root).expanduser().resolve()
        if backup_root is not None
        else source_root.parent / "backups" / "local_simulation_retirement"
    ) / stamp
    destination_root.mkdir(parents=True, exist_ok=False)

    before = capture_local_history_snapshot(source_root)
    for source in sorted(source_root.iterdir()):
        if not source.is_file() or source.suffix.lower() not in {".json", ".jsonl", ".sqlite"}:
            continue
        destination = destination_root / source.name
        if source.suffix.lower() == ".sqlite":
            _backup_sqlite(source, destination)
        else:
            shutil.copy2(source, destination)

    backup = capture_local_history_snapshot(destination_root)
    manifest = {
        "version": "local_simulation_retirement_backup_v1",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "sourceDirectory": str(source_root),
        "backupDirectory": str(destination_root),
        "before": before,
        "backup": backup,
    }
    (destination_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
