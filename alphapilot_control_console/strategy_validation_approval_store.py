"""Append-only, hash-bound approval ledger for strategy-validation Demo."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .strategy_validation_hashing import stable_hash
from .strategy_validation_release_store import StrategyValidationReleaseStore


DEFAULT_APPROVAL_DB = DATA_DIR / "strategy_validation_approvals.sqlite"
HUMAN_OPERATOR = "human_local_operator"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StrategyValidationApprovalStore:
    def __init__(
        self,
        path: Path | str = DEFAULT_APPROVAL_DB,
        release_store: StrategyValidationReleaseStore | None = None,
    ):
        if release_store is None:
            raise ValueError("release store is required for hash-bound approval")
        self.release_store = release_store
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS StrategyValidationApprovalActions (
              approvalId TEXT PRIMARY KEY,
              releaseId TEXT NOT NULL,
              releaseHash TEXT NOT NULL,
              riskConfigHash TEXT NOT NULL,
              action TEXT NOT NULL,
              actor TEXT NOT NULL,
              reason TEXT NOT NULL,
              createdAt TEXT NOT NULL,
              previousApprovalHash TEXT,
              recordHash TEXT NOT NULL UNIQUE
            );
            CREATE INDEX IF NOT EXISTS idx_strategy_validation_approval_release
              ON StrategyValidationApprovalActions(releaseId, createdAt);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def approve(self, **kwargs: Any) -> dict[str, Any]:
        return self._append(action="approve", **kwargs)

    def revoke(self, **kwargs: Any) -> dict[str, Any]:
        state = self.get_state(str(kwargs.get("releaseId") or ""))
        if not state["approved"]:
            raise ValueError("only a current approval can be revoked")
        return self._append(action="revoke", **kwargs)

    def _append(
        self,
        *,
        releaseId: str,
        releaseHash: str,
        riskConfigHash: str,
        reason: str,
        actor: str,
        action: str,
    ) -> dict[str, Any]:
        if actor != HUMAN_OPERATOR:
            raise PermissionError("approval actions require human_local_operator")
        if not reason.strip():
            raise ValueError("approval reason is required")
        release = self.release_store.require(releaseId)
        self.release_store.payload(releaseId)
        if release["releaseHash"] != releaseHash:
            raise ValueError("release hash changed or is stale")
        if release["riskConfigHash"] != riskConfigHash:
            raise ValueError("risk config hash changed or is stale")
        current = self.get_state(releaseId)
        if action == "approve" and current["approved"]:
            return current
        previous = self._latest_row(releaseId)
        previous_hash = previous["recordHash"] if previous else None
        created_at = _now()
        approval_id = f"strategy_validation_approval_{uuid.uuid4().hex}"
        body = {
            "approvalId": approval_id,
            "releaseId": releaseId,
            "releaseHash": releaseHash,
            "riskConfigHash": riskConfigHash,
            "action": action,
            "actor": actor,
            "reason": reason.strip(),
            "createdAt": created_at,
            "previousApprovalHash": previous_hash,
        }
        record_hash = stable_hash(body, "strategy_validation_approval")
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO StrategyValidationApprovalActions(
                  approvalId, releaseId, releaseHash, riskConfigHash, action,
                  actor, reason, createdAt, previousApprovalHash, recordHash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id, releaseId, releaseHash, riskConfigHash, action,
                    actor, reason.strip(), created_at, previous_hash, record_hash,
                ),
            )
        return {
            **body,
            "recordHash": record_hash,
            "approved": action == "approve",
            "runtimeArmed": False,
        }

    def get_state(self, release_id: str) -> dict[str, Any]:
        row = self._latest_row(release_id)
        if row is None:
            return {"releaseId": release_id, "approved": False, "status": "waiting_approval"}
        release = self.release_store.get(release_id)
        current_hashes = bool(
            release
            and release["releaseHash"] == row["releaseHash"]
            and release["riskConfigHash"] == row["riskConfigHash"]
        )
        approved = row["action"] == "approve" and current_hashes
        return {
            **dict(row),
            "approved": approved,
            "status": "approved" if approved else ("revoked" if row["action"] == "revoke" else "stale"),
            "runtimeArmed": False,
        }

    def list_actions(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM StrategyValidationApprovalActions ORDER BY createdAt, rowid"
        ).fetchall()
        return [dict(row) for row in rows]

    def _latest_row(self, release_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT * FROM StrategyValidationApprovalActions
            WHERE releaseId = ? ORDER BY createdAt DESC, rowid DESC LIMIT 1
            """,
            (release_id,),
        ).fetchone()
