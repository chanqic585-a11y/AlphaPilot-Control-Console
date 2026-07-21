"""Append-only operator intervention requests without implicit execution."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR


MANUAL_INTERVENTION_STORE_PATH = DATA_DIR / "manual_interventions.sqlite"
ALLOWED_ENVIRONMENTS = {"okx_demo", "live_canary", "live_standard"}
ALLOWED_ACTIONS = {
    "tighten_stop",
    "conservative_take_profit",
    "partial_reduce",
    "close_position",
    "pause_instrument",
    "pause_strategy",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_tightened_stop(before: dict[str, Any], after: dict[str, Any]) -> None:
    side = str(after.get("side") or before.get("side") or "").lower()
    old_stop = float(before.get("stopLoss") or 0)
    new_stop = float(after.get("stopLoss") or 0)
    if side not in {"long", "short"} or min(old_stop, new_stop) <= 0:
        raise ValueError("tighten_stop requires side and positive stop prices")
    if (side == "long" and new_stop < old_stop) or (side == "short" and new_stop > old_stop):
        raise ValueError("manual stop intervention cannot widen risk")


class ManualInterventionStore:
    def __init__(self, path: Path | str = MANUAL_INTERVENTION_STORE_PATH):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS ManualInterventionEvents (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              interventionId TEXT NOT NULL UNIQUE,
              environment TEXT NOT NULL,
              action TEXT NOT NULL,
              operator TEXT NOT NULL,
              strategyId TEXT NOT NULL,
              instrumentId TEXT,
              positionId TEXT,
              beforeJson TEXT NOT NULL,
              afterJson TEXT NOT NULL,
              reason TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_manual_intervention_environment
              ON ManualInterventionEvents(environment, sequence);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def record(
        self,
        *,
        environment: str,
        action: str,
        operator: str,
        strategy_id: str,
        instrument_id: str | None,
        position_id: str | None,
        before: dict[str, Any],
        after: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        if environment not in ALLOWED_ENVIRONMENTS:
            raise ValueError("unsupported manual intervention environment")
        if action not in ALLOWED_ACTIONS:
            raise ValueError("unsupported manual intervention action")
        if operator != "user_manual":
            raise PermissionError("manual intervention requires user_manual operator")
        if not str(strategy_id or "").strip() or not str(reason or "").strip():
            raise ValueError("manual intervention strategy and reason are required")
        if action == "tighten_stop":
            _validate_tightened_stop(before, after)
        intervention_id = "manual_intervention_" + uuid.uuid4().hex
        created_at = _now()
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO ManualInterventionEvents(
                  interventionId, environment, action, operator, strategyId,
                  instrumentId, positionId, beforeJson, afterJson, reason, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intervention_id,
                    environment,
                    action,
                    operator,
                    str(strategy_id),
                    str(instrument_id) if instrument_id else None,
                    str(position_id) if position_id else None,
                    _json(before),
                    _json(after),
                    str(reason),
                    created_at,
                ),
            )
        return {
            "sequence": int(cursor.lastrowid),
            "interventionId": intervention_id,
            "environment": environment,
            "action": action,
            "operator": operator,
            "strategyId": str(strategy_id),
            "instrumentId": str(instrument_id) if instrument_id else None,
            "positionId": str(position_id) if position_id else None,
            "before": before,
            "after": after,
            "reason": str(reason),
            "createdAt": created_at,
            "manualIntervention": True,
            "executionEnabled": False,
        }

    def list_events(self, environment: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM ManualInterventionEvents"
        values: tuple[str, ...] = ()
        if environment:
            query += " WHERE environment = ?"
            values = (environment,)
        query += " ORDER BY sequence"
        rows = self.connection.execute(query, values).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "sequence": int(row["sequence"]),
            "interventionId": row["interventionId"],
            "environment": row["environment"],
            "action": row["action"],
            "operator": row["operator"],
            "strategyId": row["strategyId"],
            "instrumentId": row["instrumentId"],
            "positionId": row["positionId"],
            "before": json.loads(row["beforeJson"]),
            "after": json.loads(row["afterJson"]),
            "reason": row["reason"],
            "createdAt": row["createdAt"],
            "manualIntervention": True,
            "executionEnabled": False,
        }


def record_manual_intervention(payload: dict[str, Any]) -> dict[str, Any]:
    store = ManualInterventionStore(MANUAL_INTERVENTION_STORE_PATH)
    try:
        event = store.record(
            environment=str(payload.get("environment") or ""),
            action=str(payload.get("action") or ""),
            operator=str(payload.get("operator") or ""),
            strategy_id=str(payload.get("strategyId") or ""),
            instrument_id=payload.get("instrumentId"),
            position_id=payload.get("positionId"),
            before=payload.get("before") if isinstance(payload.get("before"), dict) else {},
            after=payload.get("after") if isinstance(payload.get("after"), dict) else {},
            reason=str(payload.get("reason") or ""),
        )
        events = store.list_events(str(payload.get("environment") or ""))[-50:]
    finally:
        store.close()
    return {"ok": True, "event": event, "recentEvents": events}


def build_manual_intervention_status() -> dict[str, Any]:
    store = ManualInterventionStore(MANUAL_INTERVENTION_STORE_PATH)
    try:
        events = store.list_events()[-50:]
    finally:
        store.close()
    return {
        "ok": True,
        "recentEvents": events,
        "allowedEnvironments": sorted(ALLOWED_ENVIRONMENTS),
        "allowedActions": sorted(ALLOWED_ACTIONS),
        "appendOnly": True,
        "executionEnabled": False,
        "credentialsStored": False,
        "withdrawEnabled": False,
    }
