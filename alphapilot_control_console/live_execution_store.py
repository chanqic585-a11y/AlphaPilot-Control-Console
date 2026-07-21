"""Restart-safe local ledger for checksum-bound OKX Live Canary execution."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR


LIVE_EXECUTION_STORE_PATH = DATA_DIR / "live_execution.sqlite"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class LiveExecutionRecord:
    recordId: str
    idempotencyKey: str
    liveReleaseId: str
    liveReleaseHash: str
    riskProfileId: str
    riskProfileHash: str
    strategyCandidateId: str
    instrumentId: str
    status: str
    signal: dict[str, Any]
    orderPayload: dict[str, Any]
    exchangeOrderId: str | None
    exchangeResponse: dict[str, Any]
    createdAt: str
    updatedAt: str


class LiveExecutionStore:
    def __init__(self, path: Path | str = LIVE_EXECUTION_STORE_PATH):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS LiveExecutionRecords (
              recordId TEXT PRIMARY KEY,
              idempotencyKey TEXT NOT NULL UNIQUE,
              liveReleaseId TEXT NOT NULL,
              liveReleaseHash TEXT NOT NULL,
              riskProfileId TEXT NOT NULL,
              riskProfileHash TEXT NOT NULL,
              strategyCandidateId TEXT NOT NULL,
              instrumentId TEXT NOT NULL,
              status TEXT NOT NULL,
              signalJson TEXT NOT NULL,
              orderPayloadJson TEXT NOT NULL,
              exchangeOrderId TEXT,
              exchangeResponseJson TEXT NOT NULL,
              createdAt TEXT NOT NULL,
              updatedAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_live_execution_status
              ON LiveExecutionRecords(status, updatedAt);
            CREATE INDEX IF NOT EXISTS idx_live_execution_release
              ON LiveExecutionRecords(liveReleaseId, updatedAt);
            CREATE TABLE IF NOT EXISTS LiveExecutionEvents (
              eventId INTEGER PRIMARY KEY AUTOINCREMENT,
              recordId TEXT,
              eventType TEXT NOT NULL,
              payloadJson TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS LiveRuntimeState (
              stateKey TEXT PRIMARY KEY,
              valueJson TEXT NOT NULL,
              updatedAt TEXT NOT NULL
            );
            """
        )
        self.connection.commit()
        if self.get_runtime_flag("killSwitch") is None:
            self.set_runtime_flag("killSwitch", True)
            self.set_runtime_flag("paused", True)
            self.set_runtime_flag("pauseReason", "initial_fail_closed_state")

    def close(self) -> None:
        self.connection.close()

    def create_intent(
        self,
        *,
        idempotencyKey: str,
        liveReleaseId: str,
        liveReleaseHash: str,
        riskProfileId: str,
        riskProfileHash: str,
        strategyCandidateId: str,
        instrumentId: str,
        signal: dict[str, Any],
        orderPayload: dict[str, Any],
    ) -> LiveExecutionRecord:
        existing = self.get_by_idempotency_key(idempotencyKey)
        if existing:
            identity_matches = (
                existing.liveReleaseId == liveReleaseId
                and existing.liveReleaseHash == liveReleaseHash
                and existing.riskProfileId == riskProfileId
                and existing.riskProfileHash == riskProfileHash
                and _json(existing.signal) == _json(signal)
                and _json(existing.orderPayload) == _json(orderPayload)
            )
            if not identity_matches:
                raise RuntimeError("Live idempotency key was reused with different content")
            return existing
        now = _now()
        record_id = "live_exec_" + hashlib.sha256(idempotencyKey.encode("utf-8")).hexdigest()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO LiveExecutionRecords(
                  recordId, idempotencyKey, liveReleaseId, liveReleaseHash,
                  riskProfileId, riskProfileHash, strategyCandidateId,
                  instrumentId, status, signalJson, orderPayloadJson,
                  exchangeOrderId, exchangeResponseJson, createdAt, updatedAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'prepared', ?, ?, NULL, '{}', ?, ?)
                """,
                (
                    record_id, idempotencyKey, liveReleaseId, liveReleaseHash,
                    riskProfileId, riskProfileHash, strategyCandidateId,
                    instrumentId, _json(signal), _json(orderPayload), now, now,
                ),
            )
        self.append_event(record_id, "intent_prepared", {
            "liveReleaseId": liveReleaseId,
            "riskProfileId": riskProfileId,
            "strategyCandidateId": strategyCandidateId,
            "instrumentId": instrumentId,
        })
        return self.get_record(record_id)

    def update_record(
        self,
        recordId: str,
        *,
        status: str,
        exchangeOrderId: str | None = None,
        exchangeResponse: dict[str, Any] | None = None,
    ) -> LiveExecutionRecord:
        existing = self.get_record(recordId)
        now = _now()
        with self.connection:
            self.connection.execute(
                """
                UPDATE LiveExecutionRecords
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

    def get_record(self, recordId: str) -> LiveExecutionRecord:
        row = self.connection.execute(
            "SELECT * FROM LiveExecutionRecords WHERE recordId = ?", (recordId,)
        ).fetchone()
        if not row:
            raise KeyError(f"Unknown Live execution record: {recordId}")
        return self._from_row(row)

    def get_by_idempotency_key(self, key: str) -> LiveExecutionRecord | None:
        row = self.connection.execute(
            "SELECT * FROM LiveExecutionRecords WHERE idempotencyKey = ?", (key,)
        ).fetchone()
        return self._from_row(row) if row else None

    def list_records(self, statuses: set[str] | None = None) -> list[LiveExecutionRecord]:
        rows = self.connection.execute(
            "SELECT * FROM LiveExecutionRecords ORDER BY createdAt, recordId"
        ).fetchall()
        records = [self._from_row(row) for row in rows]
        return [record for record in records if not statuses or record.status in statuses]

    def append_event(self, recordId: str | None, eventType: str, payload: dict[str, Any]) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO LiveExecutionEvents(recordId, eventType, payloadJson, createdAt) VALUES (?, ?, ?, ?)",
                (recordId, eventType, _json(payload), _now()),
            )

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM LiveExecutionEvents ORDER BY eventId DESC LIMIT ?", (int(limit),)
        ).fetchall()
        return [
            {
                "eventId": row["eventId"],
                "recordId": row["recordId"],
                "eventType": row["eventType"],
                "payload": json.loads(row["payloadJson"]),
                "createdAt": row["createdAt"],
            }
            for row in rows
        ]

    def set_runtime_flag(self, key: str, value: Any) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO LiveRuntimeState(stateKey, valueJson, updatedAt) VALUES (?, ?, ?)
                ON CONFLICT(stateKey) DO UPDATE SET valueJson=excluded.valueJson, updatedAt=excluded.updatedAt
                """,
                (key, _json(value), _now()),
            )

    def get_runtime_flag(self, key: str, fallback: Any = None) -> Any:
        row = self.connection.execute(
            "SELECT valueJson FROM LiveRuntimeState WHERE stateKey = ?", (key,)
        ).fetchone()
        return json.loads(row["valueJson"]) if row else fallback

    def runtime_state(self) -> dict[str, Any]:
        return {
            "environment": "okx_live",
            "withdrawAllowed": False,
            "killSwitchActive": bool(self.get_runtime_flag("killSwitch", True)),
            "paused": bool(self.get_runtime_flag("paused", True)),
            "pauseReason": str(self.get_runtime_flag("pauseReason", "initial_fail_closed_state")),
            "lastReconciliationMatched": bool(self.get_runtime_flag("lastReconciliationMatched", False)),
            "lastReconciledAt": self.get_runtime_flag("lastReconciledAt"),
        }

    @staticmethod
    def _from_row(row: sqlite3.Row) -> LiveExecutionRecord:
        return LiveExecutionRecord(
            recordId=row["recordId"],
            idempotencyKey=row["idempotencyKey"],
            liveReleaseId=row["liveReleaseId"],
            liveReleaseHash=row["liveReleaseHash"],
            riskProfileId=row["riskProfileId"],
            riskProfileHash=row["riskProfileHash"],
            strategyCandidateId=row["strategyCandidateId"],
            instrumentId=row["instrumentId"],
            status=row["status"],
            signal=json.loads(row["signalJson"]),
            orderPayload=json.loads(row["orderPayloadJson"]),
            exchangeOrderId=row["exchangeOrderId"],
            exchangeResponse=json.loads(row["exchangeResponseJson"]),
            createdAt=row["createdAt"],
            updatedAt=row["updatedAt"],
        )
