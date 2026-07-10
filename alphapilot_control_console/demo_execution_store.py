"""Restart-safe local SQLite ledger for OKX Demo execution only."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class DemoExecutionRecord:
    recordId: str
    idempotencyKey: str
    demoReleaseId: str
    status: str
    signal: dict[str, Any]
    orderPayload: dict[str, Any]
    exchangeOrderId: str | None
    exchangeResponse: dict[str, Any]
    createdAt: str
    updatedAt: str


class DemoExecutionStore:
    def __init__(self, path: Path | str):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS DemoExecutionRecords (
              recordId TEXT PRIMARY KEY,
              idempotencyKey TEXT NOT NULL UNIQUE,
              demoReleaseId TEXT NOT NULL,
              status TEXT NOT NULL,
              signalJson TEXT NOT NULL,
              orderPayloadJson TEXT NOT NULL,
              exchangeOrderId TEXT,
              exchangeResponseJson TEXT NOT NULL,
              createdAt TEXT NOT NULL,
              updatedAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_demo_execution_status
              ON DemoExecutionRecords(status, updatedAt);
            CREATE TABLE IF NOT EXISTS DemoExecutionEvents (
              eventId INTEGER PRIMARY KEY AUTOINCREMENT,
              recordId TEXT,
              eventType TEXT NOT NULL,
              payloadJson TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS DemoRuntimeState (
              stateKey TEXT PRIMARY KEY,
              valueJson TEXT NOT NULL,
              updatedAt TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def create_intent(
        self,
        *,
        idempotencyKey: str,
        demoReleaseId: str,
        signal: dict[str, Any],
        orderPayload: dict[str, Any],
    ) -> DemoExecutionRecord:
        existing = self.get_by_idempotency_key(idempotencyKey)
        if existing:
            if existing.demoReleaseId != demoReleaseId or _json(existing.signal) != _json(signal):
                raise RuntimeError("Idempotency key was reused with different Demo content")
            return existing
        now = _now()
        record_id = "demo_exec_" + hashlib.sha256(idempotencyKey.encode("utf-8")).hexdigest()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO DemoExecutionRecords(
                  recordId, idempotencyKey, demoReleaseId, status, signalJson,
                  orderPayloadJson, exchangeOrderId, exchangeResponseJson, createdAt, updatedAt
                ) VALUES (?, ?, ?, 'prepared', ?, ?, NULL, '{}', ?, ?)
                """,
                (record_id, idempotencyKey, demoReleaseId, _json(signal), _json(orderPayload), now, now),
            )
        self.append_event(record_id, "intent_prepared", {"demoReleaseId": demoReleaseId})
        return self.get_record(record_id)

    def update_record(
        self,
        recordId: str,
        *,
        status: str,
        exchangeOrderId: str | None = None,
        exchangeResponse: dict[str, Any] | None = None,
    ) -> DemoExecutionRecord:
        existing = self.get_record(recordId)
        now = _now()
        with self.connection:
            self.connection.execute(
                """
                UPDATE DemoExecutionRecords
                SET status = ?, exchangeOrderId = ?, exchangeResponseJson = ?, updatedAt = ?
                WHERE recordId = ?
                """,
                (
                    status,
                    exchangeOrderId if exchangeOrderId is not None else existing.exchangeOrderId,
                    _json(exchangeResponse if exchangeResponse is not None else existing.exchangeResponse),
                    now,
                    recordId,
                ),
            )
        self.append_event(recordId, "status_changed", {"from": existing.status, "to": status})
        return self.get_record(recordId)

    def get_record(self, recordId: str) -> DemoExecutionRecord:
        row = self.connection.execute(
            "SELECT * FROM DemoExecutionRecords WHERE recordId = ?", (recordId,)
        ).fetchone()
        if not row:
            raise KeyError(f"Unknown Demo execution record: {recordId}")
        return self._from_row(row)

    def get_by_idempotency_key(self, key: str) -> DemoExecutionRecord | None:
        row = self.connection.execute(
            "SELECT * FROM DemoExecutionRecords WHERE idempotencyKey = ?", (key,)
        ).fetchone()
        return self._from_row(row) if row else None

    def list_records(self, statuses: set[str] | None = None) -> list[DemoExecutionRecord]:
        rows = self.connection.execute(
            "SELECT * FROM DemoExecutionRecords ORDER BY createdAt, recordId"
        ).fetchall()
        records = [self._from_row(row) for row in rows]
        return [record for record in records if not statuses or record.status in statuses]

    def append_event(self, recordId: str | None, eventType: str, payload: dict[str, Any]) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO DemoExecutionEvents(recordId, eventType, payloadJson, createdAt) VALUES (?, ?, ?, ?)",
                (recordId, eventType, _json(payload), _now()),
            )

    def set_runtime_flag(self, key: str, value: Any) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO DemoRuntimeState(stateKey, valueJson, updatedAt) VALUES (?, ?, ?)
                ON CONFLICT(stateKey) DO UPDATE SET valueJson=excluded.valueJson, updatedAt=excluded.updatedAt
                """,
                (key, _json(value), _now()),
            )

    def get_runtime_flag(self, key: str, fallback: Any = None) -> Any:
        row = self.connection.execute(
            "SELECT valueJson FROM DemoRuntimeState WHERE stateKey = ?", (key,)
        ).fetchone()
        return json.loads(row["valueJson"]) if row else fallback

    @staticmethod
    def _from_row(row: sqlite3.Row) -> DemoExecutionRecord:
        return DemoExecutionRecord(
            recordId=row["recordId"],
            idempotencyKey=row["idempotencyKey"],
            demoReleaseId=row["demoReleaseId"],
            status=row["status"],
            signal=json.loads(row["signalJson"]),
            orderPayload=json.loads(row["orderPayloadJson"]),
            exchangeOrderId=row["exchangeOrderId"],
            exchangeResponse=json.loads(row["exchangeResponseJson"]),
            createdAt=row["createdAt"],
            updatedAt=row["updatedAt"],
        )
