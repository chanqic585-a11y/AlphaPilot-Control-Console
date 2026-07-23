from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def _read_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, Mapping) else {}


def _number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: object) -> int:
    number = _number(value)
    return int(number) if number is not None else 0


def _elapsed_seconds(started_at: object, ended_at: object) -> float | None:
    if not started_at or not ended_at:
        return None
    try:
        start = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(ended_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0.0, round((end - start).total_seconds(), 3))


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _artifact_projection(campaign_root: Path) -> list[dict[str, Any]]:
    manifest = _read_object(campaign_root / "artifact_manifest.json")
    rows = manifest.get("artifacts")
    if not isinstance(rows, list):
        return []
    artifacts: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        name = str(row.get("path") or "").strip().replace("\\", "/")
        if not name or Path(name).is_absolute():
            continue
        artifact_path = campaign_root / name
        if not _inside(artifact_path, campaign_root) or not artifact_path.is_file():
            continue
        artifacts.append(
            {
                "name": name,
                "path": str(artifact_path),
                "sha256": str(row.get("sha256") or "") or None,
            }
        )
    return artifacts


def _trial_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    metrics = row.get("typeSpecificMetrics")
    metrics = metrics if isinstance(metrics, Mapping) else {}
    return {
        "candidateId": str(row.get("candidateId") or "") or None,
        "trialId": str(row.get("trialId") or "") or None,
        "profitFactor": _number(row.get("profitFactor")),
        "averageNetR": _number(
            row.get("selectionNetR")
            if row.get("selectionNetR") is not None
            else metrics.get("averageNetR")
        ),
        "totalNetR": _number(metrics.get("totalNetR")),
        "maxDrawdownR": _number(row.get("maxDrawdownR")),
        "totalCostR": _number(metrics.get("totalCostR")),
        "eventCount": _integer(metrics.get("eventCount")),
    }


def project_strategy_factory_execution_evidence(
    *,
    output_root: Path,
    campaign_id: str,
    config: Mapping[str, Any],
    receipt: Mapping[str, Any],
    created_at: object,
    started_at: object,
    updated_at: object,
    completed_at: object,
) -> dict[str, Any]:
    root = Path(output_root)
    campaign_root = root / campaign_id
    if not _inside(campaign_root, root):
        raise ValueError("strategy_factory_campaign_path_outside_run")

    summary = _read_object(campaign_root / "campaign_summary.json")
    preregistration = _read_object(campaign_root / "preregistration.json")
    audit = _read_object(campaign_root / "development_replay_audit.json")
    projections_payload = _read_object(campaign_root / "development_projection.json")
    comparison_panel = preregistration.get("comparisonPanel")
    comparison_panel = comparison_panel if isinstance(comparison_panel, Mapping) else {}
    snapshot_audit = audit.get("snapshotAudit")
    snapshot_audit = snapshot_audit if isinstance(snapshot_audit, Mapping) else {}

    partition_rows = snapshot_audit.get("partitions")
    partition_rows = partition_rows if isinstance(partition_rows, list) else []
    partitions: list[dict[str, Any]] = []
    for row in partition_rows:
        if not isinstance(row, Mapping):
            continue
        partitions.append(
            {
                "instrumentId": str(row.get("instrumentId") or "") or None,
                "timeframe": str(row.get("timeframe") or "") or None,
                "rowCount": _integer(row.get("rowCount")),
                "firstTimestamp": row.get("firstTimestamp"),
                "lastTimestamp": row.get("lastTimestamp"),
                "sha256": str(row.get("outputSha256") or "") or None,
            }
        )

    trial_audit_rows = audit.get("trialAudit")
    trial_audit_rows = trial_audit_rows if isinstance(trial_audit_rows, list) else []
    event_count = sum(
        _integer(row.get("eventCount"))
        for row in trial_audit_rows
        if isinstance(row, Mapping)
    )

    projection_rows = projections_payload.get("projections")
    projection_rows = projection_rows if isinstance(projection_rows, list) else []
    trials = [
        _trial_projection(row)
        for row in projection_rows
        if isinstance(row, Mapping)
    ]
    ranked_trials = sorted(
        trials,
        key=lambda row: (
            row["averageNetR"] is not None,
            row["averageNetR"] if row["averageNetR"] is not None else float("-inf"),
        ),
        reverse=True,
    )
    best_trial = ranked_trials[0] if ranked_trials else None
    worst_trial = ranked_trials[-1] if ranked_trials else None

    development_status = str(
        summary.get("developmentReplayStatus") or audit.get("status") or "not_run"
    )
    development_completed = development_status == "completed"
    formal_run_count = _integer(summary.get("formalRunCount") or receipt.get("formalRunCount"))
    formal_job_count = _integer(
        summary.get("formalJobCount")
        or receipt.get("formalJobCount")
        or formal_run_count
    )
    formal_claim_count = _integer(
        summary.get("formalClaimCount") or receipt.get("formalClaimCount")
    )
    formal_attempt_count = _integer(
        summary.get("formalAttemptCount") or receipt.get("formalAttemptCount")
    )
    formal_result_count = _integer(
        summary.get("formalResultCount") or receipt.get("formalResultCount")
    )
    result_read_count = _integer(summary.get("resultReadCount") or receipt.get("resultReadCount"))
    locked_oos_read_count = _integer(
        summary.get("lockedOosReadCount")
        or receipt.get("lockedOosReadCount")
        or receipt.get("lockedOosAccessCount")
    )
    formal_chain_complete = all(
        count > 0
        for count in (
            formal_job_count,
            formal_claim_count,
            formal_attempt_count,
            formal_result_count,
            result_read_count,
        )
    )
    if formal_chain_complete:
        formal_status = "completed"
        validation_level = "formal_results_available"
    elif any(
        count > 0
        for count in (
            formal_job_count,
            formal_claim_count,
            formal_attempt_count,
            formal_result_count,
            result_read_count,
        )
    ):
        formal_status = "running"
        validation_level = "formal_running"
    else:
        formal_status = "not_run"
        validation_level = "development_only" if development_completed else "not_started"

    end_time = completed_at or updated_at
    candidate_count = _integer(summary.get("candidateCount"))
    if not candidate_count:
        candidate_count = len(config.get("candidateIds") or [])
    return {
        "evaluationMode": (
            "real_development_backtest" if development_completed else "pending"
        ),
        "validationLevel": validation_level,
        "runtime": {
            "createdAt": created_at,
            "startedAt": started_at,
            "updatedAt": updated_at,
            "completedAt": completed_at,
            "elapsedSeconds": _elapsed_seconds(started_at or created_at, end_time),
        },
        "development": {
            "status": development_status,
            "selectionSplit": preregistration.get("selectionSplit"),
            "developmentStart": comparison_panel.get("developmentStart"),
            "developmentEnd": comparison_panel.get("developmentEnd"),
            "snapshotId": (
                snapshot_audit.get("snapshotId")
                or comparison_panel.get("dataSnapshotId")
            ),
            "costPolicyHash": comparison_panel.get("costPolicyHash"),
            "verifiedPartitionCount": _integer(
                snapshot_audit.get("verifiedPartitionCount")
            ),
            "instrumentCount": len(
                {row["instrumentId"] for row in partitions if row["instrumentId"]}
            ),
            "timeframes": sorted(
                {str(row["timeframe"]) for row in partitions if row["timeframe"]}
            ),
            "totalRowCount": sum(row["rowCount"] for row in partitions),
            "partitions": partitions,
            "candidateCount": candidate_count,
            "trialCount": _integer(summary.get("trialCount")),
            "eventCount": event_count,
            "projectionCount": len(trials),
            "positiveAverageNetRCount": sum(
                1
                for row in trials
                if row["averageNetR"] is not None and row["averageNetR"] > 0
            ),
            "allTrialTotalCostR": round(
                sum(row["totalCostR"] or 0.0 for row in trials), 8
            ),
            "bestTrial": best_trial,
            "worstTrial": worst_trial,
        },
        "formal": {
            "status": formal_status,
            "formalRunCount": formal_run_count,
            "formalJobCount": formal_job_count,
            "formalClaimCount": formal_claim_count,
            "formalAttemptCount": formal_attempt_count,
            "formalResultCount": formal_result_count,
            "resultReadCount": result_read_count,
            "lockedOosReadCount": locked_oos_read_count,
            "releaseCount": _integer(summary.get("releaseCount") or receipt.get("releaseCount")),
        },
        "artifacts": _artifact_projection(campaign_root),
    }
