"""Online backup and fail-closed restore receipts for local SQLite state."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..sqlite_runtime_policy import integrity_check


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _database_snapshot(connection: sqlite3.Connection) -> dict[str, Any]:
    integrity = integrity_check(connection)
    tables = [
        str(row[0])
        for row in connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    ]
    counts = {
        table: int(
            connection.execute(
                f'SELECT COUNT(*) FROM "{table.replace(chr(34), chr(34) * 2)}"'
            ).fetchone()[0]
        )
        for table in tables
    }
    return {
        "integrityPassed": bool(integrity["passed"]),
        "integrityRows": list(integrity["rows"]),
        "userVersion": int(connection.execute("PRAGMA user_version").fetchone()[0]),
        "journalMode": str(connection.execute("PRAGMA journal_mode").fetchone()[0]),
        "tableCounts": counts,
    }


def create_online_backup(
    source_path: Path | str,
    destination_path: Path | str,
) -> dict[str, Any]:
    source = Path(source_path)
    destination = Path(destination_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    source_connection = sqlite3.connect(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
        snapshot = _database_snapshot(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()
    return {
        "schemaVersion": "alphapilot_v63_sqlite_backup_receipt_v1",
        "operation": "online_backup",
        "sourcePath": str(source.resolve()),
        "destinationPath": str(destination.resolve()),
        "sha256": _sha256(destination),
        "createdAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
        **snapshot,
    }


@dataclass(frozen=True)
class RestoreGuard:
    allRolesStopped: bool
    demoArmed: bool
    liveArmed: bool
    activeLeaseCount: int

    def reason_codes(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.allRolesStopped:
            reasons.append("roles_not_stopped")
        if self.demoArmed:
            reasons.append("demo_armed")
        if self.liveArmed:
            reasons.append("live_armed")
        if self.activeLeaseCount != 0:
            reasons.append("active_leases_nonzero")
        return tuple(reasons)


def restore_online_backup(
    backup_path: Path | str,
    destination_path: Path | str,
    *,
    guard: RestoreGuard,
) -> dict[str, Any]:
    reasons = guard.reason_codes()
    if reasons:
        raise PermissionError("sqlite_restore_blocked:" + ",".join(reasons))
    source = Path(backup_path)
    destination = Path(destination_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_suffix(destination.suffix + ".restore.tmp")
    if staging.exists():
        staging.unlink()

    source_connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    staging_connection = sqlite3.connect(staging)
    try:
        source_snapshot = _database_snapshot(source_connection)
        if not source_snapshot["integrityPassed"]:
            raise RuntimeError("sqlite_restore_source_integrity_failed")
        source_connection.backup(staging_connection)
        restored_snapshot = _database_snapshot(staging_connection)
        if not restored_snapshot["integrityPassed"]:
            raise RuntimeError("sqlite_restore_staging_integrity_failed")
    finally:
        staging_connection.close()
        source_connection.close()
    os.replace(staging, destination)
    return {
        "schemaVersion": "alphapilot_v63_sqlite_restore_receipt_v1",
        "operation": "guarded_restore",
        "sourcePath": str(source.resolve()),
        "destinationPath": str(destination.resolve()),
        "sha256": _sha256(destination),
        "createdAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "guard": {
            "allRolesStopped": guard.allRolesStopped,
            "demoArmed": guard.demoArmed,
            "liveArmed": guard.liveArmed,
            "activeLeaseCount": guard.activeLeaseCount,
        },
        **restored_snapshot,
    }
