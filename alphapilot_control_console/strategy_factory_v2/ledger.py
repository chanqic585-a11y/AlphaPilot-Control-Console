from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

from ..sqlite_runtime_policy import open_sqlite
from .errors import StrategyFactoryV2Error
from .schemas import STATES, validate_experiment, validate_failure, validate_hypothesis


_FORMAL_COLUMNS = {
    "job": "formalJobCount",
    "claim": "formalClaimCount",
    "attempt": "formalAttemptCount",
    "result": "formalResultCount",
    "read": "formalReadCount",
}

_TRANSITIONS = {
    "hypothesis_draft": {"hypothesis_validated", "blocked", "archived"},
    "hypothesis_validated": {"data_readiness", "blocked", "archived"},
    "data_readiness": {"candidate_build", "blocked", "archived"},
    "candidate_build": {"trial_queued", "blocked", "archived"},
    "trial_queued": {"trial_running", "blocked", "archived"},
    "trial_running": {"trial_queued", "development_complete", "blocked", "archived"},
    "development_complete": {"formal_queued", "blocked", "archived"},
    "formal_queued": {"formal_running", "blocked", "archived"},
    "formal_running": {"formal_complete", "blocked", "archived"},
    "formal_complete": {"demo_release_draft", "archived", "blocked"},
    "demo_release_draft": {"archived", "blocked"},
    "blocked": {"archived"},
    "archived": set(),
}


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class StrategyFactoryV2:
    """Durable research-only state machine with no release approval or execution API."""

    def __init__(
        self,
        state_path: Path,
        *,
        clock: Callable[[], str] = _utc_now,
    ) -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self.connection = open_sqlite(self.state_path)
        self.connection.row_factory = __import__("sqlite3").Row
        self._initialize()

    def close(self) -> None:
        self.connection.close()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS StrategyFactoryV2Runs (
                runId TEXT PRIMARY KEY,
                campaignId TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL,
                hypothesisJson TEXT NOT NULL,
                dataReadinessJson TEXT,
                candidateId TEXT,
                candidateDefinitionHash TEXT,
                completedTrialCount INTEGER NOT NULL DEFAULT 0,
                formalJobCount INTEGER NOT NULL DEFAULT 0,
                formalClaimCount INTEGER NOT NULL DEFAULT 0,
                formalAttemptCount INTEGER NOT NULL DEFAULT 0,
                formalResultCount INTEGER NOT NULL DEFAULT 0,
                formalReadCount INTEGER NOT NULL DEFAULT 0,
                survivorCount INTEGER NOT NULL DEFAULT 0,
                failureCount INTEGER NOT NULL DEFAULT 0,
                createdAt TEXT NOT NULL,
                updatedAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS StrategyFactoryV2Trials (
                trialId TEXT PRIMARY KEY,
                runId TEXT NOT NULL,
                state TEXT NOT NULL,
                experimentJson TEXT NOT NULL,
                resultJson TEXT,
                createdAt TEXT NOT NULL,
                completedAt TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_strategy_factory_v2_trials_run
                ON StrategyFactoryV2Trials(runId, createdAt);
            CREATE TABLE IF NOT EXISTS StrategyFactoryV2Failures (
                failureId INTEGER PRIMARY KEY AUTOINCREMENT,
                runId TEXT NOT NULL,
                familyFingerprint TEXT NOT NULL,
                failureLayer TEXT NOT NULL,
                payloadJson TEXT NOT NULL,
                createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_strategy_factory_v2_failures_family
                ON StrategyFactoryV2Failures(familyFingerprint, failureId);
            CREATE TABLE IF NOT EXISTS StrategyFactoryV2FormalEvidence (
                evidenceId INTEGER PRIMARY KEY AUTOINCREMENT,
                runId TEXT NOT NULL,
                evidenceType TEXT NOT NULL,
                artifactHash TEXT NOT NULL,
                createdAt TEXT NOT NULL,
                UNIQUE(runId, evidenceType, artifactHash)
            );
            CREATE TABLE IF NOT EXISTS StrategyFactoryV2Events (
                eventId INTEGER PRIMARY KEY AUTOINCREMENT,
                runId TEXT NOT NULL,
                eventType TEXT NOT NULL,
                payloadJson TEXT NOT NULL,
                createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_strategy_factory_v2_events_run
                ON StrategyFactoryV2Events(runId, eventId);
            """
        )
        self.connection.commit()

    def create_run(
        self,
        *,
        run_id: str,
        campaign_id: str,
        hypothesis_draft: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not run_id.strip() or not campaign_id.strip():
            raise StrategyFactoryV2Error("run_identity_required")
        now = self.clock()
        self.connection.execute(
            """
            INSERT INTO StrategyFactoryV2Runs(
                runId, campaignId, state, hypothesisJson, createdAt, updatedAt
            ) VALUES (?, ?, 'hypothesis_draft', ?, ?, ?)
            """,
            (run_id, campaign_id, _json(dict(hypothesis_draft)), now, now),
        )
        self._event(run_id, "hypothesis_draft_created", dict(hypothesis_draft), now)
        self.connection.commit()
        return self.get_run(run_id)

    def transition(self, run_id: str, target: str) -> dict[str, Any]:
        if target not in STATES:
            raise StrategyFactoryV2Error("unsupported_state")
        row = self._row(run_id)
        source = str(row["state"])
        if target not in _TRANSITIONS[source]:
            raise StrategyFactoryV2Error(f"invalid_transition:{source}:{target}")
        if target == "development_complete" and int(row["completedTrialCount"]) <= 0:
            raise StrategyFactoryV2Error("completed_trial_required")
        if target == "formal_complete":
            counts = self._formal_counts(row)
            if any(counts[name] <= 0 for name in _FORMAL_COLUMNS):
                raise StrategyFactoryV2Error("formal_evidence_incomplete")
        now = self.clock()
        self.connection.execute(
            "UPDATE StrategyFactoryV2Runs SET state = ?, updatedAt = ? WHERE runId = ?",
            (target, now, run_id),
        )
        self._event(run_id, "state_transition", {"from": source, "to": target}, now)
        self.connection.commit()
        return self.get_run(run_id)

    def validate_hypothesis(self, run_id: str) -> dict[str, Any]:
        row = self._row(run_id)
        hypothesis = validate_hypothesis(json.loads(row["hypothesisJson"]))
        self._event(run_id, "hypothesis_validated", hypothesis, self.clock())
        return self.transition(run_id, "hypothesis_validated")

    def record_data_readiness(
        self,
        run_id: str,
        *,
        snapshot_id: str,
        status: str,
        blockers: list[str],
    ) -> dict[str, Any]:
        if status not in {"ready", "blocked"} or not snapshot_id.strip():
            raise StrategyFactoryV2Error("data_readiness_invalid")
        self.transition(run_id, "data_readiness")
        payload = {
            "snapshotId": snapshot_id,
            "status": status,
            "blockers": sorted({str(item) for item in blockers}),
        }
        now = self.clock()
        self.connection.execute(
            "UPDATE StrategyFactoryV2Runs SET dataReadinessJson = ?, updatedAt = ? WHERE runId = ?",
            (_json(payload), now, run_id),
        )
        self._event(run_id, "data_readiness_recorded", payload, now)
        self.connection.commit()
        return self.transition(run_id, "candidate_build" if status == "ready" else "blocked")

    def build_candidate(
        self,
        run_id: str,
        *,
        candidate_id: str,
        candidate_definition_hash: str,
    ) -> dict[str, Any]:
        row = self._row(run_id)
        if row["state"] != "candidate_build":
            raise StrategyFactoryV2Error("candidate_build_state_required")
        if not candidate_id.strip() or not candidate_definition_hash.strip():
            raise StrategyFactoryV2Error("candidate_identity_required")
        now = self.clock()
        self.connection.execute(
            """
            UPDATE StrategyFactoryV2Runs
            SET candidateId = ?, candidateDefinitionHash = ?, updatedAt = ?
            WHERE runId = ?
            """,
            (candidate_id, candidate_definition_hash, now, run_id),
        )
        self._event(
            run_id,
            "candidate_built",
            {"candidateId": candidate_id, "candidateDefinitionHash": candidate_definition_hash},
            now,
        )
        self.connection.commit()
        return self.get_run(run_id)

    def queue_trial(self, run_id: str, experiment: Mapping[str, Any]) -> dict[str, Any]:
        row = self._row(run_id)
        if row["state"] not in {"candidate_build", "trial_running"}:
            raise StrategyFactoryV2Error("trial_queue_state_invalid")
        validated = validate_experiment(experiment)
        if str(validated["candidateId"]) != str(row["candidateId"]):
            raise StrategyFactoryV2Error("trial_candidate_mismatch")
        now = self.clock()
        self.connection.execute(
            """
            INSERT INTO StrategyFactoryV2Trials(
                trialId, runId, state, experimentJson, createdAt
            ) VALUES (?, ?, 'queued', ?, ?)
            """,
            (validated["experimentId"], run_id, _json(validated), now),
        )
        self._event(run_id, "trial_queued", validated, now)
        self.connection.commit()
        return self.transition(run_id, "trial_queued")

    def start_trial(self, run_id: str, trial_id: str) -> dict[str, Any]:
        row = self._trial(trial_id)
        if row["runId"] != run_id or row["state"] != "queued":
            raise StrategyFactoryV2Error("trial_not_startable")
        self.connection.execute(
            "UPDATE StrategyFactoryV2Trials SET state = 'running' WHERE trialId = ?",
            (trial_id,),
        )
        self.connection.commit()
        return self.transition(run_id, "trial_running")

    def complete_trial(
        self,
        run_id: str,
        trial_id: str,
        *,
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        row = self._trial(trial_id)
        if row["runId"] != run_id or row["state"] != "running":
            raise StrategyFactoryV2Error("trial_not_running")
        if not str(result.get("status") or "").strip():
            raise StrategyFactoryV2Error("trial_result_status_required")
        now = self.clock()
        self.connection.execute(
            """
            UPDATE StrategyFactoryV2Trials
            SET state = 'completed', resultJson = ?, completedAt = ?
            WHERE trialId = ?
            """,
            (_json(dict(result)), now, trial_id),
        )
        self.connection.execute(
            """
            UPDATE StrategyFactoryV2Runs
            SET completedTrialCount = completedTrialCount + 1, updatedAt = ?
            WHERE runId = ?
            """,
            (now, run_id),
        )
        self._event(run_id, "trial_completed", {"trialId": trial_id, "result": dict(result)}, now)
        self.connection.commit()
        return self.get_run(run_id)

    def complete_development(self, run_id: str) -> dict[str, Any]:
        return self.transition(run_id, "development_complete")

    def queue_formal(self, run_id: str, *, job_hash: str) -> dict[str, Any]:
        self._record_formal(run_id, "job", job_hash)
        return self.transition(run_id, "formal_queued")

    def claim_formal(self, run_id: str, *, claim_hash: str) -> dict[str, Any]:
        self._record_formal(run_id, "claim", claim_hash)
        return self.get_run(run_id)

    def start_formal(self, run_id: str, *, attempt_hash: str) -> dict[str, Any]:
        self._record_formal(run_id, "attempt", attempt_hash)
        return self.transition(run_id, "formal_running")

    def complete_formal(
        self,
        run_id: str,
        *,
        result_hash: str,
        survivor_count: int,
    ) -> dict[str, Any]:
        if survivor_count < 0:
            raise StrategyFactoryV2Error("formal_survivor_count_invalid")
        self._record_formal(run_id, "result", result_hash)
        self.connection.execute(
            "UPDATE StrategyFactoryV2Runs SET survivorCount = ? WHERE runId = ?",
            (survivor_count, run_id),
        )
        self.connection.commit()
        return self.get_run(run_id)

    def read_formal_result(self, run_id: str, *, read_hash: str) -> dict[str, Any]:
        self._record_formal(run_id, "read", read_hash)
        return self.transition(run_id, "formal_complete")

    def draft_demo_release(self, run_id: str) -> dict[str, Any]:
        row = self._row(run_id)
        if int(row["survivorCount"]) <= 0:
            raise StrategyFactoryV2Error("demo_release_requires_survivor")
        return self.transition(run_id, "demo_release_draft")

    def archive(self, run_id: str) -> dict[str, Any]:
        return self.transition(run_id, "archived")

    def record_failure(self, run_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._row(run_id)
        failure = validate_failure(payload)
        now = self.clock()
        cursor = self.connection.execute(
            """
            INSERT INTO StrategyFactoryV2Failures(
                runId, familyFingerprint, failureLayer, payloadJson, createdAt
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_id,
                failure["familyFingerprint"],
                failure["failureLayer"],
                _json(failure),
                now,
            ),
        )
        self.connection.execute(
            """
            UPDATE StrategyFactoryV2Runs
            SET failureCount = failureCount + 1, updatedAt = ? WHERE runId = ?
            """,
            (now, run_id),
        )
        self._event(run_id, "failure_attributed", {"failureId": cursor.lastrowid, **failure}, now)
        self.connection.commit()
        return {"failureId": int(cursor.lastrowid), **failure}

    def negative_memory(
        self, *, family_fingerprint: str | None = None, limit: int = 500
    ) -> list[dict[str, Any]]:
        parameters: list[Any] = []
        where = ""
        if family_fingerprint:
            where = "WHERE familyFingerprint = ?"
            parameters.append(family_fingerprint)
        parameters.append(max(1, min(int(limit), 5_000)))
        rows = self.connection.execute(
            f"""
            SELECT failureId, runId, payloadJson, createdAt
            FROM StrategyFactoryV2Failures
            {where}
            ORDER BY failureId DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
        memory = []
        for row in rows:
            payload = json.loads(row["payloadJson"])
            memory.append(
                {
                    "failureId": int(row["failureId"]),
                    "runId": row["runId"],
                    **payload,
                    "prohibitedRepeats": list(payload.get("prohibitedRepair") or []),
                    "createdAt": row["createdAt"],
                }
            )
        return memory

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._project(self._row(run_id))

    def list_runs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(int(limit), 5_000))
        rows = self.connection.execute(
            """
            SELECT * FROM StrategyFactoryV2Runs
            ORDER BY createdAt DESC, runId DESC
            LIMIT ?
            """,
            (bounded_limit,),
        ).fetchall()
        return [self._project(row) for row in rows]

    def projection_state_version(self) -> str:
        """Return a compact version for read-only run projections."""

        row = self.connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM StrategyFactoryV2Runs) AS runCount,
                (SELECT COALESCE(MAX(eventId), 0) FROM StrategyFactoryV2Events) AS maxEventId,
                (SELECT COALESCE(MAX(failureId), 0) FROM StrategyFactoryV2Failures)
                    AS maxFailureId,
                (SELECT COALESCE(MAX(evidenceId), 0) FROM StrategyFactoryV2FormalEvidence)
                    AS maxEvidenceId
            """
        ).fetchone()
        identity = _json(
            {
                "runCount": int(row["runCount"]),
                "maxEventId": int(row["maxEventId"]),
                "maxFailureId": int(row["maxFailureId"]),
                "maxEvidenceId": int(row["maxEvidenceId"]),
            }
        )
        return f"strategy-factory-v2:{sha256(identity.encode('utf-8')).hexdigest()}"

    def list_runs_page(
        self,
        *,
        limit: int = 100,
        after: tuple[Any, ...] | list[Any] | None = None,
    ) -> dict[str, Any]:
        """Read one bounded keyset page ordered by ``createdAt, runId``."""

        bounded_limit = max(1, min(int(limit), 200))
        parameters: tuple[Any, ...]
        if after is None:
            where_clause = ""
            parameters = (bounded_limit + 1,)
        else:
            if len(after) != 2:
                raise StrategyFactoryV2Error("run_page_cursor_invalid")
            created_at, run_id = (str(value) for value in after)
            where_clause = """
            WHERE createdAt < ?
               OR (createdAt = ? AND runId < ?)
            """
            parameters = (created_at, created_at, run_id, bounded_limit + 1)

        rows = self.connection.execute(
            f"""
            SELECT * FROM StrategyFactoryV2Runs
            {where_clause}
            ORDER BY createdAt DESC, runId DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
        has_more = len(rows) > bounded_limit
        page_rows = rows[:bounded_limit]
        items = [self._project(row) for row in page_rows]
        next_key = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_key = (str(last["createdAt"]), str(last["runId"]))
        return {
            "items": items,
            "hasMore": has_more,
            "nextKey": next_key,
            "stateVersion": self.projection_state_version(),
        }

    def _record_formal(self, run_id: str, evidence_type: str, artifact_hash: str) -> None:
        if evidence_type not in _FORMAL_COLUMNS or not artifact_hash.strip():
            raise StrategyFactoryV2Error("formal_evidence_invalid")
        row = self._row(run_id)
        expected_states = {
            "job": {"development_complete"},
            "claim": {"formal_queued"},
            "attempt": {"formal_queued"},
            "result": {"formal_running"},
            "read": {"formal_running"},
        }
        if row["state"] not in expected_states[evidence_type]:
            raise StrategyFactoryV2Error(f"formal_{evidence_type}_state_invalid")
        now = self.clock()
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO StrategyFactoryV2FormalEvidence(
                runId, evidenceType, artifactHash, createdAt
            ) VALUES (?, ?, ?, ?)
            """,
            (run_id, evidence_type, artifact_hash, now),
        )
        if cursor.rowcount:
            column = _FORMAL_COLUMNS[evidence_type]
            self.connection.execute(
                f"UPDATE StrategyFactoryV2Runs SET {column} = {column} + 1, updatedAt = ? WHERE runId = ?",
                (now, run_id),
            )
            self._event(
                run_id,
                f"formal_{evidence_type}_recorded",
                {"artifactHash": artifact_hash},
                now,
            )
        self.connection.commit()

    def _formal_counts(self, row) -> dict[str, int]:
        return {name: int(row[column]) for name, column in _FORMAL_COLUMNS.items()}

    def _project(self, row) -> dict[str, Any]:
        return {
            "runId": row["runId"],
            "campaignId": row["campaignId"],
            "state": row["state"],
            "hypothesis": json.loads(row["hypothesisJson"]),
            "dataReadiness": (
                json.loads(row["dataReadinessJson"]) if row["dataReadinessJson"] else None
            ),
            "candidateId": row["candidateId"],
            "candidateDefinitionHash": row["candidateDefinitionHash"],
            "completedTrialCount": int(row["completedTrialCount"]),
            "formalEvidence": self._formal_counts(row),
            "survivorCount": int(row["survivorCount"]),
            "failureCount": int(row["failureCount"]),
            "createdAt": row["createdAt"],
            "updatedAt": row["updatedAt"],
            "executionAuthorized": False,
        }

    def _row(self, run_id: str):
        row = self.connection.execute(
            "SELECT * FROM StrategyFactoryV2Runs WHERE runId = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise StrategyFactoryV2Error("strategy_factory_v2_run_not_found")
        return row

    def _trial(self, trial_id: str):
        row = self.connection.execute(
            "SELECT * FROM StrategyFactoryV2Trials WHERE trialId = ?", (trial_id,)
        ).fetchone()
        if row is None:
            raise StrategyFactoryV2Error("strategy_factory_v2_trial_not_found")
        return row

    def _event(self, run_id: str, event_type: str, payload: Mapping[str, Any], created_at: str) -> None:
        self.connection.execute(
            """
            INSERT INTO StrategyFactoryV2Events(runId, eventType, payloadJson, createdAt)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, event_type, _json(dict(payload)), created_at),
        )
