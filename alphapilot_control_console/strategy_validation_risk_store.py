"""Persistent append-only risk state for strategy-validation Demo."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .strategy_validation_approval_store import HUMAN_OPERATOR


DEFAULT_RISK_DB = DATA_DIR / "strategy_validation_risk.sqlite"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StrategyValidationRiskStore:
    def __init__(self, path: Path | str = DEFAULT_RISK_DB):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS StrategyValidationRiskEvents (
              eventId TEXT PRIMARY KEY,
              releaseId TEXT,
              eventType TEXT NOT NULL,
              blockersJson TEXT NOT NULL,
              reason TEXT NOT NULL,
              actor TEXT NOT NULL,
              pausedAfter INTEGER NOT NULL,
              createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_strategy_validation_risk_time
              ON StrategyValidationRiskEvents(createdAt);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def append(
        self,
        *,
        eventType: str,
        releaseId: str | None,
        blockers: list[str],
        reason: str,
        actor: str = "strategy_validation_risk_gateway",
        pausedAfter: bool = False,
    ) -> dict[str, Any]:
        event_id = f"strategy_validation_risk_{uuid.uuid4().hex}"
        created_at = _now()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO StrategyValidationRiskEvents(
                  eventId, releaseId, eventType, blockersJson, reason,
                  actor, pausedAfter, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id, releaseId, eventType,
                    json.dumps(blockers, ensure_ascii=False, sort_keys=True),
                    reason, actor, int(pausedAfter), created_at,
                ),
            )
        return {
            "eventId": event_id,
            "releaseId": releaseId,
            "eventType": eventType,
            "blockers": list(blockers),
            "reason": reason,
            "actor": actor,
            "paused": pausedAfter,
            "createdAt": created_at,
        }

    def state(self) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM StrategyValidationRiskEvents ORDER BY createdAt DESC, rowid DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return {"paused": False, "lastEvent": None}
        return {
            "paused": bool(row["pausedAfter"]),
            "lastEvent": {
                **dict(row),
                "blockers": json.loads(row["blockersJson"]),
            },
        }

    def manual_resume(self, *, reason: str, actor: str) -> dict[str, Any]:
        if actor != HUMAN_OPERATOR:
            raise PermissionError("risk pause can only be resumed by human_local_operator")
        if not reason.strip():
            raise ValueError("manual resume reason is required")
        return self.append(
            eventType="manual_resume",
            releaseId=None,
            blockers=[],
            reason=reason.strip(),
            actor=actor,
            pausedAfter=False,
        )

    def list_events(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM StrategyValidationRiskEvents ORDER BY createdAt, rowid"
        ).fetchall()
        return [{**dict(row), "blockers": json.loads(row["blockersJson"])} for row in rows]
