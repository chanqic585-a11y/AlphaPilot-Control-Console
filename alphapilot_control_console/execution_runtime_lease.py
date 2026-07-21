"""Single-writer execution authority for Demo and Live order runtimes."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from .config import DATA_DIR
from .sqlite_runtime_policy import open_sqlite


EXECUTION_RUNTIME_LEASE_PATH = DATA_DIR / "execution_runtime_lease.sqlite"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return normalized.astimezone(UTC).isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExecutionRuntimeLeaseClaim:
    environment: str
    ownerId: str
    token: str
    acquiredAt: str
    expiresAt: str


class ExecutionRuntimeLeaseStore:
    """Persist only token hashes so order authority remains process-only."""

    def __init__(
        self,
        path: Path | str,
        *,
        now_factory: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._now = now_factory
        self.connection = open_sqlite(path)
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS ExecutionRuntimeLeases (
              environment TEXT PRIMARY KEY,
              ownerId TEXT NOT NULL,
              tokenHash TEXT NOT NULL,
              acquiredAt TEXT NOT NULL,
              heartbeatAt TEXT NOT NULL,
              expiresAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ExecutionRuntimeLeaseEvents (
              eventId INTEGER PRIMARY KEY AUTOINCREMENT,
              environment TEXT NOT NULL,
              ownerId TEXT NOT NULL,
              eventType TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def acquire(
        self,
        *,
        environment: str,
        owner_id: str,
        ttl_seconds: int,
    ) -> ExecutionRuntimeLeaseClaim:
        normalized_environment = str(environment).strip().lower()
        normalized_owner = str(owner_id).strip()
        if normalized_environment not in {"okx_demo", "okx_live"}:
            raise ValueError("Execution lease environment must be okx_demo or okx_live")
        if not normalized_owner:
            raise ValueError("Execution lease owner is required")
        if not 5 <= int(ttl_seconds) <= 300:
            raise ValueError("Execution lease TTL must be between 5 and 300 seconds")

        now = self._now().astimezone(UTC)
        token = secrets.token_urlsafe(32)
        claim = ExecutionRuntimeLeaseClaim(
            environment=normalized_environment,
            ownerId=normalized_owner,
            token=token,
            acquiredAt=_iso(now),
            expiresAt=_iso(now + timedelta(seconds=int(ttl_seconds))),
        )
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            existing = self.connection.execute(
                "SELECT * FROM ExecutionRuntimeLeases WHERE environment = ?",
                (normalized_environment,),
            ).fetchone()
            if existing is not None and _parse(str(existing["expiresAt"])) > now:
                raise PermissionError(
                    f"Execution authority is already held by {existing['ownerId']}"
                )
            self.connection.execute(
                """
                INSERT INTO ExecutionRuntimeLeases(
                  environment, ownerId, tokenHash, acquiredAt, heartbeatAt, expiresAt
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(environment) DO UPDATE SET
                  ownerId=excluded.ownerId,
                  tokenHash=excluded.tokenHash,
                  acquiredAt=excluded.acquiredAt,
                  heartbeatAt=excluded.heartbeatAt,
                  expiresAt=excluded.expiresAt
                """,
                (
                    claim.environment,
                    claim.ownerId,
                    _token_hash(claim.token),
                    claim.acquiredAt,
                    claim.acquiredAt,
                    claim.expiresAt,
                ),
            )
            self._append_event(claim, "lease_acquired", now)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return claim

    def assert_authority(self, claim: ExecutionRuntimeLeaseClaim) -> None:
        row = self.connection.execute(
            "SELECT * FROM ExecutionRuntimeLeases WHERE environment = ?",
            (claim.environment,),
        ).fetchone()
        now = self._now().astimezone(UTC)
        valid = (
            row is not None
            and str(row["ownerId"]) == claim.ownerId
            and str(row["tokenHash"]) == _token_hash(claim.token)
            and _parse(str(row["expiresAt"])) > now
        )
        if not valid:
            raise PermissionError("Execution runtime lease is absent, stale, or owned elsewhere")

    def heartbeat(
        self,
        claim: ExecutionRuntimeLeaseClaim,
        *,
        ttl_seconds: int,
    ) -> ExecutionRuntimeLeaseClaim:
        self.assert_authority(claim)
        now = self._now().astimezone(UTC)
        refreshed = ExecutionRuntimeLeaseClaim(
            environment=claim.environment,
            ownerId=claim.ownerId,
            token=claim.token,
            acquiredAt=claim.acquiredAt,
            expiresAt=_iso(now + timedelta(seconds=int(ttl_seconds))),
        )
        with self.connection:
            self.connection.execute(
                "UPDATE ExecutionRuntimeLeases SET heartbeatAt = ?, expiresAt = ? WHERE environment = ?",
                (_iso(now), refreshed.expiresAt, claim.environment),
            )
            self._append_event(refreshed, "lease_heartbeat", now)
        return refreshed

    def release(self, claim: ExecutionRuntimeLeaseClaim) -> None:
        self.assert_authority(claim)
        now = self._now().astimezone(UTC)
        with self.connection:
            self._append_event(claim, "lease_released", now)
            self.connection.execute(
                "DELETE FROM ExecutionRuntimeLeases WHERE environment = ? AND tokenHash = ?",
                (claim.environment, _token_hash(claim.token)),
            )

    def projection(self, environment: str) -> dict[str, object] | None:
        row = self.connection.execute(
            "SELECT * FROM ExecutionRuntimeLeases WHERE environment = ?",
            (str(environment).strip().lower(),),
        ).fetchone()
        if row is None:
            return None
        return {
            "environment": str(row["environment"]),
            "ownerId": str(row["ownerId"]),
            "tokenHash": str(row["tokenHash"]),
            "acquiredAt": str(row["acquiredAt"]),
            "heartbeatAt": str(row["heartbeatAt"]),
            "expiresAt": str(row["expiresAt"]),
            "expired": _parse(str(row["expiresAt"])) <= self._now().astimezone(UTC),
        }

    def _append_event(
        self,
        claim: ExecutionRuntimeLeaseClaim,
        event_type: str,
        now: datetime,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO ExecutionRuntimeLeaseEvents(environment, ownerId, eventType, createdAt)
            VALUES (?, ?, ?, ?)
            """,
            (claim.environment, claim.ownerId, event_type, _iso(now)),
        )
