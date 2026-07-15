"""Isolated restart-safe SQLite ledger for Demo engineering smoke only."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_SENSITIVE_PARTS = ("apikey", "secretkey", "passphrase", "password", "credential", "accesstoken")
_TERMINAL_STATUSES = {"completed", "failed", "canceled"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _reject_sensitive(value: Any, path: str = "engineeringSmoke") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            compact = str(key).replace("_", "").replace("-", "").lower()
            if any(part in compact for part in _SENSITIVE_PARTS):
                raise ValueError(f"Sensitive field is forbidden in engineering smoke ledger: {path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


@dataclass(frozen=True)
class DemoEngineeringSmokeRecord:
    runId: str
    idempotencyKey: str
    releaseId: str
    releaseHash: str
    instrumentId: str
    status: str
    attemptCount: int
    duplicateAttemptCount: int
    orderPayload: dict[str, Any]
    exchangeOrderId: str | None
    orderStatus: str
    positionStatus: str
    exitStatus: str
    reconciliationStatus: str
    exchangeProjection: dict[str, Any]
    errorCode: str | None
    errorMessage: str | None
    createdAt: str
    updatedAt: str


@dataclass(frozen=True)
class CreateRunResult:
    record: DemoEngineeringSmokeRecord
    created: bool


class DemoEngineeringSmokeStore:
    def __init__(self, path: Path | str):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.path = target
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS DemoEngineeringSmokeRuns (
              runId TEXT PRIMARY KEY,
              idempotencyKey TEXT NOT NULL UNIQUE,
              releaseId TEXT NOT NULL,
              releaseHash TEXT NOT NULL,
              instrumentId TEXT NOT NULL,
              status TEXT NOT NULL,
              attemptCount INTEGER NOT NULL DEFAULT 0,
              duplicateAttemptCount INTEGER NOT NULL DEFAULT 0,
              orderPayloadJson TEXT NOT NULL,
              exchangeOrderId TEXT,
              orderStatus TEXT NOT NULL DEFAULT 'not_started',
              positionStatus TEXT NOT NULL DEFAULT 'not_checked',
              exitStatus TEXT NOT NULL DEFAULT 'not_started',
              reconciliationStatus TEXT NOT NULL DEFAULT 'not_started',
              exchangeProjectionJson TEXT NOT NULL DEFAULT '{}',
              errorCode TEXT,
              errorMessage TEXT,
              createdAt TEXT NOT NULL,
              updatedAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_demo_engineering_smoke_status
              ON DemoEngineeringSmokeRuns(status, updatedAt);
            CREATE TABLE IF NOT EXISTS DemoEngineeringSmokeEvents (
              eventId INTEGER PRIMARY KEY AUTOINCREMENT,
              runId TEXT,
              eventType TEXT NOT NULL,
              payloadJson TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def create_or_get_run(
        self,
        *,
        idempotencyKey: str,
        releaseId: str,
        releaseHash: str,
        instrumentId: str,
        orderPayload: dict[str, Any],
    ) -> CreateRunResult:
        _reject_sensitive(orderPayload, "orderPayload")
        existing = self.get_by_idempotency_key(idempotencyKey)
        if existing is not None:
            if (
                existing.releaseId != releaseId
                or existing.releaseHash != releaseHash
                or existing.instrumentId != instrumentId
                or _json(existing.orderPayload) != _json(orderPayload)
            ):
                raise RuntimeError("Engineering smoke idempotency key was reused with different content")
            with self.connection:
                self.connection.execute(
                    "UPDATE DemoEngineeringSmokeRuns SET duplicateAttemptCount = duplicateAttemptCount + 1, updatedAt = ? WHERE runId = ?",
                    (_now(), existing.runId),
                )
            return CreateRunResult(self.get_run(existing.runId), False)
        run_id = "demo_smoke_" + hashlib.sha256(idempotencyKey.encode("utf-8")).hexdigest()[:32]
        now = _now()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO DemoEngineeringSmokeRuns(
                  runId, idempotencyKey, releaseId, releaseHash, instrumentId,
                  status, orderPayloadJson, createdAt, updatedAt
                ) VALUES (?, ?, ?, ?, ?, 'prepared', ?, ?, ?)
                """,
                (run_id, idempotencyKey, releaseId, releaseHash, instrumentId, _json(orderPayload), now, now),
            )
        return CreateRunResult(self.get_run(run_id), True)

    def increment_attempt(self, runId: str, *, maximumAttempts: int) -> DemoEngineeringSmokeRecord:
        record = self.get_run(runId)
        if record.attemptCount >= maximumAttempts:
            raise RuntimeError("Demo engineering smoke retry limit reached")
        with self.connection:
            self.connection.execute(
                "UPDATE DemoEngineeringSmokeRuns SET attemptCount = attemptCount + 1, updatedAt = ? WHERE runId = ?",
                (_now(), runId),
            )
        return self.get_run(runId)

    def update_run(self, runId: str, **changes: Any) -> DemoEngineeringSmokeRecord:
        allowed = {
            "status": "status",
            "exchangeOrderId": "exchangeOrderId",
            "orderStatus": "orderStatus",
            "positionStatus": "positionStatus",
            "exitStatus": "exitStatus",
            "reconciliationStatus": "reconciliationStatus",
            "exchangeProjection": "exchangeProjectionJson",
            "errorCode": "errorCode",
            "errorMessage": "errorMessage",
        }
        unknown = set(changes) - set(allowed)
        if unknown:
            raise ValueError("Unsupported engineering smoke fields: " + ",".join(sorted(unknown)))
        if "exchangeProjection" in changes:
            _reject_sensitive(changes["exchangeProjection"], "exchangeProjection")
        assignments: list[str] = []
        values: list[Any] = []
        for name, value in changes.items():
            column = allowed[name]
            assignments.append(f"{column} = ?")
            values.append(_json(value) if name == "exchangeProjection" else value)
        if assignments:
            assignments.append("updatedAt = ?")
            values.append(_now())
            values.append(runId)
            with self.connection:
                self.connection.execute(
                    f"UPDATE DemoEngineeringSmokeRuns SET {', '.join(assignments)} WHERE runId = ?",
                    values,
                )
        return self.get_run(runId)

    def append_event(self, runId: str | None, eventType: str, payload: dict[str, Any]) -> None:
        _reject_sensitive(payload, "eventPayload")
        with self.connection:
            self.connection.execute(
                "INSERT INTO DemoEngineeringSmokeEvents(runId, eventType, payloadJson, createdAt) VALUES (?, ?, ?, ?)",
                (runId, eventType, _json(payload), _now()),
            )

    def get_run(self, runId: str) -> DemoEngineeringSmokeRecord:
        row = self.connection.execute(
            "SELECT * FROM DemoEngineeringSmokeRuns WHERE runId = ?", (runId,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown Demo engineering smoke run: {runId}")
        return self._from_row(row)

    def get_by_idempotency_key(self, key: str) -> DemoEngineeringSmokeRecord | None:
        row = self.connection.execute(
            "SELECT * FROM DemoEngineeringSmokeRuns WHERE idempotencyKey = ?", (key,)
        ).fetchone()
        return self._from_row(row) if row else None

    def list_runs(self) -> list[DemoEngineeringSmokeRecord]:
        rows = self.connection.execute(
            "SELECT * FROM DemoEngineeringSmokeRuns ORDER BY createdAt, runId"
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_recoverable_runs(self) -> list[DemoEngineeringSmokeRecord]:
        return [record for record in self.list_runs() if record.status not in _TERMINAL_STATUSES]

    def list_events(self, runId: str | None = None) -> list[dict[str, Any]]:
        if runId is None:
            rows = self.connection.execute(
                "SELECT * FROM DemoEngineeringSmokeEvents ORDER BY eventId"
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM DemoEngineeringSmokeEvents WHERE runId = ? ORDER BY eventId", (runId,)
            ).fetchall()
        return [
            {
                "eventId": int(row["eventId"]),
                "runId": row["runId"],
                "eventType": row["eventType"],
                "payload": json.loads(row["payloadJson"]),
                "createdAt": row["createdAt"],
            }
            for row in rows
        ]

    def build_summary(self) -> dict[str, Any]:
        records = self.list_runs()
        return {
            "runCount": len(records),
            "completedCount": sum(record.status == "completed" for record in records),
            "failedCount": sum(record.status == "failed" for record in records),
            "activeCount": sum(record.status not in _TERMINAL_STATUSES for record in records),
            "orderAttemptCount": sum(record.attemptCount for record in records),
            "duplicateAttemptCount": sum(record.duplicateAttemptCount for record in records),
            "latestRun": self._project(records[-1]) if records else None,
        }

    @staticmethod
    def _project(record: DemoEngineeringSmokeRecord) -> dict[str, Any]:
        return {
            "runId": record.runId,
            "releaseId": record.releaseId,
            "instrumentId": record.instrumentId,
            "status": record.status,
            "attemptCount": record.attemptCount,
            "duplicateAttemptCount": record.duplicateAttemptCount,
            "exchangeOrderId": record.exchangeOrderId,
            "orderStatus": record.orderStatus,
            "positionStatus": record.positionStatus,
            "exitStatus": record.exitStatus,
            "reconciliationStatus": record.reconciliationStatus,
            "errorCode": record.errorCode,
            "errorMessage": record.errorMessage,
            "createdAt": record.createdAt,
            "updatedAt": record.updatedAt,
        }

    @staticmethod
    def _from_row(row: sqlite3.Row) -> DemoEngineeringSmokeRecord:
        return DemoEngineeringSmokeRecord(
            runId=row["runId"],
            idempotencyKey=row["idempotencyKey"],
            releaseId=row["releaseId"],
            releaseHash=row["releaseHash"],
            instrumentId=row["instrumentId"],
            status=row["status"],
            attemptCount=int(row["attemptCount"]),
            duplicateAttemptCount=int(row["duplicateAttemptCount"]),
            orderPayload=json.loads(row["orderPayloadJson"]),
            exchangeOrderId=row["exchangeOrderId"],
            orderStatus=row["orderStatus"],
            positionStatus=row["positionStatus"],
            exitStatus=row["exitStatus"],
            reconciliationStatus=row["reconciliationStatus"],
            exchangeProjection=json.loads(row["exchangeProjectionJson"]),
            errorCode=row["errorCode"],
            errorMessage=row["errorMessage"],
            createdAt=row["createdAt"],
            updatedAt=row["updatedAt"],
        )
