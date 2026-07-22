from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .config import DATA_DIR, get_quant_engine_path
from .sqlite_runtime_policy import open_sqlite
from .strategy_factory_outcomes import (
    build_strategy_factory_outcome,
    read_strategy_factory_outcome,
)


DEFAULT_STATE_PATH = DATA_DIR / "strategy_factory" / "strategy_factory.sqlite"
DEFAULT_ARTIFACT_ROOT = DATA_DIR / "strategy_factory" / "runs"
DEFAULT_DEVELOPMENT_PROFILE_PATH = (
    DATA_DIR / "strategy_factory" / "development_profile.json"
)
DEVELOPMENT_PROFILE_SCHEMA = "strategy_factory_development_profile_v1"
DEVELOPMENT_COMPARISON_FIELDS = (
    "developmentStart",
    "developmentEnd",
    "dataSnapshotId",
    "costPolicyHash",
    "capitalPolicyHash",
    "benchmarkPolicyHash",
    "randomSeed",
)
ALLOWED_OPERATIONS = {"generate", "combine"}
ALLOWED_MODES = {"quick", "standard"}
ALLOWED_TIMEFRAMES = {"5m", "15m", "1h", "4h", "1d"}
MAX_CANDIDATES = 12
MAX_TRIAL_BUDGET = 96
MAX_CONCURRENT_RUNS = 1
VISIBLE_STAGES = (
    "prepare_material",
    "generate_plan",
    "data_check",
    "tuning_backtest",
    "robustness",
    "portfolio_evaluation",
    "complete",
)
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
ACTIVE_STATUSES = {"queued", "running", "pause_requested", "paused"}
PROHIBITED_RECEIPT_FIELDS = (
    "demoReleaseCount",
    "approvalCount",
    "demoArm",
    "orderCount",
    "tradeApiUsed",
    "withdrawApiUsed",
    "privateAccountReadUsed",
)


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _content_hash(prefix: str, payload: object) -> str:
    digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def _write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def build_research_worker_environment(
    source: dict[str, str] | os._Environ[str] | None = None,
) -> dict[str, str]:
    environment = dict(source or os.environ)
    sensitive_markers = ("API_KEY", "SECRET", "PASSPHRASE", "CREDENTIAL")
    for name in list(environment):
        upper_name = name.upper()
        if "OKX" in upper_name and any(marker in upper_name for marker in sensitive_markers):
            environment.pop(name, None)
    environment.update(
        {
            "ALPHAPILOT_RESEARCH_WORKER": "1",
            "ALPHAPILOT_ORDER_ACCESS": "0",
            "ALPHAPILOT_PRIVATE_API_ACCESS": "0",
        }
    )
    return environment


def _default_launcher(*, command: list[str], cwd: Path, log_path: Path) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("ab")
    try:
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW | getattr(
                subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0
            )
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
            env=build_research_worker_environment(),
        )
    finally:
        log_handle.close()
    return {"pid": process.pid, "started": True}


class StrategyFactoryOrchestrator:
    """Bounded research launcher; it cannot approve, ARM, or execute strategies."""

    def __init__(
        self,
        *,
        state_path: Path = DEFAULT_STATE_PATH,
        artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
        quant_root: Path | None = None,
        source_registry_path: Path | None = None,
        python_executable: Path | None = None,
        development_profile_path: Path | None = None,
        launcher: Callable[..., dict[str, Any]] = _default_launcher,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.state_path = Path(state_path)
        self.artifact_root = Path(artifact_root)
        self.quant_root = Path(quant_root or get_quant_engine_path())
        self.source_registry_path = Path(
            source_registry_path
            or self.quant_root
            / "research/source_registry/strategy_research_source_registry.json"
        )
        configured_python = os.environ.get("ALPHAPILOT_QUANT_PYTHON")
        self.python_executable = Path(
            python_executable
            or configured_python
            or self.quant_root / ".venv/Scripts/python.exe"
        )
        configured_profile = development_profile_path or os.environ.get(
            "ALPHAPILOT_STRATEGY_FACTORY_DEVELOPMENT_PROFILE"
        )
        self.development_profile_path = Path(
            configured_profile or DEFAULT_DEVELOPMENT_PROFILE_PATH
        )
        self.development_profile_required = configured_profile is not None
        self.launcher = launcher
        self.clock = clock
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.connection = open_sqlite(self.state_path)
        self._initialize()

    def close(self) -> None:
        self.connection.close()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS StrategyFactoryRuns (
                runId TEXT PRIMARY KEY,
                programId TEXT NOT NULL,
                campaignId TEXT NOT NULL UNIQUE,
                operation TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                stageIndex INTEGER NOT NULL,
                stageCount INTEGER NOT NULL,
                completedCount INTEGER NOT NULL,
                totalCount INTEGER NOT NULL,
                progressPercent INTEGER NOT NULL,
                currentCandidate TEXT,
                resultClass TEXT,
                survivorCount INTEGER NOT NULL DEFAULT 0,
                pid INTEGER,
                jobJsonPath TEXT NOT NULL,
                pauseMarkerPath TEXT NOT NULL,
                logPath TEXT NOT NULL,
                artifactPath TEXT NOT NULL,
                configJson TEXT NOT NULL,
                receiptJson TEXT,
                createdAt TEXT NOT NULL,
                updatedAt TEXT NOT NULL,
                startedAt TEXT,
                completedAt TEXT
            );
            CREATE TABLE IF NOT EXISTS StrategyFactoryEvents (
                eventId INTEGER PRIMARY KEY AUTOINCREMENT,
                runId TEXT NOT NULL,
                eventType TEXT NOT NULL,
                payloadJson TEXT NOT NULL,
                createdAt TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_strategy_factory_events_run
                ON StrategyFactoryEvents(runId, eventId);
            """
        )
        self.connection.commit()

    def _load_registry(self) -> dict[str, Any]:
        if not self.source_registry_path.is_file():
            raise FileNotFoundError(self.source_registry_path)
        payload = json.loads(self.source_registry_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("families"), list):
            raise ValueError("strategy_source_registry_invalid")
        return payload

    def _load_development_profile(self) -> dict[str, Any] | None:
        path = self.development_profile_path
        if not path.is_file():
            if self.development_profile_required:
                raise FileNotFoundError(path)
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("strategy_factory_development_profile_invalid")
        if payload.get("schemaVersion") != DEVELOPMENT_PROFILE_SCHEMA:
            raise ValueError("strategy_factory_development_profile_schema_invalid")
        profile_id = str(payload.get("profileId") or "").strip()
        comparison = payload.get("comparisonPanel")
        replay = payload.get("developmentReplay")
        if not profile_id or not isinstance(comparison, dict) or not isinstance(replay, dict):
            raise ValueError("strategy_factory_development_profile_invalid")
        missing_fields = [
            field
            for field in DEVELOPMENT_COMPARISON_FIELDS
            if comparison.get(field) in {None, ""}
        ]
        if missing_fields:
            raise ValueError(
                "strategy_factory_development_profile_missing_fields:"
                + ",".join(missing_fields)
            )
        manifest_value = str(replay.get("snapshotManifestPath") or "").strip()
        if not manifest_value:
            raise ValueError("strategy_factory_development_profile_manifest_missing")
        manifest_path = Path(manifest_value)
        if not manifest_path.is_absolute():
            manifest_path = path.parent / manifest_path
        manifest_path = manifest_path.resolve()
        if not manifest_path.is_file():
            raise FileNotFoundError(manifest_path)
        snapshot = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(snapshot, dict) or snapshot.get("snapshotId") != comparison.get(
            "dataSnapshotId"
        ):
            raise ValueError("strategy_factory_development_profile_snapshot_mismatch")
        normalized = {
            "schemaVersion": DEVELOPMENT_PROFILE_SCHEMA,
            "profileId": profile_id,
            "comparisonPanel": {
                **{field: comparison[field] for field in DEVELOPMENT_COMPARISON_FIELDS},
                "randomSeed": int(comparison["randomSeed"]),
            },
            "developmentReplay": {
                **replay,
                "snapshotManifestPath": str(manifest_path),
                "roundTripCostRate": float(replay.get("roundTripCostRate") or 0),
            },
        }
        normalized["profileHash"] = _content_hash(
            "strategy_factory_development_profile",
            normalized,
        )
        return normalized

    @staticmethod
    def _assert_profile_matches_payload(
        profile: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        comparison = profile["comparisonPanel"]
        for field in DEVELOPMENT_COMPARISON_FIELDS:
            if field not in payload:
                continue
            requested = payload[field]
            expected = comparison[field]
            if field == "randomSeed":
                matches = int(requested) == int(expected)
            else:
                matches = str(requested) == str(expected)
            if not matches:
                raise ValueError("strategy_factory_development_profile_mismatch")
        if "developmentReplay" in payload and _canonical_json(
            payload["developmentReplay"]
        ) != _canonical_json(profile["developmentReplay"]):
            raise ValueError("strategy_factory_development_profile_mismatch")

    def _select_candidates(
        self,
        registry: dict[str, Any],
        requested_family_ids: list[str],
        maximum: int,
    ) -> tuple[list[str], list[str]]:
        known_families = {
            str(item.get("familyId") or ""): item
            for item in registry["families"]
            if isinstance(item, dict) and item.get("familyId")
        }
        family_ids = requested_family_ids or list(known_families)
        unknown = sorted(set(family_ids) - set(known_families))
        if unknown:
            raise ValueError(f"unknown_strategy_family:{','.join(unknown)}")
        candidate_ids: list[str] = []
        selected_families: list[str] = []
        for family_id in family_ids:
            variants = known_families[family_id].get("variants") or []
            family_candidates = [
                str(item.get("candidateId") or "")
                for item in variants
                if isinstance(item, dict) and item.get("candidateId")
            ]
            if not family_candidates:
                continue
            selected_families.append(family_id)
            for candidate_id in family_candidates:
                if candidate_id not in candidate_ids:
                    candidate_ids.append(candidate_id)
                if len(candidate_ids) >= maximum:
                    break
            if len(candidate_ids) >= maximum:
                break
        if not selected_families or not candidate_ids:
            raise ValueError("strategy_factory_candidate_selection_empty")
        return selected_families, candidate_ids

    def create_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = str(payload.get("operation") or "").strip()
        timeframe = str(payload.get("timeframe") or "").strip()
        mode = str(payload.get("mode") or "").strip()
        if operation not in ALLOWED_OPERATIONS:
            raise ValueError("strategy_factory_operation_invalid")
        if timeframe not in ALLOWED_TIMEFRAMES:
            raise ValueError("strategy_factory_timeframe_invalid")
        if mode not in ALLOWED_MODES:
            raise ValueError("strategy_factory_mode_invalid")
        maximum_candidates = int(payload.get("maxCandidateCount") or 0)
        maximum_trials = int(payload.get("maxTrialBudget") or 0)
        if not 1 <= maximum_candidates <= MAX_CANDIDATES:
            raise ValueError("strategy_factory_candidate_budget_invalid")
        if not 1 <= maximum_trials <= MAX_TRIAL_BUDGET:
            raise ValueError("strategy_factory_trial_budget_invalid")

        registry = self._load_registry()
        requested_families = [
            str(value).strip()
            for value in payload.get("familyIds") or []
            if str(value).strip()
        ]
        family_ids, candidate_ids = self._select_candidates(
            registry,
            requested_families,
            maximum_candidates,
        )
        now = _iso(self.clock())
        suffix = uuid4().hex[:12]
        program_id = f"strategy_factory_program_{suffix}"
        campaign_id = f"strategy_factory_{timeframe}_{operation}_{suffix}"
        run_id = f"strategy_factory_run_{suffix}"
        run_root = self.artifact_root / run_id
        job_path = run_root / "campaign_input.json"
        pause_marker = run_root / "PAUSE"
        log_path = run_root / "research.log"
        output_root = run_root / "reports"
        development_profile = self._load_development_profile()
        if development_profile:
            self._assert_profile_matches_payload(development_profile, payload)
            comparison_panel = dict(development_profile["comparisonPanel"])
        else:
            comparison_panel = {
                "developmentStart": str(
                    payload.get("developmentStart") or "2024-01-01T00:00:00Z"
                ),
                "developmentEnd": str(
                    payload.get("developmentEnd") or "2025-01-01T00:00:00Z"
                ),
                "dataSnapshotId": str(
                    payload.get("dataSnapshotId") or "runtime_data_readiness_required"
                ),
                "costPolicyHash": str(
                    payload.get("costPolicyHash") or "frozen_cost_policy_required"
                ),
                "capitalPolicyHash": str(
                    payload.get("capitalPolicyHash") or "frozen_capital_policy_required"
                ),
                "benchmarkPolicyHash": str(
                    payload.get("benchmarkPolicyHash") or "frozen_benchmark_policy_required"
                ),
                "randomSeed": int(payload.get("randomSeed") or 56),
            }
        config = {
            "schemaVersion": "v56_strategy_factory_job_v1",
            "runId": run_id,
            "programId": program_id,
            "campaignId": campaign_id,
            "createdAt": now,
            "operation": operation,
            "timeframe": timeframe,
            "mode": mode,
            "familyIds": family_ids,
            "candidateIds": candidate_ids,
            "maxCandidateCount": maximum_candidates,
            "maxTrialBudget": maximum_trials,
            "lockedOosTuningAllowed": False,
            "automaticPromotionAllowed": False,
            "forcePassAllowed": False,
            "experimentBudget": {
                "maximumCandidates": maximum_candidates,
                "maximumTrials": maximum_trials,
                "maximumFormalRuns": min(4, maximum_trials),
                "maximumStructuralRevisionsPerFamily": 1,
            },
            "comparisonPanel": comparison_panel,
            "developmentEvidence": [],
            "formalOutcomes": [],
            "executionBoundary": {
                "demoReleaseCount": 0,
                "approvalCount": 0,
                "demoArm": False,
                "orderCount": 0,
                "tradeApiUsed": False,
                "withdrawApiUsed": False,
                "privateAccountReadUsed": False,
            },
            "workerPolicy": {
                "policyVersion": "strategy_research_worker_policy_v1",
                "marketDataAccess": "read_only",
                "privateApiAccess": False,
                "orderAccess": False,
                "automaticPromotionAllowed": False,
                "maximumConcurrentRuns": MAX_CONCURRENT_RUNS,
                "processPriority": "below_normal",
            },
        }
        if development_profile:
            config["developmentReplay"] = development_profile["developmentReplay"]
            config["developmentProfile"] = {
                "schemaVersion": development_profile["schemaVersion"],
                "profileId": development_profile["profileId"],
                "profileHash": development_profile["profileHash"],
            }
        elif payload.get("developmentReplay"):
            config["developmentReplay"] = payload["developmentReplay"]
        config["jobHash"] = _content_hash("strategy_factory_job", config)
        _write_json_atomic(job_path, config)
        self.connection.execute(
            """
            INSERT INTO StrategyFactoryRuns (
                runId, programId, campaignId, operation, timeframe, mode,
                status, stage, stageIndex, stageCount, completedCount, totalCount,
                progressPercent, survivorCount, jobJsonPath, pauseMarkerPath,
                logPath, artifactPath, configJson, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                program_id,
                campaign_id,
                operation,
                timeframe,
                mode,
                "queued",
                VISIBLE_STAGES[0],
                0,
                len(VISIBLE_STAGES),
                0,
                len(VISIBLE_STAGES),
                0,
                0,
                str(job_path),
                str(pause_marker),
                str(log_path),
                str(output_root),
                _canonical_json(config),
                now,
                now,
            ),
        )
        self._append_event(run_id, "created", config, created_at=now)
        self.connection.commit()
        return self.get_run(run_id)

    def _command(self, row: sqlite3.Row, now: str) -> list[str]:
        run_root = Path(row["jobJsonPath"]).parent
        return [
            str(self.python_executable),
            "-m",
            "alphapilot.scripts.run_v36_candidate_research",
            "--repo-root",
            str(self.quant_root),
            "--state-root",
            str(run_root / "state"),
            "--output-root",
            str(row["artifactPath"]),
            "--job-json",
            str(row["jobJsonPath"]),
            "--pause-file",
            str(row["pauseMarkerPath"]),
            "--worker-exit-file",
            str(self._worker_exit_marker(row)),
            "--registry-path",
            str(self.source_registry_path),
            "--now",
            now,
            "--owner",
            f"strategy-factory:{row['runId']}",
        ]

    @staticmethod
    def _worker_exit_marker(row: sqlite3.Row) -> Path:
        return Path(row["jobJsonPath"]).parent / "state/worker_stopped.json"

    def _launch_run(self, row: sqlite3.Row, *, event_type: str) -> dict[str, Any]:
        now = _iso(self.clock())
        for marker in (
            Path(row["pauseMarkerPath"]),
            self._worker_exit_marker(row),
        ):
            if marker.exists():
                marker.unlink()
        launch = self.launcher(
            command=self._command(row, now),
            cwd=self.quant_root,
            log_path=Path(row["logPath"]),
        )
        if not launch.get("started") or not launch.get("pid"):
            raise RuntimeError("strategy_factory_launch_failed")
        self.connection.execute(
            """
            UPDATE StrategyFactoryRuns
            SET status = 'running', pid = ?, stage = 'generate_plan', stageIndex = 1,
                completedCount = MAX(completedCount, 1), totalCount = ?,
                progressPercent = MAX(progressPercent, 14),
                startedAt = COALESCE(startedAt, ?), completedAt = NULL,
                updatedAt = ?
            WHERE runId = ?
            """,
            (int(launch["pid"]), len(VISIBLE_STAGES), now, now, row["runId"]),
        )
        self._append_event(
            str(row["runId"]),
            event_type,
            {"pid": int(launch["pid"])},
            created_at=now,
        )
        self.connection.commit()
        return self.get_run(str(row["runId"]))

    def start_run(self, run_id: str) -> dict[str, Any]:
        row = self._row(run_id)
        if row["status"] not in {"queued", "paused"}:
            raise ValueError("strategy_factory_run_not_startable")
        if row["status"] == "paused" and row["pid"] is not None:
            if not self._worker_exit_marker(row).is_file():
                raise ValueError("strategy_factory_pause_handoff_in_progress")
        active_count = self.connection.execute(
            """
            SELECT COUNT(*) FROM StrategyFactoryRuns
            WHERE runId <> ? AND status IN ('running', 'pause_requested')
            """,
            (run_id,),
        ).fetchone()[0]
        if int(active_count) >= MAX_CONCURRENT_RUNS:
            raise ValueError("strategy_factory_concurrency_limit")
        return self._launch_run(row, event_type="started")

    def pause_run(self, run_id: str) -> dict[str, Any]:
        row = self._row(run_id)
        if row["status"] == "pause_requested":
            return self._project(row)
        if row["status"] not in {"queued", "running"}:
            raise ValueError("strategy_factory_run_not_pausable")
        marker = Path(row["pauseMarkerPath"])
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("paused\n", encoding="ascii")
        now = _iso(self.clock())
        next_status = "paused" if row["status"] == "queued" else "pause_requested"
        event_type = "paused" if next_status == "paused" else "pause_requested"
        self.connection.execute(
            "UPDATE StrategyFactoryRuns SET status = ?, updatedAt = ? WHERE runId = ?",
            (next_status, now, run_id),
        )
        self._append_event(run_id, event_type, {}, created_at=now)
        self.connection.commit()
        return self.get_run(run_id)

    def resume_run(self, run_id: str) -> dict[str, Any]:
        row = self._row(run_id)
        if row["status"] == "pause_requested":
            raise ValueError("strategy_factory_pause_handoff_in_progress")
        if row["status"] != "paused":
            raise ValueError("strategy_factory_run_not_paused")
        if row["pid"] is not None and not self._worker_exit_marker(row).is_file():
            raise ValueError("strategy_factory_pause_handoff_in_progress")
        return self._launch_run(row, event_type="resumed")

    def record_checkpoint(
        self,
        run_id: str,
        *,
        stage: str,
        completed_count: int,
        total_count: int,
        current_candidate: str | None = None,
    ) -> dict[str, Any]:
        row = self._row(run_id)
        if row["status"] in TERMINAL_STATUSES:
            raise ValueError("strategy_factory_run_terminal")
        if stage not in VISIBLE_STAGES:
            raise ValueError("strategy_factory_stage_invalid")
        if total_count <= 0 or not 0 <= completed_count <= total_count:
            raise ValueError("strategy_factory_progress_invalid")
        stage_index = VISIBLE_STAGES.index(stage)
        if stage_index < int(row["stageIndex"]):
            raise ValueError("strategy_factory_stage_regression")
        progress = round(completed_count * 100 / total_count)
        now = _iso(self.clock())
        self.connection.execute(
            """
            UPDATE StrategyFactoryRuns
            SET stage = ?, stageIndex = ?, stageCount = ?, completedCount = ?,
                totalCount = ?, progressPercent = ?, currentCandidate = ?, updatedAt = ?
            WHERE runId = ?
            """,
            (
                stage,
                stage_index,
                len(VISIBLE_STAGES),
                completed_count,
                total_count,
                progress,
                current_candidate,
                now,
                run_id,
            ),
        )
        self._append_event(
            run_id,
            "checkpoint",
            {
                "stage": stage,
                "completedCount": completed_count,
                "totalCount": total_count,
                "currentCandidate": current_candidate,
            },
            created_at=now,
        )
        self.connection.commit()
        return self.get_run(run_id)

    def record_receipt(self, run_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
        row = self._row(run_id)
        if any(bool(receipt.get(field)) for field in PROHIBITED_RECEIPT_FIELDS):
            raise ValueError("strategy_factory_execution_boundary_crossed")
        status = str(receipt.get("status") or "").strip()
        if not status:
            raise ValueError("strategy_factory_receipt_status_missing")
        previous_receipt = json.loads(row["receiptJson"]) if row["receiptJson"] else {}
        if (
            receipt.get("receiptHash")
            and receipt.get("receiptHash") == previous_receipt.get("receiptHash")
        ):
            return self._project(row)
        if status == "paused":
            now = _iso(self.clock())
            self.connection.execute(
                """
                UPDATE StrategyFactoryRuns
                SET status = 'paused', pid = NULL, receiptJson = ?,
                    updatedAt = ?, completedAt = NULL
                WHERE runId = ?
                """,
                (_canonical_json(receipt), now, run_id),
            )
            self._append_event(run_id, "paused", receipt, created_at=now)
            self.connection.commit()
            return self.get_run(run_id)
        result_class = {
            "immutable_release_ready": "can_enter_demo",
            "waiting_exact_release_approval": "can_enter_demo",
            "research_blocked_data": "data_insufficient",
            "no_stable_candidates": "failed",
            "no_survivor": "failed",
            "research_zero_qualified": "failed",
        }.get(status, "system_issue" if status in {"failed", "error"} else "needs_forward_validation")
        survivor_count = int(
            receipt.get("releaseCount")
            or receipt.get("eligibleCandidateCount")
            or 0
        )
        now = _iso(self.clock())
        config = json.loads(row["configJson"])
        outcome = build_strategy_factory_outcome(
            run_id=run_id,
            campaign_id=str(row["campaignId"]),
            candidate_ids=config["candidateIds"],
            receipt=receipt,
            output_root=Path(row["artifactPath"]),
            outcome_root=Path(row["jobJsonPath"]).parent / "outcome",
            created_at=now,
        )
        self.connection.execute(
            """
            UPDATE StrategyFactoryRuns
            SET status = 'completed', stage = 'complete', stageIndex = ?,
                stageCount = ?, completedCount = ?, totalCount = ?, progressPercent = 100,
                resultClass = ?, survivorCount = ?, receiptJson = ?, updatedAt = ?,
                completedAt = ?
            WHERE runId = ?
            """,
            (
                len(VISIBLE_STAGES) - 1,
                len(VISIBLE_STAGES),
                len(VISIBLE_STAGES),
                len(VISIBLE_STAGES),
                result_class,
                survivor_count,
                _canonical_json(receipt),
                now,
                now,
                run_id,
            ),
        )
        self._append_event(run_id, "completed", receipt, created_at=now)
        if int(outcome["candidateReviewRequestCount"]):
            self._append_event(
                run_id,
                "candidate_review_required",
                {
                    "requestCount": outcome["candidateReviewRequestCount"],
                    "requestPath": outcome["candidateReviewRequestPath"],
                    "approvalCount": 0,
                    "demoArm": False,
                    "orderCount": 0,
                },
                created_at=now,
            )
        if int(outcome["archivedFailureCount"]):
            self._append_event(
                run_id,
                "candidate_failures_archived",
                {
                    "archivedFailureCount": outcome["archivedFailureCount"],
                    "archivePath": outcome["failureArchivePath"],
                },
                created_at=now,
            )
        self.connection.commit()
        return self.get_run(run_id)

    def refresh_run(self, run_id: str) -> dict[str, Any]:
        row = self._row(run_id)
        if row["status"] in TERMINAL_STATUSES:
            return self._project(row)
        receipt_path = Path(row["jobJsonPath"]).parent / "state/research_cycle_receipts.jsonl"
        if not receipt_path.is_file():
            return self._project(row)
        for line in reversed(receipt_path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                receipt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(receipt, dict):
                continue
            if receipt.get("campaignId") != row["campaignId"]:
                continue
            if (
                receipt.get("status") == "paused"
                and not self._worker_exit_marker(row).is_file()
            ):
                return self._project(row)
            return self.record_receipt(run_id, receipt)
        return self._project(row)

    def _append_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        created_at: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO StrategyFactoryEvents(runId, eventType, payloadJson, createdAt)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, event_type, _canonical_json(payload), created_at),
        )

    def _row(self, run_id: str) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT * FROM StrategyFactoryRuns WHERE runId = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return row

    @staticmethod
    def _project(row: sqlite3.Row) -> dict[str, Any]:
        config = json.loads(row["configJson"])
        receipt = json.loads(row["receiptJson"]) if row["receiptJson"] else {}
        outcome = read_strategy_factory_outcome(
            Path(row["jobJsonPath"]).parent / "outcome"
        )
        return {
            "runId": row["runId"],
            "researchRunId": row["runId"],
            "programId": row["programId"],
            "campaignId": row["campaignId"],
            "operation": row["operation"],
            "timeframe": row["timeframe"],
            "mode": row["mode"],
            "status": row["status"],
            "stage": row["stage"],
            "stageIndex": row["stageIndex"],
            "stageCount": row["stageCount"],
            "completedCount": row["completedCount"],
            "totalCount": row["totalCount"],
            "progressPercent": row["progressPercent"],
            "currentCandidate": row["currentCandidate"],
            "resultClass": row["resultClass"],
            "survivorCount": row["survivorCount"],
            "pid": row["pid"],
            "jobJsonPath": row["jobJsonPath"],
            "pauseMarkerPath": row["pauseMarkerPath"],
            "workerExitMarkerPath": str(
                Path(row["jobJsonPath"]).parent / "state/worker_stopped.json"
            ),
            "logPath": row["logPath"],
            "artifactPath": row["artifactPath"],
            "createdAt": row["createdAt"],
            "updatedAt": row["updatedAt"],
            "startedAt": row["startedAt"],
            "completedAt": row["completedAt"],
            "familyIds": config["familyIds"],
            "candidateIds": config["candidateIds"],
            "maxCandidateCount": config["maxCandidateCount"],
            "maxTrialBudget": config["maxTrialBudget"],
            "lockedOosTuningAllowed": False,
            "automaticPromotionAllowed": False,
            "forcePassAllowed": False,
            "approvalCount": int(receipt.get("approvalCount") or 0),
            "demoArm": bool(receipt.get("demoArm")),
            "orderCount": int(receipt.get("orderCount") or 0),
            "readOnly": False,
            "executionBoundary": config["executionBoundary"],
            "workerPolicy": config.get("workerPolicy") or {},
            **outcome,
        }

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._project(self._row(run_id))

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM StrategyFactoryRuns ORDER BY createdAt DESC, runId DESC LIMIT ?",
            (max(1, min(int(limit), 100)),),
        ).fetchall()
        return [self._project(row) for row in rows]

    def list_candidate_review_requests(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM StrategyFactoryRuns ORDER BY createdAt DESC, runId DESC LIMIT 100"
        ).fetchall()
        pending: list[dict[str, Any]] = []
        for row in rows:
            request_path = (
                Path(row["jobJsonPath"]).parent
                / "outcome"
                / "candidate_review_requests.json"
            )
            if not request_path.is_file():
                continue
            payload = json.loads(request_path.read_text(encoding="utf-8"))
            requests = payload.get("requests") if isinstance(payload, dict) else None
            if not isinstance(requests, list):
                raise ValueError("strategy_factory_candidate_review_requests_invalid")
            for request in requests:
                if not isinstance(request, dict):
                    raise ValueError("strategy_factory_candidate_review_request_invalid")
                if request.get("status") != "pending_human_review":
                    continue
                pending.append(
                    {
                        **request,
                        "runId": row["runId"],
                        "campaignId": row["campaignId"],
                        "timeframe": row["timeframe"],
                        "mode": row["mode"],
                    }
                )
        pending.sort(
            key=lambda item: (str(item.get("createdAt") or ""), str(item.get("requestHash") or "")),
            reverse=True,
        )
        return pending[: max(1, min(int(limit), 500))]

    def summary(self) -> dict[str, Any]:
        runs = self.list_runs(limit=20)
        for run in runs:
            if run["status"] in ACTIVE_STATUSES:
                self.refresh_run(run["runId"])
        runs = self.list_runs(limit=20)
        active = next(
            (run for run in runs if run["status"] in ACTIVE_STATUSES),
            None,
        )
        latest = active or (runs[0] if runs else None)
        if latest is None:
            return {
                "researchRunId": None,
                "stage": "idle",
                "completedCount": 0,
                "totalCount": len(VISIBLE_STAGES),
                "progressPercent": 0,
                "currentCandidate": None,
                "status": "idle",
                "resultClass": None,
                "readOnly": False,
                "automaticPromotionAllowed": False,
                "demoArm": False,
                "orderCount": 0,
            }
        return latest


def build_strategy_factory_orchestrator() -> StrategyFactoryOrchestrator:
    return StrategyFactoryOrchestrator()
