"""Credential-free runtime state for the unified automatic execution runner."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ENVIRONMENTS = {"okx_demo", "okx_live"}
RUNTIME_FIELDS = {
    "status",
    "lastHeartbeatAt",
    "nextEvaluationAt",
    "pauseReason",
    "lastError",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _environment(value: str) -> str:
    if value not in ENVIRONMENTS:
        raise ValueError(f"Unsupported automatic execution environment: {value!r}")
    return value


def _reject_sensitive(value: Any, path: str = "payload") -> None:
    forbidden = ("apikey", "secretkey", "passphrase", "credential", "password")
    if isinstance(value, dict):
        for key, child in value.items():
            compact = str(key).replace("_", "").replace("-", "").lower()
            if any(token in compact for token in forbidden) and child not in (None, "", False):
                raise ValueError(f"Credential-like runtime data is forbidden: {path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


class UnifiedAutoExecutionStore:
    def __init__(self, path: Path | str):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(target, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS AutoExecutionRuntime (
              environment TEXT PRIMARY KEY,
              desiredEnabled INTEGER NOT NULL DEFAULT 0,
              armedProcessId TEXT,
              status TEXT NOT NULL DEFAULT 'disabled',
              lastHeartbeatAt TEXT,
              nextEvaluationAt TEXT,
              pauseReason TEXT,
              lastError TEXT,
              updatedAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS AutoExecutionCheckpoints (
              environment TEXT NOT NULL,
              releaseId TEXT NOT NULL,
              timeframe TEXT NOT NULL,
              closedCandleKey TEXT NOT NULL,
              evaluatedAt TEXT NOT NULL,
              PRIMARY KEY(environment, releaseId, timeframe)
            );
            CREATE TABLE IF NOT EXISTS AutoExecutionEvents (
              eventId INTEGER PRIMARY KEY AUTOINCREMENT,
              environment TEXT NOT NULL,
              eventType TEXT NOT NULL,
              payloadJson TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_auto_execution_events_environment
              ON AutoExecutionEvents(environment, eventId DESC);
            CREATE TABLE IF NOT EXISTS AutoExecutionActionRequests (
              requestId TEXT PRIMARY KEY,
              environment TEXT NOT NULL,
              action TEXT NOT NULL,
              payloadHash TEXT NOT NULL,
              status TEXT NOT NULL,
              resultJson TEXT,
              createdAt TEXT NOT NULL,
              completedAt TEXT
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def _ensure_runtime(self, environment: str) -> None:
        environment = _environment(environment)
        with self._lock:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO AutoExecutionRuntime(environment, updatedAt)
                    VALUES (?, ?)
                    """,
                    (environment, _now()),
                )

    def runtime(self, environment: str, *, current_process_id: str | None = None) -> dict[str, Any]:
        environment = _environment(environment)
        with self._lock:
            self._ensure_runtime(environment)
            row = self.connection.execute(
                "SELECT * FROM AutoExecutionRuntime WHERE environment = ?",
                (environment,),
            ).fetchone()
            assert row is not None
            current = str(current_process_id if current_process_id is not None else os.getpid())
            armed_process = str(row["armedProcessId"] or "")
            return {
                "environment": row["environment"],
                "desiredEnabled": bool(row["desiredEnabled"]),
                "armedProcessId": armed_process or None,
                "armedForCurrentProcess": bool(armed_process and armed_process == current),
                "status": row["status"],
                "lastHeartbeatAt": row["lastHeartbeatAt"],
                "nextEvaluationAt": row["nextEvaluationAt"],
                "pauseReason": row["pauseReason"],
                "lastError": row["lastError"],
                "updatedAt": row["updatedAt"],
            }

    def set_desired_enabled(self, environment: str, enabled: bool) -> dict[str, Any]:
        environment = _environment(environment)
        with self._lock:
            self._ensure_runtime(environment)
            status = "waiting_for_arm" if enabled else "disabled"
            with self.connection:
                self.connection.execute(
                    """
                    UPDATE AutoExecutionRuntime
                    SET desiredEnabled = ?, status = ?, pauseReason = NULL,
                        lastError = NULL, updatedAt = ?
                    WHERE environment = ?
                    """,
                    (1 if enabled else 0, status, _now(), environment),
                )
            self.append_event(environment, "desired_state_changed", {"enabled": bool(enabled)})
            return self.runtime(environment)

    def record_arm(self, environment: str, *, process_id: str) -> dict[str, Any]:
        environment = _environment(environment)
        if not str(process_id).strip():
            raise ValueError("A process identity is required to arm automatic execution")
        with self._lock:
            self._ensure_runtime(environment)
            with self.connection:
                self.connection.execute(
                    """
                    UPDATE AutoExecutionRuntime
                    SET armedProcessId = ?, status = 'armed', pauseReason = NULL,
                        lastError = NULL, updatedAt = ?
                    WHERE environment = ?
                    """,
                    (str(process_id), _now(), environment),
                )
            self.append_event(environment, "armed", {"processId": str(process_id)})
            return self.runtime(environment, current_process_id=str(process_id))

    def disarm(self, environment: str, *, reason: str = "operator_request") -> dict[str, Any]:
        environment = _environment(environment)
        with self._lock:
            self._ensure_runtime(environment)
            with self.connection:
                self.connection.execute(
                    """
                    UPDATE AutoExecutionRuntime
                    SET armedProcessId = NULL, status = 'disarmed', pauseReason = ?, updatedAt = ?
                    WHERE environment = ?
                    """,
                    (str(reason), _now(), environment),
                )
            self.append_event(environment, "disarmed", {"reason": str(reason)})
            return self.runtime(environment)

    def update_runtime(self, environment: str, **changes: Any) -> dict[str, Any]:
        environment = _environment(environment)
        unknown = set(changes) - RUNTIME_FIELDS
        if unknown:
            raise ValueError("Unsupported runtime fields: " + ",".join(sorted(unknown)))
        _reject_sensitive(changes)
        with self._lock:
            self._ensure_runtime(environment)
            if not changes:
                return self.runtime(environment)
            assignments = ", ".join(f"{key} = ?" for key in changes)
            values = [changes[key] for key in changes]
            with self.connection:
                self.connection.execute(
                    f"UPDATE AutoExecutionRuntime SET {assignments}, updatedAt = ? WHERE environment = ?",
                    (*values, _now(), environment),
                )
            return self.runtime(environment)

    def save_checkpoint(
        self,
        environment: str,
        release_id: str,
        timeframe: str,
        candle_key: str,
    ) -> None:
        environment = _environment(environment)
        if not release_id or not timeframe or not candle_key:
            raise ValueError("Checkpoint identity is incomplete")
        with self._lock:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO AutoExecutionCheckpoints(
                      environment, releaseId, timeframe, closedCandleKey, evaluatedAt
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(environment, releaseId, timeframe) DO UPDATE SET
                      closedCandleKey = excluded.closedCandleKey,
                      evaluatedAt = excluded.evaluatedAt
                    """,
                    (environment, release_id, timeframe, candle_key, _now()),
                )

    def checkpoint(self, environment: str, release_id: str, timeframe: str) -> str | None:
        environment = _environment(environment)
        with self._lock:
            row = self.connection.execute(
                """
                SELECT closedCandleKey FROM AutoExecutionCheckpoints
                WHERE environment = ? AND releaseId = ? AND timeframe = ?
                """,
                (environment, release_id, timeframe),
            ).fetchone()
            return str(row["closedCandleKey"]) if row else None

    def retire_checkpoints(self, environment: str, release_ids: list[str]) -> int:
        environment = _environment(environment)
        selected = list(dict.fromkeys(str(value) for value in release_ids if str(value)))
        if not selected:
            return 0
        placeholders = ",".join("?" for _ in selected)
        with self._lock:
            with self.connection:
                cursor = self.connection.execute(
                    f"DELETE FROM AutoExecutionCheckpoints WHERE environment = ? AND releaseId IN ({placeholders})",
                    (environment, *selected),
                )
            return int(cursor.rowcount or 0)

    def append_event(self, environment: str, event_type: str, payload: dict[str, Any]) -> None:
        environment = _environment(environment)
        _reject_sensitive(payload)
        with self._lock:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO AutoExecutionEvents(environment, eventType, payloadJson, createdAt)
                    VALUES (?, ?, ?, ?)
                    """,
                    (environment, str(event_type), _json(payload), _now()),
                )

    def list_events(self, environment: str, limit: int = 50) -> list[dict[str, Any]]:
        environment = _environment(environment)
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT eventId, eventType, payloadJson, createdAt
                FROM AutoExecutionEvents
                WHERE environment = ?
                ORDER BY eventId DESC LIMIT ?
                """,
                (environment, max(1, min(int(limit), 500))),
            ).fetchall()
            return [
                {
                    "eventId": int(row["eventId"]),
                    "environment": environment,
                    "eventType": row["eventType"],
                    "payload": json.loads(row["payloadJson"]),
                    "createdAt": row["createdAt"],
                }
                for row in rows
            ]

    def claim_action_request(
        self,
        *,
        request_id: str,
        environment: str,
        action: str,
        payload_hash: str,
    ) -> dict[str, Any]:
        environment = _environment(environment)
        request_id = str(request_id).strip()
        action = str(action).strip()
        payload_hash = str(payload_hash).strip()
        if not request_id or not action or not payload_hash:
            raise ValueError("Action request identity is incomplete")
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM AutoExecutionActionRequests WHERE requestId = ?",
                (request_id,),
            ).fetchone()
            if row is None:
                with self.connection:
                    self.connection.execute(
                        """
                        INSERT INTO AutoExecutionActionRequests(
                          requestId, environment, action, payloadHash, status, createdAt
                        ) VALUES (?, ?, ?, ?, 'pending', ?)
                        """,
                        (request_id, environment, action, payload_hash, _now()),
                    )
                return {"state": "claimed", "requestId": request_id}
            if (
                row["environment"] != environment
                or row["action"] != action
                or row["payloadHash"] != payload_hash
            ):
                return {"state": "conflict", "requestId": request_id}
            if row["status"] == "completed":
                return {
                    "state": "replay",
                    "requestId": request_id,
                    "result": json.loads(row["resultJson"] or "{}"),
                }
            return {"state": "in_progress", "requestId": request_id}

    def complete_action_request(self, request_id: str, result: dict[str, Any]) -> None:
        request_id = str(request_id).strip()
        if not request_id:
            raise ValueError("Action request id is required")
        _reject_sensitive(result)
        with self._lock:
            with self.connection:
                cursor = self.connection.execute(
                    """
                    UPDATE AutoExecutionActionRequests
                    SET status = 'completed', resultJson = ?, completedAt = ?
                    WHERE requestId = ?
                    """,
                    (_json(result), _now(), request_id),
                )
            if not cursor.rowcount:
                raise KeyError(f"Unknown action request: {request_id}")

    def action_request(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM AutoExecutionActionRequests WHERE requestId = ?",
                (str(request_id),),
            ).fetchone()
            if row is None:
                return None
            return {
                "requestId": row["requestId"],
                "environment": row["environment"],
                "action": row["action"],
                "payloadHash": row["payloadHash"],
                "status": row["status"],
                "result": json.loads(row["resultJson"] or "{}"),
                "createdAt": row["createdAt"],
                "completedAt": row["completedAt"],
            }
