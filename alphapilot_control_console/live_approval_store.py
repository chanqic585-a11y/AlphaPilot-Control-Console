"""Append-only local approval ledger for future Live release review."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


LIVE_APPROVAL_CONFIRMATION = "APPROVE_LIVE_CANDIDATE_REVIEW"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class LiveApprovalAction:
    actionId: str
    packageId: str
    packageHash: str
    action: str
    riskBudget: dict[str, Any]
    actor: str
    confirmationHash: str | None
    createdAt: str


class LiveApprovalStore:
    def __init__(self, path: Path | str):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS LiveApprovalActions (
              actionId TEXT PRIMARY KEY,
              packageId TEXT NOT NULL,
              packageHash TEXT NOT NULL,
              action TEXT NOT NULL,
              riskBudgetJson TEXT NOT NULL,
              actor TEXT NOT NULL,
              confirmationHash TEXT,
              createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_live_approval_package
              ON LiveApprovalActions(packageId, createdAt);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def approve(
        self,
        *,
        packageId: str,
        packageHash: str,
        riskBudget: dict[str, Any],
        confirmation: str,
        actor: str,
    ) -> LiveApprovalAction:
        self._require_manual_actor(actor)
        if confirmation != LIVE_APPROVAL_CONFIRMATION:
            raise PermissionError("The exact manual approval confirmation is required")
        if not packageId or not packageHash or not riskBudget:
            raise ValueError("Package identity and risk budget are required")
        current = self.get_state(packageId, packageHash)
        if current["status"] == "approved_for_future_release_review":
            return self._latest_exact(packageId, packageHash)
        return self._append(
            packageId=packageId,
            packageHash=packageHash,
            action="approved",
            riskBudget=riskBudget,
            actor=actor,
            confirmationHash=hashlib.sha256(confirmation.encode("utf-8")).hexdigest(),
        )

    def revoke(self, *, packageId: str, packageHash: str, actor: str) -> LiveApprovalAction:
        self._require_manual_actor(actor)
        state = self.get_state(packageId, packageHash)
        if state["status"] != "approved_for_future_release_review":
            raise ValueError("Only the current checksum-bound approval can be revoked")
        approved = self._latest_exact(packageId, packageHash)
        return self._append(
            packageId=packageId,
            packageHash=packageHash,
            action="revoked",
            riskBudget=approved.riskBudget,
            actor=actor,
            confirmationHash=None,
        )

    def get_state(self, packageId: str, currentPackageHash: str) -> dict[str, Any]:
        exact = self._latest_row(packageId, currentPackageHash)
        if exact:
            status = "approved_for_future_release_review" if exact["action"] == "approved" else "revoked"
            return {
                "status": status,
                "environment": "okx_live",
                "packageHash": exact["packageHash"],
                "approvedAt": exact["createdAt"] if exact["action"] == "approved" else None,
                "revokedAt": exact["createdAt"] if exact["action"] == "revoked" else None,
                "riskBudget": json.loads(exact["riskBudgetJson"]),
                "executionEnabled": False,
            }
        latest = self.connection.execute(
            "SELECT * FROM LiveApprovalActions WHERE packageId = ? ORDER BY createdAt DESC, rowid DESC LIMIT 1",
            (packageId,),
        ).fetchone()
        if latest:
            return {
                "status": "checksum_changed_approval_invalid",
                "environment": "okx_live",
                "packageHash": latest["packageHash"],
                "approvedAt": None,
                "revokedAt": None,
                "riskBudget": json.loads(latest["riskBudgetJson"]),
                "executionEnabled": False,
            }
        return {
            "status": "awaiting_manual_approval",
            "environment": "okx_live",
            "packageHash": currentPackageHash,
            "approvedAt": None,
            "revokedAt": None,
            "riskBudget": {},
            "executionEnabled": False,
        }

    def list_actions(self) -> list[LiveApprovalAction]:
        rows = self.connection.execute(
            "SELECT * FROM LiveApprovalActions ORDER BY createdAt, rowid"
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def _append(
        self,
        *,
        packageId: str,
        packageHash: str,
        action: str,
        riskBudget: dict[str, Any],
        actor: str,
        confirmationHash: str | None,
    ) -> LiveApprovalAction:
        record = LiveApprovalAction(
            actionId=f"live_approval_{uuid.uuid4().hex}",
            packageId=packageId,
            packageHash=packageHash,
            action=action,
            riskBudget=dict(riskBudget),
            actor=actor,
            confirmationHash=confirmationHash,
            createdAt=_now(),
        )
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO LiveApprovalActions(
                  actionId, packageId, packageHash, action, riskBudgetJson,
                  actor, confirmationHash, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.actionId,
                    record.packageId,
                    record.packageHash,
                    record.action,
                    _json(record.riskBudget),
                    record.actor,
                    record.confirmationHash,
                    record.createdAt,
                ),
            )
        return record

    def _latest_exact(self, packageId: str, packageHash: str) -> LiveApprovalAction:
        row = self._latest_row(packageId, packageHash)
        if not row:
            raise KeyError("No checksum-bound approval action exists")
        return self._from_row(row)

    def _latest_row(self, packageId: str, packageHash: str) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT * FROM LiveApprovalActions
            WHERE packageId = ? AND packageHash = ?
            ORDER BY createdAt DESC, rowid DESC LIMIT 1
            """,
            (packageId, packageHash),
        ).fetchone()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> LiveApprovalAction:
        return LiveApprovalAction(
            actionId=row["actionId"],
            packageId=row["packageId"],
            packageHash=row["packageHash"],
            action=row["action"],
            riskBudget=json.loads(row["riskBudgetJson"]),
            actor=row["actor"],
            confirmationHash=row["confirmationHash"],
            createdAt=row["createdAt"],
        )

    @staticmethod
    def _require_manual_actor(actor: str) -> None:
        if actor != "user_manual":
            raise PermissionError("Live candidate approval can only be written by user_manual")
