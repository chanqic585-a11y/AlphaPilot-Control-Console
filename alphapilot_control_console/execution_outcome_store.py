"""Immutable closed Demo/Live execution outcomes for offline research feedback."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR


EXECUTION_OUTCOME_STORE_PATH = DATA_DIR / "execution_outcomes.sqlite"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@dataclass(frozen=True)
class FormalExecutionOutcome:
    executionOutcomeId: str
    environment: str
    sourceRecordId: str
    releaseId: str
    releaseHash: str
    strategyCandidateId: str
    dataSnapshotId: str
    outcome: dict[str, Any]
    contentHash: str
    createdAt: str


class ExecutionOutcomeStore:
    def __init__(self, path: Path | str = EXECUTION_OUTCOME_STORE_PATH):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(target)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS FormalExecutionOutcomes (
              executionOutcomeId TEXT PRIMARY KEY,
              environment TEXT NOT NULL,
              sourceRecordId TEXT NOT NULL,
              releaseId TEXT NOT NULL,
              releaseHash TEXT NOT NULL,
              strategyCandidateId TEXT NOT NULL,
              dataSnapshotId TEXT NOT NULL,
              outcomeJson TEXT NOT NULL,
              contentHash TEXT NOT NULL,
              createdAt TEXT NOT NULL,
              UNIQUE(environment, sourceRecordId)
            );
            CREATE INDEX IF NOT EXISTS idx_formal_execution_outcomes_release
              ON FormalExecutionOutcomes(environment, releaseId, createdAt);
            CREATE INDEX IF NOT EXISTS idx_formal_execution_outcomes_candidate
              ON FormalExecutionOutcomes(strategyCandidateId, createdAt);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def record_closed(self, draft: dict[str, Any]) -> FormalExecutionOutcome:
        environment = str(draft.get("environment") or "")
        if environment not in {"okx_demo", "live"}:
            raise ValueError("Execution outcome environment must be okx_demo or live")
        required_text = (
            "sourceRecordId", "releaseId", "releaseHash", "strategyCandidateId",
            "dataSnapshotId", "instrumentId", "timeframe", "direction",
            "decisionAt", "entryAt", "exitAt", "exitReason", "sourcePayloadHash",
        )
        missing = [key for key in required_text if not str(draft.get(key) or "").strip()]
        if missing:
            raise ValueError("Closed execution outcome is missing: " + ",".join(missing))
        if environment == "live":
            live_lineage = [
                key
                for key in ("riskProfileId", "riskProfileHash")
                if not str(draft.get(key) or "").strip()
            ]
            if live_lineage:
                raise ValueError("Live execution outcome is missing: " + ",".join(live_lineage))
        if str(draft["direction"]) not in {"long", "short"}:
            raise ValueError("Execution outcome direction must be long or short")
        decision_at = _parse_time(str(draft["decisionAt"]))
        entry_at = _parse_time(str(draft["entryAt"]))
        exit_at = _parse_time(str(draft["exitAt"]))
        if not decision_at <= entry_at <= exit_at:
            raise ValueError("Execution outcome timestamps are out of order")
        numbers = {
            key: float(draft.get(key))
            for key in (
                "entryPrice", "exitPrice", "quantity", "grossPnl", "feePaid",
                "slippagePaid", "netPnl", "riskAmount",
            )
        }
        if not all(math.isfinite(value) for value in numbers.values()):
            raise ValueError("Execution outcome contains non-finite numbers")
        if any(numbers[key] <= 0 for key in ("entryPrice", "exitPrice", "quantity", "riskAmount")):
            raise ValueError("Execution prices, quantity, and risk amount must be positive")
        if numbers["feePaid"] < 0 or numbers["slippagePaid"] < 0:
            raise ValueError("Execution costs cannot be negative")
        expected_net = numbers["grossPnl"] - numbers["feePaid"] - numbers["slippagePaid"]
        if abs(expected_net - numbers["netPnl"]) > max(1e-8, abs(expected_net) * 1e-8):
            raise ValueError("Execution net PnL does not reconcile with gross PnL and costs")
        evidence_class = "okx_demo" if environment == "okx_demo" else "live"
        trade = {
            **numbers,
            "grossR": numbers["grossPnl"] / numbers["riskAmount"],
            "netR": numbers["netPnl"] / numbers["riskAmount"],
            "exitReason": str(draft["exitReason"]),
            "sameBarAmbiguous": False,
        }
        payload = {
            "schemaVersion": "alphapilot_execution_outcome_v1",
            "evidenceClass": evidence_class,
            "environment": environment,
            "sourceEntityType": "okx_demo_execution" if environment == "okx_demo" else "okx_live_execution",
            "sourceEntityId": str(draft["sourceRecordId"]),
            "releaseId": str(draft["releaseId"]),
            "releaseHash": str(draft["releaseHash"]),
            "riskProfileId": str(draft.get("riskProfileId") or ""),
            "riskProfileHash": str(draft.get("riskProfileHash") or ""),
            "strategyCandidateId": str(draft["strategyCandidateId"]),
            "dataSnapshotId": str(draft["dataSnapshotId"]),
            "instrumentId": str(draft["instrumentId"]),
            "timeframe": str(draft["timeframe"]),
            "direction": str(draft["direction"]),
            "decisionAt": str(draft["decisionAt"]),
            "entryAt": str(draft["entryAt"]),
            "exitAt": str(draft["exitAt"]),
            "status": "closed",
            "trade": trade,
            "sourcePayloadHash": str(draft["sourcePayloadHash"]),
            "accountValuesPersisted": False,
        }
        content_hash = _hash(payload)
        outcome_id = "execution_outcome_" + _hash({
            "environment": environment,
            "sourceRecordId": draft["sourceRecordId"],
            "releaseId": draft["releaseId"],
            "payload": payload,
        })
        existing = self.get_by_source(environment, str(draft["sourceRecordId"]))
        if existing:
            if existing.contentHash != content_hash:
                raise RuntimeError("Closed execution source was reused with different outcome content")
            return existing
        now = _now()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO FormalExecutionOutcomes(
                  executionOutcomeId, environment, sourceRecordId, releaseId,
                  releaseHash, strategyCandidateId, dataSnapshotId, outcomeJson,
                  contentHash, createdAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome_id, environment, draft["sourceRecordId"], draft["releaseId"],
                    draft["releaseHash"], draft["strategyCandidateId"], draft["dataSnapshotId"],
                    _canonical(payload), content_hash, now,
                ),
            )
        return self.get(outcome_id)

    def get(self, outcome_id: str) -> FormalExecutionOutcome:
        row = self.connection.execute(
            "SELECT * FROM FormalExecutionOutcomes WHERE executionOutcomeId = ?", (outcome_id,)
        ).fetchone()
        if not row:
            raise KeyError("Formal execution outcome not found")
        return self._from_row(row)

    def get_by_source(self, environment: str, source_record_id: str) -> FormalExecutionOutcome | None:
        row = self.connection.execute(
            "SELECT * FROM FormalExecutionOutcomes WHERE environment = ? AND sourceRecordId = ?",
            (environment, source_record_id),
        ).fetchone()
        return self._from_row(row) if row else None

    def list_outcomes(self) -> list[FormalExecutionOutcome]:
        rows = self.connection.execute(
            "SELECT * FROM FormalExecutionOutcomes ORDER BY createdAt, executionOutcomeId"
        ).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> FormalExecutionOutcome:
        return FormalExecutionOutcome(
            executionOutcomeId=row["executionOutcomeId"],
            environment=row["environment"],
            sourceRecordId=row["sourceRecordId"],
            releaseId=row["releaseId"],
            releaseHash=row["releaseHash"],
            strategyCandidateId=row["strategyCandidateId"],
            dataSnapshotId=row["dataSnapshotId"],
            outcome=json.loads(row["outcomeJson"]),
            contentHash=row["contentHash"],
            createdAt=row["createdAt"],
        )
