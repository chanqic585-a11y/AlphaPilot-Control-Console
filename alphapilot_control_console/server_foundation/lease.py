"""Environment-and-role scoped runtime leases with fencing tokens."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from ..sqlite_runtime_policy import open_sqlite
from .contracts import FoundationRole


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return normalized.astimezone(UTC).isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FoundationLeaseClaim:
    leaseId: str
    environment: str
    role: FoundationRole
    ownerId: str
    token: str
    fencingToken: int
    acquiredAt: str
    expiresAt: str


class FoundationLeaseStore:
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
            CREATE TABLE IF NOT EXISTS FoundationLeaseSequences (
              environment TEXT NOT NULL,
              role TEXT NOT NULL,
              lastFencingToken INTEGER NOT NULL,
              PRIMARY KEY(environment, role)
            );
            CREATE TABLE IF NOT EXISTS FoundationRuntimeLeases (
              environment TEXT NOT NULL,
              role TEXT NOT NULL,
              leaseId TEXT NOT NULL,
              ownerId TEXT NOT NULL,
              tokenHash TEXT NOT NULL,
              fencingToken INTEGER NOT NULL,
              acquiredAt TEXT NOT NULL,
              heartbeatAt TEXT NOT NULL,
              expiresAt TEXT NOT NULL,
              PRIMARY KEY(environment, role)
            );
            CREATE TABLE IF NOT EXISTS FoundationLeaseEvents (
              eventId INTEGER PRIMARY KEY AUTOINCREMENT,
              environment TEXT NOT NULL,
              role TEXT NOT NULL,
              leaseId TEXT NOT NULL,
              ownerId TEXT NOT NULL,
              fencingToken INTEGER NOT NULL,
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
        role: FoundationRole,
        owner_id: str,
        ttl_seconds: int,
    ) -> FoundationLeaseClaim:
        normalized_environment = str(environment).strip().lower()
        normalized_owner = str(owner_id).strip()
        if not normalized_environment or not normalized_owner:
            raise ValueError("foundation_lease_scope_and_owner_required")
        if not 5 <= int(ttl_seconds) <= 300:
            raise ValueError("foundation_lease_ttl_must_be_5_to_300_seconds")
        role = FoundationRole(role)
        now = self._now().astimezone(UTC)
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            existing = self.connection.execute(
                """
                SELECT * FROM FoundationRuntimeLeases
                WHERE environment = ? AND role = ?
                """,
                (normalized_environment, role.value),
            ).fetchone()
            if existing is not None and _parse(str(existing["expiresAt"])) > now:
                raise PermissionError(
                    "foundation_lease_scope_already_owned:"
                    f"{normalized_environment}:{role.value}"
                )
            sequence = self.connection.execute(
                """
                SELECT lastFencingToken FROM FoundationLeaseSequences
                WHERE environment = ? AND role = ?
                """,
                (normalized_environment, role.value),
            ).fetchone()
            fencing_token = int(sequence["lastFencingToken"]) + 1 if sequence else 1
            self.connection.execute(
                """
                INSERT INTO FoundationLeaseSequences(environment, role, lastFencingToken)
                VALUES (?, ?, ?)
                ON CONFLICT(environment, role) DO UPDATE SET
                  lastFencingToken = excluded.lastFencingToken
                """,
                (normalized_environment, role.value, fencing_token),
            )
            token = secrets.token_urlsafe(32)
            lease_id = (
                f"{normalized_environment}-{role.value}-{fencing_token}-"
                f"{secrets.token_hex(8)}"
            )
            claim = FoundationLeaseClaim(
                leaseId=lease_id,
                environment=normalized_environment,
                role=role,
                ownerId=normalized_owner,
                token=token,
                fencingToken=fencing_token,
                acquiredAt=_iso(now),
                expiresAt=_iso(now + timedelta(seconds=int(ttl_seconds))),
            )
            self.connection.execute(
                """
                INSERT INTO FoundationRuntimeLeases(
                  environment, role, leaseId, ownerId, tokenHash, fencingToken,
                  acquiredAt, heartbeatAt, expiresAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(environment, role) DO UPDATE SET
                  leaseId=excluded.leaseId,
                  ownerId=excluded.ownerId,
                  tokenHash=excluded.tokenHash,
                  fencingToken=excluded.fencingToken,
                  acquiredAt=excluded.acquiredAt,
                  heartbeatAt=excluded.heartbeatAt,
                  expiresAt=excluded.expiresAt
                """,
                (
                    claim.environment,
                    claim.role.value,
                    claim.leaseId,
                    claim.ownerId,
                    _hash(claim.token),
                    claim.fencingToken,
                    claim.acquiredAt,
                    claim.acquiredAt,
                    claim.expiresAt,
                ),
            )
            self._append_event(claim, "lease_acquired", now)
            self.connection.commit()
            return claim
        except Exception:
            self.connection.rollback()
            raise

    def assert_authority(self, claim: FoundationLeaseClaim) -> None:
        row = self.connection.execute(
            """
            SELECT * FROM FoundationRuntimeLeases
            WHERE environment = ? AND role = ?
            """,
            (claim.environment, claim.role.value),
        ).fetchone()
        now = self._now().astimezone(UTC)
        valid = (
            row is not None
            and str(row["leaseId"]) == claim.leaseId
            and str(row["ownerId"]) == claim.ownerId
            and str(row["tokenHash"]) == _hash(claim.token)
            and int(row["fencingToken"]) == claim.fencingToken
            and _parse(str(row["expiresAt"])) > now
        )
        if not valid:
            raise PermissionError("foundation_lease_absent_stale_or_fenced")

    def heartbeat(
        self,
        claim: FoundationLeaseClaim,
        *,
        ttl_seconds: int,
    ) -> FoundationLeaseClaim:
        self.assert_authority(claim)
        now = self._now().astimezone(UTC)
        refreshed = FoundationLeaseClaim(
            leaseId=claim.leaseId,
            environment=claim.environment,
            role=claim.role,
            ownerId=claim.ownerId,
            token=claim.token,
            fencingToken=claim.fencingToken,
            acquiredAt=claim.acquiredAt,
            expiresAt=_iso(now + timedelta(seconds=int(ttl_seconds))),
        )
        with self.connection:
            self.connection.execute(
                """
                UPDATE FoundationRuntimeLeases
                SET heartbeatAt = ?, expiresAt = ?
                WHERE environment = ? AND role = ? AND fencingToken = ?
                """,
                (
                    _iso(now),
                    refreshed.expiresAt,
                    claim.environment,
                    claim.role.value,
                    claim.fencingToken,
                ),
            )
            self._append_event(refreshed, "lease_heartbeat", now)
        return refreshed

    def release(self, claim: FoundationLeaseClaim) -> None:
        self.assert_authority(claim)
        now = self._now().astimezone(UTC)
        with self.connection:
            self._append_event(claim, "lease_released", now)
            self.connection.execute(
                """
                DELETE FROM FoundationRuntimeLeases
                WHERE environment = ? AND role = ? AND tokenHash = ?
                """,
                (claim.environment, claim.role.value, _hash(claim.token)),
            )

    def active_count(self, environment: str | None = None) -> int:
        now = _iso(self._now().astimezone(UTC))
        if environment is None:
            row = self.connection.execute(
                "SELECT COUNT(*) FROM FoundationRuntimeLeases WHERE expiresAt > ?",
                (now,),
            ).fetchone()
        else:
            row = self.connection.execute(
                """
                SELECT COUNT(*) FROM FoundationRuntimeLeases
                WHERE environment = ? AND expiresAt > ?
                """,
                (str(environment).strip().lower(), now),
            ).fetchone()
        return int(row[0])

    def projection(self) -> list[dict[str, object]]:
        rows = self.connection.execute(
            """
            SELECT environment, role, leaseId, ownerId, tokenHash, fencingToken,
                   acquiredAt, heartbeatAt, expiresAt
            FROM FoundationRuntimeLeases
            ORDER BY environment, role
            """
        ).fetchall()
        now = self._now().astimezone(UTC)
        return [
            {
                "environment": str(row["environment"]),
                "role": str(row["role"]),
                "leaseId": str(row["leaseId"]),
                "ownerId": str(row["ownerId"]),
                "tokenHash": str(row["tokenHash"]),
                "fencingToken": int(row["fencingToken"]),
                "acquiredAt": str(row["acquiredAt"]),
                "heartbeatAt": str(row["heartbeatAt"]),
                "expiresAt": str(row["expiresAt"]),
                "expired": _parse(str(row["expiresAt"])) <= now,
            }
            for row in rows
        ]

    def _append_event(
        self,
        claim: FoundationLeaseClaim,
        event_type: str,
        now: datetime,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO FoundationLeaseEvents(
              environment, role, leaseId, ownerId, fencingToken, eventType, createdAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim.environment,
                claim.role.value,
                claim.leaseId,
                claim.ownerId,
                claim.fencingToken,
                event_type,
                _iso(now),
            ),
        )
