"""Fail-closed Runtime admission kept independent from human approval."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .strategy_validation_approval_store import HUMAN_OPERATOR, StrategyValidationApprovalStore
from .strategy_validation_release_store import StrategyValidationReleaseStore


DEFAULT_RUNTIME_DB = DATA_DIR / "strategy_validation_runtime.sqlite"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StrategyValidationRuntimeAdmission:
    def __init__(
        self,
        path: Path | str = DEFAULT_RUNTIME_DB,
        release_store: StrategyValidationReleaseStore | None = None,
        approval_store: StrategyValidationApprovalStore | None = None,
    ):
        if release_store is None or approval_store is None:
            raise ValueError("release and approval stores are required")
        self.release_store = release_store
        self.approval_store = approval_store
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS StrategyValidationRuntimeActions (
              actionId INTEGER PRIMARY KEY AUTOINCREMENT,
              action TEXT NOT NULL,
              actor TEXT NOT NULL,
              reason TEXT NOT NULL,
              createdAt TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def arm(self, *, reason: str, actor: str) -> dict[str, Any]:
        return self._append("arm", reason, actor)

    def disarm(self, *, reason: str, actor: str) -> dict[str, Any]:
        return self._append("disarm", reason, actor)

    def state(self) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM StrategyValidationRuntimeActions ORDER BY actionId DESC LIMIT 1"
        ).fetchone()
        return {
            "armed": bool(row and row["action"] == "arm"),
            "lastAction": dict(row) if row else None,
        }
    def evaluate(
        self,
        release_id: str,
        *,
        universeFresh: bool,
        riskPaused: bool = False,
    ) -> dict[str, Any]:
        try:
            release = self.release_store.require(release_id)
            self.release_store.payload(release_id)
        except (KeyError, ValueError) as error:
            return {"eligible": False, "status": "release_invalid", "reason": str(error)}
        approval = self.approval_store.get_state(release_id)
        if not approval.get("approved"):
            return {"eligible": False, "status": "not_approved", "releaseId": release_id}
        if not self.state()["armed"]:
            return {"eligible": False, "status": "not_armed", "releaseId": release_id}
        if not universeFresh:
            return {"eligible": False, "status": "universe_stale", "releaseId": release_id}
        if riskPaused:
            return {"eligible": False, "status": "risk_paused", "releaseId": release_id}
        return {
            "eligible": True,
            "status": "eligible",
            "releaseId": release_id,
            "releaseHash": release["releaseHash"],
            "riskConfigHash": release["riskConfigHash"],
        }

    def _append(self, action: str, reason: str, actor: str) -> dict[str, Any]:
        if actor != HUMAN_OPERATOR:
            raise PermissionError("Runtime ARM actions require human_local_operator")
        if not reason.strip():
            raise ValueError("Runtime action reason is required")
        created_at = _now()
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO StrategyValidationRuntimeActions(action, actor, reason, createdAt) VALUES (?, ?, ?, ?)",
                (action, actor, reason.strip(), created_at),
            )
        return {
            "actionId": cursor.lastrowid,
            "action": action,
            "actor": actor,
            "reason": reason.strip(),
            "createdAt": created_at,
            "armed": action == "arm",
            "approvalCreated": False,
            "ordersCreated": 0,
        }
