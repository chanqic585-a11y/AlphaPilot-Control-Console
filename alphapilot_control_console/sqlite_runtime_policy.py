"""Shared SQLite safety policy for local AlphaPilot ledgers."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


DEFAULT_BUSY_TIMEOUT_MS = 5_000


def open_sqlite(
    path: Path | str,
    *,
    foreign_keys: bool = True,
    wal: bool = True,
    synchronous: str = "NORMAL",
) -> sqlite3.Connection:
    """Open a local ledger with explicit, inspectable runtime pragmas."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA busy_timeout = {DEFAULT_BUSY_TIMEOUT_MS}")
    connection.execute(f"PRAGMA foreign_keys = {'ON' if foreign_keys else 'OFF'}")
    if wal:
        connection.execute("PRAGMA journal_mode = WAL")
    normalized_sync = str(synchronous).strip().upper()
    if normalized_sync not in {"OFF", "NORMAL", "FULL", "EXTRA"}:
        connection.close()
        raise ValueError("Unsupported SQLite synchronous policy")
    connection.execute(f"PRAGMA synchronous = {normalized_sync}")
    return connection


def integrity_check(connection: sqlite3.Connection) -> dict[str, object]:
    rows = [str(row[0]) for row in connection.execute("PRAGMA integrity_check").fetchall()]
    return {"passed": rows == ["ok"], "rows": rows}


def ensure_migration_ledger(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS SchemaMigrationLedger (
          migrationId TEXT PRIMARY KEY,
          checksum TEXT NOT NULL,
          description TEXT NOT NULL,
          targetUserVersion INTEGER NOT NULL,
          appliedAt TEXT NOT NULL
        )
        """
    )
    connection.commit()


def get_user_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _migration_checksum(statements: tuple[str, ...]) -> str:
    body = "\n-- statement --\n".join(statement.strip() for statement in statements)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def apply_migration(
    connection: sqlite3.Connection,
    *,
    migration_id: str,
    description: str,
    statements: Iterable[str],
    target_user_version: int,
) -> bool:
    """Apply one immutable migration or verify the prior matching receipt."""

    if not migration_id.strip() or target_user_version < 0:
        raise ValueError("Migration identity and target user version are required")
    normalized = tuple(statement.strip() for statement in statements if statement.strip())
    if not normalized:
        raise ValueError("At least one migration statement is required")
    checksum = _migration_checksum(normalized)
    ensure_migration_ledger(connection)
    row = connection.execute(
        "SELECT checksum FROM SchemaMigrationLedger WHERE migrationId = ?",
        (migration_id,),
    ).fetchone()
    if row is not None:
        if str(row[0]) != checksum:
            raise RuntimeError("Migration checksum does not match the immutable ledger")
        return False

    with connection:
        for statement in normalized:
            connection.execute(statement)
        connection.execute(f"PRAGMA user_version = {int(target_user_version)}")
        connection.execute(
            """
            INSERT INTO SchemaMigrationLedger (
              migrationId, checksum, description, targetUserVersion, appliedAt
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                migration_id,
                checksum,
                description,
                target_user_version,
                datetime.now(UTC).replace(microsecond=0).isoformat(),
            ),
        )
    return True


def online_backup(
    source: sqlite3.Connection,
    destination_path: Path | str,
) -> dict[str, object]:
    """Create an online SQLite backup and return a redacted integrity receipt."""

    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = sqlite3.connect(destination)
    try:
        source.backup(backup)
        result = integrity_check(backup)
    finally:
        backup.close()
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return {
        "path": str(destination),
        "sha256": digest,
        "integrityPassed": bool(result["passed"]),
        "createdAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
