from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import ALLOWED_STRATEGY_STATUSES, DATA_DIR, ensure_data_dir


STATE_PATH = DATA_DIR / "console_state.json"
AUDIT_PATH = DATA_DIR / "audit_log.jsonl"
MOBILE_STATUS_PATH = DATA_DIR / "mobile_control_status.json"
EXCHANGE_PROBE_PATH = DATA_DIR / "exchange_probe_results.json"

ALLOWED_ARTIFACT_REVIEW_STATUSES = {
    "unreviewed",
    "continue_observing",
    "paper_observation",
    "paused",
    "rejected",
}

ARTIFACT_REVIEW_LABELS = {
    "unreviewed": "未复核",
    "continue_observing": "继续观察",
    "paper_observation": "进入纸面观察",
    "paused": "暂停",
    "rejected": "淘汰",
}

ALLOWED_PAPER_OBSERVATION_TASK_STATUSES = {
    "planned",
    "active",
    "paused",
    "completed",
    "rejected",
}

PAPER_OBSERVATION_TASK_LABELS = {
    "planned": "计划中",
    "active": "观察中",
    "paused": "已暂停",
    "completed": "已完成",
    "rejected": "已淘汰",
}

ALLOWED_PAPER_OBSERVATION_LOG_TYPES = {
    "no_signal",
    "signal_seen",
    "rule_matched",
    "missed",
    "invalidated",
    "risk_warning",
}

PAPER_OBSERVATION_LOG_LABELS = {
    "no_signal": "无信号",
    "signal_seen": "看到信号",
    "rule_matched": "规则匹配",
    "missed": "错过观察",
    "invalidated": "条件失效",
    "risk_warning": "风险提醒",
}

ALLOWED_WEAKNESS_ACTION_STATUSES = {
    "todo",
    "in_progress",
    "needs_more_samples",
    "resolved",
    "archived",
}

WEAKNESS_ACTION_STATUS_LABELS = {
    "todo": "待处理",
    "in_progress": "处理中",
    "needs_more_samples": "待更多样本",
    "resolved": "已处理",
    "archived": "已归档",
}

CONTROL_CONSOLE_STATE_SOURCE = "alphapilot_control_console_v13_10_2"
ALLOWED_STRATEGY_PIPELINE_STAGES = {
    "local_sandbox",
    "demo_trial",
    "demo_validated",
    "live_candidate",
    "archived",
}
STRATEGY_PIPELINE_STAGE_LABELS = {
    "local_sandbox": "本地沙盒",
    "demo_trial": "Demo 观察",
    "demo_validated": "Demo 已验证",
    "live_candidate": "实盘候选",
    "archived": "已归档",
}
DEFAULT_LOCAL_SANDBOX_AUTO_RUNNER = {
    "enabled": False,
    "intervalMinutes": 5,
    "maxRunsPerDay": 288,
    "status": "disabled",
    "replayMode": "rolling_window",
    "replayCursor": 0,
    "lastReplayCursor": None,
    "lastReplayWindowId": None,
    "lastReplayWindowCount": 0,
    "todayKey": None,
    "todayRunCount": 0,
    "lastRunAt": None,
    "nextRunAt": None,
    "lastRunId": None,
    "lastReportId": None,
    "lastError": None,
    "consecutiveFailures": 0,
    "source": CONTROL_CONSOLE_STATE_SOURCE,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def write_json(path: Path, payload: Any) -> None:
    ensure_data_dir()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_state() -> dict[str, Any]:
    state = read_json(STATE_PATH, {"strategies": {}, "updatedAt": None})
    if not isinstance(state, dict):
        state = {"strategies": {}, "artifactReviews": {}, "updatedAt": None}
    if not isinstance(state.get("strategies"), dict):
        state["strategies"] = {}
    if not isinstance(state.get("artifactReviews"), dict):
        state["artifactReviews"] = {}
    if not isinstance(state.get("paperObservationTasks"), dict):
        state["paperObservationTasks"] = {}
    if not isinstance(state.get("paperObservationLogs"), dict):
        state["paperObservationLogs"] = {}
    if not isinstance(state.get("localSandboxRuns"), list):
        state["localSandboxRuns"] = []
    if not isinstance(state.get("localSandboxDailyReports"), list):
        state["localSandboxDailyReports"] = []
    if not isinstance(state.get("localSandboxHealthSnapshots"), list):
        state["localSandboxHealthSnapshots"] = []
    if not isinstance(state.get("localSandboxAutoRunner"), dict):
        state["localSandboxAutoRunner"] = dict(DEFAULT_LOCAL_SANDBOX_AUTO_RUNNER)
    if not isinstance(state.get("localSandboxAutoRunEvents"), list):
        state["localSandboxAutoRunEvents"] = []
    if not isinstance(state.get("localSandboxLearningSnapshots"), list):
        state["localSandboxLearningSnapshots"] = []
    if not isinstance(state.get("strategyStageAssignments"), dict):
        state["strategyStageAssignments"] = {}
    if not isinstance(state.get("manualExecutionTickets"), list):
        state["manualExecutionTickets"] = []
    if not isinstance(state.get("preLiveRehearsals"), list):
        state["preLiveRehearsals"] = []
    if not isinstance(state.get("testnetSimulatedOrders"), list):
        state["testnetSimulatedOrders"] = []
    if not isinstance(state.get("exchangeDemoEvents"), list):
        state["exchangeDemoEvents"] = []
    if not isinstance(state.get("noKeyPreLiveScans"), list):
        state["noKeyPreLiveScans"] = []
    if not isinstance(state.get("noKeyPreLiveTickets"), list):
        state["noKeyPreLiveTickets"] = []
    if not isinstance(state.get("autoExecutionRuns"), list):
        state["autoExecutionRuns"] = []
    if not isinstance(state.get("autoExecutionRecords"), list):
        state["autoExecutionRecords"] = []
    if not isinstance(state.get("autoExecutionLifecycleEvents"), list):
        state["autoExecutionLifecycleEvents"] = []
    if not isinstance(state.get("weaknessActionTasks"), dict):
        state["weaknessActionTasks"] = {}
    if not isinstance(state.get("researchActionExecutionRuns"), list):
        state["researchActionExecutionRuns"] = []
    return state


def save_state(state: dict[str, Any]) -> None:
    state["updatedAt"] = now_iso()
    write_json(STATE_PATH, state)


def append_audit(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_data_dir()
    event = {
        "eventType": event_type,
        "payload": payload,
        "createdAt": now_iso(),
        "source": CONTROL_CONSOLE_STATE_SOURCE,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def list_audit(limit: int = 50) -> list[dict[str, Any]]:
    if not AUDIT_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def update_strategy_status(strategy_id: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ALLOWED_STRATEGY_STATUSES:
        raise ValueError(f"Unsupported strategy status: {status}")
    state = load_state()
    strategy_state = state["strategies"].setdefault(strategy_id, {})
    strategy_state["status"] = status
    strategy_state["note"] = note
    strategy_state["updatedAt"] = now_iso()
    save_state(state)
    append_audit(
        "strategy_status_updated",
        {"strategyId": strategy_id, "status": status, "note": note},
    )
    return strategy_state


def list_artifact_reviews() -> dict[str, Any]:
    state = load_state()
    return state.get("artifactReviews", {})


def get_artifact_review(artifact_id: str) -> dict[str, Any]:
    reviews = list_artifact_reviews()
    review = reviews.get(artifact_id)
    if not isinstance(review, dict):
        return {
            "artifactId": artifact_id,
            "reviewStatus": "unreviewed",
            "reviewLabel": ARTIFACT_REVIEW_LABELS["unreviewed"],
            "reviewNote": "",
            "reviewedAt": None,
            "source": CONTROL_CONSOLE_STATE_SOURCE,
        }
    status = str(review.get("reviewStatus") or "unreviewed")
    return {
        "artifactId": artifact_id,
        "reviewStatus": status if status in ALLOWED_ARTIFACT_REVIEW_STATUSES else "unreviewed",
        "reviewLabel": ARTIFACT_REVIEW_LABELS.get(status, ARTIFACT_REVIEW_LABELS["unreviewed"]),
        "reviewNote": str(review.get("reviewNote") or ""),
        "reviewedAt": review.get("reviewedAt"),
        "source": review.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
    }


def update_artifact_review(artifact_id: str, review_status: str, note: str = "") -> dict[str, Any]:
    if review_status not in ALLOWED_ARTIFACT_REVIEW_STATUSES:
        raise ValueError(f"Unsupported artifact review status: {review_status}")
    state = load_state()
    review = {
        "artifactId": artifact_id,
        "reviewStatus": review_status,
        "reviewLabel": ARTIFACT_REVIEW_LABELS.get(review_status, review_status),
        "reviewNote": note,
        "reviewedAt": now_iso(),
        "source": CONTROL_CONSOLE_STATE_SOURCE,
    }
    state["artifactReviews"][artifact_id] = review
    save_state(state)
    append_audit(
        "strategy_artifact_review_updated",
        {"artifactId": artifact_id, "reviewStatus": review_status, "note": note},
    )
    return review


def list_weakness_action_tasks() -> dict[str, Any]:
    state = load_state()
    tasks = state.get("weaknessActionTasks")
    return tasks if isinstance(tasks, dict) else {}


def get_weakness_action_task(action_id: str) -> dict[str, Any]:
    task = list_weakness_action_tasks().get(action_id)
    if not isinstance(task, dict):
        return {
            "actionId": action_id,
            "taskStatus": "todo",
            "taskStatusLabel": WEAKNESS_ACTION_STATUS_LABELS["todo"],
            "taskNote": "",
            "owner": "local_research",
            "updatedAt": None,
            "source": CONTROL_CONSOLE_STATE_SOURCE,
        }
    status = str(task.get("taskStatus") or "todo")
    if status not in ALLOWED_WEAKNESS_ACTION_STATUSES:
        status = "todo"
    return {
        "actionId": action_id,
        "taskStatus": status,
        "taskStatusLabel": WEAKNESS_ACTION_STATUS_LABELS.get(status, status),
        "taskNote": str(task.get("taskNote") or ""),
        "owner": str(task.get("owner") or "local_research"),
        "updatedAt": task.get("updatedAt"),
        "resolvedAt": task.get("resolvedAt"),
        "source": task.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
    }


def update_weakness_action_task(
    action_id: str,
    task_status: str,
    note: str = "",
    owner: str = "local_research",
) -> dict[str, Any]:
    if task_status not in ALLOWED_WEAKNESS_ACTION_STATUSES:
        raise ValueError(f"Unsupported weakness action task status: {task_status}")
    state = load_state()
    now = now_iso()
    task = {
        "actionId": action_id,
        "taskStatus": task_status,
        "taskStatusLabel": WEAKNESS_ACTION_STATUS_LABELS.get(task_status, task_status),
        "taskNote": note,
        "owner": owner or "local_research",
        "updatedAt": now,
        "source": CONTROL_CONSOLE_STATE_SOURCE,
    }
    if task_status == "resolved":
        task["resolvedAt"] = now
    state["weaknessActionTasks"][action_id] = task
    save_state(state)
    append_audit(
        "weakness_action_task_updated",
        {"actionId": action_id, "taskStatus": task_status, "note": note, "owner": task["owner"]},
    )
    return task


def save_research_action_execution_run(run: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    rows = state.get("researchActionExecutionRuns")
    if not isinstance(rows, list):
        rows = []
    run = {
        **run,
        "createdAt": run.get("createdAt") or now_iso(),
        "source": run.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
    }
    rows.append(run)
    state["researchActionExecutionRuns"] = rows[-100:]
    save_state(state)
    append_audit(
        "research_action_execution_run_saved",
        {
            "runId": run.get("runId"),
            "actionCount": run.get("summary", {}).get("actionCount") if isinstance(run.get("summary"), dict) else None,
            "updatedTaskCount": run.get("summary", {}).get("updatedTaskCount") if isinstance(run.get("summary"), dict) else None,
            "dryRunApproved": False,
            "liveTradingApproved": False,
        },
    )
    return run


def list_research_action_execution_runs(limit: int = 10) -> list[dict[str, Any]]:
    state = load_state()
    rows = state.get("researchActionExecutionRuns") if isinstance(state.get("researchActionExecutionRuns"), list) else []
    safe_limit = max(1, min(int(limit or 10), 100))
    return [row for row in rows if isinstance(row, dict)][-safe_limit:][::-1]


def list_paper_observation_tasks() -> dict[str, Any]:
    state = load_state()
    return state.get("paperObservationTasks", {})


def list_strategy_stage_assignments(stage: str | None = None) -> dict[str, dict[str, Any]]:
    state = load_state()
    raw = state.get("strategyStageAssignments")
    assignments = raw if isinstance(raw, dict) else {}
    result = {
        str(strategy_id): dict(item)
        for strategy_id, item in assignments.items()
        if isinstance(item, dict)
    }
    if stage is None:
        return result
    return {
        strategy_id: item
        for strategy_id, item in result.items()
        if item.get("stage") == stage
    }


def set_strategy_stage_assignment(
    strategy_id: str,
    stage: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_id = str(strategy_id or "").strip()
    normalized_stage = str(stage or "").strip()
    if not normalized_id:
        raise ValueError("strategy_id_required")
    if normalized_stage not in ALLOWED_STRATEGY_PIPELINE_STAGES:
        raise ValueError(f"unsupported_strategy_pipeline_stage:{normalized_stage}")
    state = load_state()
    assignments = state.get("strategyStageAssignments")
    if not isinstance(assignments, dict):
        assignments = {}
    current = assignments.get(normalized_id) if isinstance(assignments.get(normalized_id), dict) else {}
    now = now_iso()
    extra = metadata if isinstance(metadata, dict) else {}
    assignment = {
        **current,
        **extra,
        "strategyId": normalized_id,
        "stage": normalized_stage,
        "stageLabel": STRATEGY_PIPELINE_STAGE_LABELS[normalized_stage],
        "sampleDataPreserved": True,
        "updatedAt": now,
        "source": CONTROL_CONSOLE_STATE_SOURCE,
    }
    assignment.setdefault("createdAt", now)
    if normalized_stage == "demo_trial":
        assignment.setdefault("promotedAt", now)
    assignments[normalized_id] = assignment
    state["strategyStageAssignments"] = assignments
    save_state(state)
    append_audit(
        "strategy_pipeline_stage_updated",
        {
            "strategyId": normalized_id,
            "fromStage": current.get("stage") or "local_sandbox",
            "toStage": normalized_stage,
            "sampleDataPreserved": True,
        },
    )
    return assignment


def get_paper_observation_task(artifact_id: str) -> dict[str, Any] | None:
    task = list_paper_observation_tasks().get(artifact_id)
    return task if isinstance(task, dict) else None


def list_paper_observation_logs(artifact_id: str | None = None) -> dict[str, list[dict[str, Any]]] | list[dict[str, Any]]:
    state = load_state()
    logs_by_artifact = state.get("paperObservationLogs", {})
    if not isinstance(logs_by_artifact, dict):
        return [] if artifact_id else {}
    if artifact_id:
        rows = logs_by_artifact.get(artifact_id, [])
        return rows if isinstance(rows, list) else []
    return {
        str(key): value
        for key, value in logs_by_artifact.items()
        if isinstance(value, list)
    }


def add_paper_observation_log(
    artifact_id: str,
    log_type: str = "no_signal",
    note: str = "",
    signal_observed: bool | None = None,
    rule_matched: bool | None = None,
    outcome: str = "",
    artifact: dict[str, Any] | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if log_type not in ALLOWED_PAPER_OBSERVATION_LOG_TYPES:
        raise ValueError(f"Unsupported paper observation log type: {log_type}")
    state = load_state()
    logs_by_artifact = state["paperObservationLogs"]
    rows = logs_by_artifact.get(artifact_id) if isinstance(logs_by_artifact.get(artifact_id), list) else []
    now = now_iso()
    artifact = artifact or {}
    log = {
        "logId": f"paper_log::{artifact_id}::{len(rows) + 1}",
        "artifactId": artifact_id,
        "strategyId": artifact.get("strategyId"),
        "title": artifact.get("displayName") or artifact.get("title") or artifact_id,
        "version": artifact.get("version"),
        "logType": log_type,
        "logLabel": PAPER_OBSERVATION_LOG_LABELS.get(log_type, log_type),
        "signalObserved": bool(signal_observed) if signal_observed is not None else log_type in {"signal_seen", "rule_matched"},
        "ruleMatched": bool(rule_matched) if rule_matched is not None else log_type == "rule_matched",
        "outcome": outcome,
        "note": note,
        "createdAt": now,
        "source": CONTROL_CONSOLE_STATE_SOURCE,
    }
    if isinstance(extra_fields, dict):
        protected_keys = set(log.keys())
        for key, value in extra_fields.items():
            safe_key = str(key).strip()
            if not safe_key or safe_key in protected_keys:
                continue
            log[safe_key] = value
    rows.append(log)
    logs_by_artifact[artifact_id] = rows[-200:]
    save_state(state)
    append_audit(
        "paper_observation_log_added",
        {
            "artifactId": artifact_id,
            "logType": log_type,
            "signalObserved": log["signalObserved"],
            "ruleMatched": log["ruleMatched"],
            "outcome": outcome,
            "note": note,
        },
    )
    return log


def save_local_sandbox_run(run: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    runs = state.get("localSandboxRuns")
    if not isinstance(runs, list):
        runs = []
    run = {
        **run,
        "source": run.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
        "createdAt": run.get("createdAt") or now_iso(),
    }
    runs.append(run)
    state["localSandboxRuns"] = runs[-50:]
    save_state(state)
    append_audit(
        "local_sandbox_run_completed",
        {
            "runId": run.get("runId"),
            "taskCount": run.get("taskCount"),
            "generatedLogCount": run.get("generatedLogCount"),
            "closedSampleCount": run.get("closedSampleCount"),
            "dataGapCount": run.get("dataGapCount"),
            "skippedDuplicateCount": run.get("skippedDuplicateCount"),
        },
    )
    return run


def list_local_sandbox_runs(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    runs = state.get("localSandboxRuns") if isinstance(state.get("localSandboxRuns"), list) else []
    safe_limit = max(1, min(int(limit or 20), 50))
    return [run for run in runs if isinstance(run, dict)][-safe_limit:][::-1]


def save_local_sandbox_daily_report(report: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    reports = state.get("localSandboxDailyReports")
    if not isinstance(reports, list):
        reports = []
    snapshots = state.get("localSandboxHealthSnapshots")
    if not isinstance(snapshots, list):
        snapshots = []
    report = {
        **report,
        "source": report.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
        "generatedAt": report.get("generatedAt") or now_iso(),
    }
    report.pop("recentReports", None)
    reports.append(report)
    rows = report.get("strategyHealthRows") if isinstance(report.get("strategyHealthRows"), list) else []
    for row in rows:
        if isinstance(row, dict):
            snapshots.append({
                **row,
                "reportId": report.get("reportId"),
                "dateKey": report.get("dateKey"),
                "generatedAt": report.get("generatedAt"),
                "source": report.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
            })
    state["localSandboxDailyReports"] = reports[-60:]
    state["localSandboxHealthSnapshots"] = snapshots[-500:]
    save_state(state)
    append_audit(
        "local_sandbox_daily_report_built",
        {
            "reportId": report.get("reportId"),
            "dateKey": report.get("dateKey"),
            "strategyCount": report.get("summary", {}).get("strategyCount") if isinstance(report.get("summary"), dict) else None,
            "dailyLogCount": report.get("summary", {}).get("dailyLogCount") if isinstance(report.get("summary"), dict) else None,
            "averageHealthScore": report.get("summary", {}).get("averageHealthScore") if isinstance(report.get("summary"), dict) else None,
        },
    )
    return report


def list_local_sandbox_daily_reports(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    reports = state.get("localSandboxDailyReports") if isinstance(state.get("localSandboxDailyReports"), list) else []
    safe_limit = max(1, min(int(limit or 20), 60))
    safe_reports: list[dict[str, Any]] = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        item = dict(report)
        item.pop("recentReports", None)
        safe_reports.append(item)
    return safe_reports[-safe_limit:][::-1]


def list_local_sandbox_health_snapshots(limit: int = 100) -> list[dict[str, Any]]:
    state = load_state()
    snapshots = state.get("localSandboxHealthSnapshots") if isinstance(state.get("localSandboxHealthSnapshots"), list) else []
    safe_limit = max(1, min(int(limit or 100), 500))
    return [row for row in snapshots if isinstance(row, dict)][-safe_limit:][::-1]


def get_local_sandbox_auto_runner_state() -> dict[str, Any]:
    state = load_state()
    raw = state.get("localSandboxAutoRunner") if isinstance(state.get("localSandboxAutoRunner"), dict) else {}
    runner = {**DEFAULT_LOCAL_SANDBOX_AUTO_RUNNER, **raw}
    runner["enabled"] = bool(runner.get("enabled"))
    runner["intervalMinutes"] = max(1, min(int(runner.get("intervalMinutes") or 5), 1440))
    runner["maxRunsPerDay"] = max(1, min(int(runner.get("maxRunsPerDay") or 288), 288))
    runner["todayRunCount"] = max(0, int(runner.get("todayRunCount") or 0))
    runner["replayMode"] = str(runner.get("replayMode") or "rolling_window")
    runner["replayCursor"] = max(0, int(runner.get("replayCursor") or 0))
    runner["lastReplayWindowCount"] = max(0, int(runner.get("lastReplayWindowCount") or 0))
    runner["source"] = runner.get("source") or CONTROL_CONSOLE_STATE_SOURCE
    return runner


def update_local_sandbox_auto_runner_state(fields: dict[str, Any], event: dict[str, Any] | None = None) -> dict[str, Any]:
    state = load_state()
    current = get_local_sandbox_auto_runner_state()
    updates = fields if isinstance(fields, dict) else {}
    runner = {**current, **updates, "source": CONTROL_CONSOLE_STATE_SOURCE}
    runner["enabled"] = bool(runner.get("enabled"))
    runner["intervalMinutes"] = max(1, min(int(runner.get("intervalMinutes") or 5), 1440))
    runner["maxRunsPerDay"] = max(1, min(int(runner.get("maxRunsPerDay") or 288), 288))
    runner["todayRunCount"] = max(0, int(runner.get("todayRunCount") or 0))
    runner["replayMode"] = str(runner.get("replayMode") or "rolling_window")
    runner["replayCursor"] = max(0, int(runner.get("replayCursor") or 0))
    runner["lastReplayWindowCount"] = max(0, int(runner.get("lastReplayWindowCount") or 0))
    state["localSandboxAutoRunner"] = runner
    if isinstance(event, dict):
        events = state.get("localSandboxAutoRunEvents")
        if not isinstance(events, list):
            events = []
        event_payload = {
            **event,
            "createdAt": event.get("createdAt") or now_iso(),
            "source": event.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
        }
        events.append(event_payload)
        state["localSandboxAutoRunEvents"] = events[-200:]
    save_state(state)
    if isinstance(event, dict):
        append_audit(
            "local_sandbox_auto_runner_event",
            {
                "eventType": event.get("eventType"),
                "status": runner.get("status"),
                "enabled": runner.get("enabled"),
                "todayRunCount": runner.get("todayRunCount"),
                "lastRunId": runner.get("lastRunId"),
                "lastReportId": runner.get("lastReportId"),
            },
        )
    return runner


def list_local_sandbox_auto_run_events(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    events = state.get("localSandboxAutoRunEvents") if isinstance(state.get("localSandboxAutoRunEvents"), list) else []
    safe_limit = max(1, min(int(limit or 20), 200))
    return [row for row in events if isinstance(row, dict)][-safe_limit:][::-1]


def save_local_sandbox_learning_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    rows = state.get("localSandboxLearningSnapshots")
    if not isinstance(rows, list):
        rows = []
    snapshot = {
        **snapshot,
        "createdAt": snapshot.get("createdAt") or now_iso(),
        "source": snapshot.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
    }
    rows.append(snapshot)
    state["localSandboxLearningSnapshots"] = rows[-500:]
    save_state(state)
    append_audit(
        "local_sandbox_learning_snapshot_saved",
        {
            "sampleCount": snapshot.get("sampleCount"),
            "closedSampleCount": snapshot.get("closedSampleCount"),
            "mlReadiness": snapshot.get("mlReadiness"),
        },
    )
    return snapshot


def list_local_sandbox_learning_snapshots(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    rows = state.get("localSandboxLearningSnapshots") if isinstance(state.get("localSandboxLearningSnapshots"), list) else []
    safe_limit = max(1, min(int(limit or 20), 500))
    return [row for row in rows if isinstance(row, dict)][-safe_limit:][::-1]


def upsert_paper_observation_task(
    artifact_id: str,
    task_status: str = "active",
    note: str = "",
    target_sample_count: int | None = None,
    observation_days: int | None = None,
    artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if task_status not in ALLOWED_PAPER_OBSERVATION_TASK_STATUSES:
        raise ValueError(f"Unsupported paper observation task status: {task_status}")
    state = load_state()
    tasks = state["paperObservationTasks"]
    existing = tasks.get(artifact_id) if isinstance(tasks.get(artifact_id), dict) else {}
    now = now_iso()
    artifact = artifact or {}
    task = {
        **existing,
        "taskId": existing.get("taskId") or f"paper_observation::{artifact_id}",
        "artifactId": artifact_id,
        "strategyId": artifact.get("strategyId") or existing.get("strategyId"),
        "title": artifact.get("title") or existing.get("title") or artifact_id,
        "version": artifact.get("version") or existing.get("version"),
        "sourceFile": artifact.get("sourceFile") or existing.get("sourceFile"),
        "readinessTier": artifact.get("readinessTier") or existing.get("readinessTier"),
        "researchScore": artifact.get("researchScore") if artifact.get("researchScore") is not None else existing.get("researchScore"),
        "taskStatus": task_status,
        "taskLabel": PAPER_OBSERVATION_TASK_LABELS.get(task_status, task_status),
        "targetSampleCount": target_sample_count or existing.get("targetSampleCount") or 50,
        "observationDays": observation_days or existing.get("observationDays") or 60,
        "note": note if note else existing.get("note", ""),
        "createdAt": existing.get("createdAt") or now,
        "updatedAt": now,
        "source": CONTROL_CONSOLE_STATE_SOURCE,
    }
    if task_status == "active" and not task.get("startedAt"):
        task["startedAt"] = now
    if task_status == "completed":
        task["completedAt"] = now
    tasks[artifact_id] = task
    save_state(state)
    append_audit(
        "paper_observation_task_updated",
        {
            "artifactId": artifact_id,
            "taskStatus": task_status,
            "targetSampleCount": task["targetSampleCount"],
            "observationDays": task["observationDays"],
            "note": note,
        },
    )
    return task


def write_mobile_status(payload: dict[str, Any]) -> None:
    write_json(MOBILE_STATUS_PATH, payload)


def read_exchange_probe_results() -> dict[str, Any] | None:
    payload = read_json(EXCHANGE_PROBE_PATH, None)
    return payload if isinstance(payload, dict) else None


def write_exchange_probe_results(payload: dict[str, Any]) -> None:
    write_json(EXCHANGE_PROBE_PATH, payload)
    append_audit(
        "public_exchange_probe_completed",
        {
            "symbol": payload.get("symbol"),
            "timeframe": payload.get("timeframe"),
            "resultCount": len(payload.get("results") or []),
            "publicOnly": True,
        },
    )


def save_manual_execution_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    tickets = state.get("manualExecutionTickets")
    if not isinstance(tickets, list):
        tickets = []
    ticket = {
        **ticket,
        "ticketId": ticket.get("ticketId") or f"manual_ticket::{len(tickets) + 1}",
        "createdAt": ticket.get("createdAt") or now_iso(),
        "source": ticket.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
        "safetyBoundary": {
            "localRecordOnly": True,
            "notAnOrder": True,
            "apiKeyUsed": False,
            "tradeApiUsed": False,
            "withdrawApiUsed": False,
            "realAccountRead": False,
            "realPositionRead": False,
        },
    }
    tickets.append(ticket)
    state["manualExecutionTickets"] = tickets[-200:]
    save_state(state)
    append_audit(
        "manual_execution_ticket_saved",
        {
            "ticketId": ticket.get("ticketId"),
            "taskId": ticket.get("taskId"),
            "status": ticket.get("status"),
            "localRecordOnly": True,
        },
    )
    return ticket


def list_manual_execution_tickets(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    tickets = state.get("manualExecutionTickets") if isinstance(state.get("manualExecutionTickets"), list) else []
    safe_limit = max(1, min(int(limit or 20), 200))
    return [row for row in tickets if isinstance(row, dict)][-safe_limit:][::-1]


def save_pre_live_rehearsal(rehearsal: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    rehearsals = state.get("preLiveRehearsals")
    if not isinstance(rehearsals, list):
        rehearsals = []
    rehearsal = {
        **rehearsal,
        "rehearsalId": rehearsal.get("rehearsalId") or f"pre_live_rehearsal::{len(rehearsals) + 1}",
        "createdAt": rehearsal.get("createdAt") or now_iso(),
        "source": rehearsal.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
        "persistedAsRehearsal": True,
        "createdExchangeOrder": False,
        "connectedExchange": False,
        "storedApiKey": False,
        "safetyBoundary": {
            **(rehearsal.get("safetyBoundary") if isinstance(rehearsal.get("safetyBoundary"), dict) else {}),
            "localRecordOnly": True,
            "notAnOrder": True,
            "apiKeyUsed": False,
            "tradeApiUsed": False,
            "withdrawApiUsed": False,
            "realAccountRead": False,
            "realPositionRead": False,
        },
    }
    rehearsals.append(rehearsal)
    state["preLiveRehearsals"] = rehearsals[-200:]
    save_state(state)
    append_audit(
        "pre_live_rehearsal_saved",
        {
            "rehearsalId": rehearsal.get("rehearsalId"),
            "strategyId": rehearsal.get("strategyId"),
            "symbol": rehearsal.get("symbol"),
            "riskPassed": rehearsal.get("riskPassed"),
            "finalState": rehearsal.get("finalState"),
            "localRecordOnly": True,
        },
    )
    return rehearsal


def list_pre_live_rehearsals(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    rehearsals = state.get("preLiveRehearsals") if isinstance(state.get("preLiveRehearsals"), list) else []
    safe_limit = max(1, min(int(limit or 20), 200))
    return [row for row in rehearsals if isinstance(row, dict)][-safe_limit:][::-1]


def save_testnet_simulated_order(record: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    records = state.get("testnetSimulatedOrders")
    if not isinstance(records, list):
        records = []
    record = {
        **record,
        "simulationId": record.get("simulationId") or f"testnet_simulated_order::{len(records) + 1}",
        "createdAt": record.get("createdAt") or now_iso(),
        "source": record.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
        "localRecordOnly": True,
        "connectedExchange": False,
        "createdExchangeOrder": False,
        "storedApiKey": False,
    }
    records.append(record)
    state["testnetSimulatedOrders"] = records[-200:]
    save_state(state)
    append_audit(
        "testnet_simulated_order_saved",
        {
            "simulationId": record.get("simulationId"),
            "strategyId": record.get("strategyId"),
            "symbol": record.get("symbol"),
            "status": record.get("status"),
            "notionalUsdt": record.get("notionalUsdt"),
            "localRecordOnly": True,
        },
    )
    return record


def list_testnet_simulated_orders(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    records = state.get("testnetSimulatedOrders") if isinstance(state.get("testnetSimulatedOrders"), list) else []
    safe_limit = max(1, min(int(limit or 20), 200))
    return [row for row in records if isinstance(row, dict)][-safe_limit:][::-1]


def save_exchange_demo_event(record: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    records = state.get("exchangeDemoEvents")
    if not isinstance(records, list):
        records = []
    record = {
        **record,
        "eventId": record.get("eventId") or f"exchange_demo_event::{len(records) + 1}",
        "createdAt": record.get("createdAt") or now_iso(),
        "source": record.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
        "environment": "okx_demo",
        "liveTrading": False,
        "withdrawEnabled": False,
    }
    records.append(record)
    state["exchangeDemoEvents"] = records[-300:]
    save_state(state)
    append_audit(
        "exchange_demo_event_saved",
        {
            "eventId": record.get("eventId"),
            "eventType": record.get("eventType"),
            "status": record.get("status"),
            "instId": record.get("instId"),
            "notionalUsdt": record.get("notionalUsdt"),
            "environment": "okx_demo",
            "liveTrading": False,
        },
    )
    return record


def list_exchange_demo_events(limit: int = 30) -> list[dict[str, Any]]:
    state = load_state()
    records = state.get("exchangeDemoEvents") if isinstance(state.get("exchangeDemoEvents"), list) else []
    safe_limit = max(1, min(int(limit or 30), 300))
    return [row for row in records if isinstance(row, dict)][-safe_limit:][::-1]


def save_no_key_pre_live_scan(record: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    records = state.get("noKeyPreLiveScans")
    if not isinstance(records, list):
        records = []
    record = {
        **record,
        "scanId": record.get("scanId") or f"no_key_pre_live_scan::{len(records) + 1}",
        "createdAt": record.get("createdAt") or now_iso(),
        "source": record.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
        "environment": "public_market_only",
        "apiKeyUsed": False,
        "ordersCreated": False,
        "liveTrading": False,
        "withdrawEnabled": False,
    }
    records.append(record)
    state["noKeyPreLiveScans"] = records[-50:]
    save_state(state)
    append_audit(
        "no_key_pre_live_scan_saved",
        {
            "scanId": record.get("scanId"),
            "candidateCount": record.get("candidateCount"),
            "publicOkCount": record.get("publicOkCount"),
            "apiKeyUsed": False,
            "ordersCreated": False,
            "liveTrading": False,
        },
    )
    return record


def list_no_key_pre_live_scans(limit: int = 10) -> list[dict[str, Any]]:
    state = load_state()
    records = state.get("noKeyPreLiveScans") if isinstance(state.get("noKeyPreLiveScans"), list) else []
    safe_limit = max(1, min(int(limit or 10), 50))
    return [row for row in records if isinstance(row, dict)][-safe_limit:][::-1]


def save_no_key_pre_live_ticket(record: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    records = state.get("noKeyPreLiveTickets")
    if not isinstance(records, list):
        records = []
    record = {
        **record,
        "ticketId": record.get("ticketId") or f"no_key_pre_live_ticket::{len(records) + 1}",
        "createdAt": record.get("createdAt") or now_iso(),
        "source": record.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
        "environment": "local_observation_only",
        "apiKeyUsed": False,
        "ordersCreated": False,
        "demoOrderCreated": False,
        "liveTrading": False,
        "withdrawEnabled": False,
        "ticketStatus": record.get("ticketStatus") or "local_observation",
    }
    records.append(record)
    state["noKeyPreLiveTickets"] = records[-200:]
    save_state(state)
    append_audit(
        "no_key_pre_live_ticket_saved",
        {
            "ticketId": record.get("ticketId"),
            "strategyId": record.get("strategyId"),
            "instId": record.get("instId"),
            "notionalUsdt": record.get("notionalUsdt"),
            "apiKeyUsed": False,
            "ordersCreated": False,
            "liveTrading": False,
        },
    )
    return record


def list_no_key_pre_live_tickets(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    records = state.get("noKeyPreLiveTickets") if isinstance(state.get("noKeyPreLiveTickets"), list) else []
    safe_limit = max(1, min(int(limit or 20), 200))
    return [row for row in records if isinstance(row, dict)][-safe_limit:][::-1]


def save_auto_execution_run(record: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    records = state.get("autoExecutionRuns")
    if not isinstance(records, list):
        records = []
    record = {
        **record,
        "runId": record.get("runId") or f"auto_execution_run::{len(records) + 1}",
        "createdAt": record.get("createdAt") or now_iso(),
        "source": record.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
        "environment": "local_auto_execution",
        "apiKeyUsed": False,
        "ordersCreated": False,
        "demoOrderCreated": False,
        "liveTrading": False,
        "withdrawEnabled": False,
    }
    records.append(record)
    state["autoExecutionRuns"] = records[-100:]
    save_state(state)
    append_audit(
        "auto_execution_run_saved",
        {
            "runId": record.get("runId"),
            "selectedCount": record.get("selectedCount"),
            "blockedCount": record.get("blockedCount"),
            "recordCount": record.get("recordCount"),
            "apiKeyUsed": False,
            "ordersCreated": False,
            "liveTrading": False,
        },
    )
    return record


def list_auto_execution_runs(limit: int = 20) -> list[dict[str, Any]]:
    state = load_state()
    records = state.get("autoExecutionRuns") if isinstance(state.get("autoExecutionRuns"), list) else []
    safe_limit = max(1, min(int(limit or 20), 100))
    return [row for row in records if isinstance(row, dict)][-safe_limit:][::-1]


def save_auto_execution_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state = load_state()
    records = state.get("autoExecutionRecords")
    if not isinstance(records, list):
        records = []
    created: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = {
            **row,
            "recordId": row.get("recordId") or f"auto_execution_record::{len(records) + len(created) + 1}",
            "createdAt": row.get("createdAt") or now_iso(),
            "source": row.get("source") or CONTROL_CONSOLE_STATE_SOURCE,
            "environment": "local_auto_execution",
            "executionMode": row.get("executionMode") or "local_auto_simulation",
            "apiKeyUsed": False,
            "ordersCreated": False,
            "demoOrderCreated": False,
            "liveTrading": False,
            "withdrawEnabled": False,
        }
        created.append(item)
    records.extend(created)
    state["autoExecutionRecords"] = records[-500:]
    save_state(state)
    append_audit(
        "auto_execution_records_saved",
        {
            "count": len(created),
            "runIds": sorted({str(item.get("runId") or "") for item in created if item.get("runId")}),
            "apiKeyUsed": False,
            "ordersCreated": False,
            "liveTrading": False,
        },
    )
    return created


def list_auto_execution_records(limit: int = 30) -> list[dict[str, Any]]:
    state = load_state()
    records = state.get("autoExecutionRecords") if isinstance(state.get("autoExecutionRecords"), list) else []
    safe_limit = max(1, min(int(limit or 30), 500))
    return [row for row in records if isinstance(row, dict)][-safe_limit:][::-1]


def save_auto_execution_lifecycle_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state = load_state()
    records = state.get("autoExecutionLifecycleEvents")
    if not isinstance(records, list):
        records = []
    created: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("recordId") or "").strip():
            continue
        projection = row.get("projection") if isinstance(row.get("projection"), dict) else {}
        market_snapshot = row.get("marketSnapshot") if isinstance(row.get("marketSnapshot"), dict) else {}
        item = {
            **row,
            "projection": projection,
            "marketSnapshot": market_snapshot,
            "eventId": row.get("eventId") or f"auto_execution_lifecycle_event::{uuid4().hex}",
            "createdAt": row.get("createdAt") or now_iso(),
            "source": row.get("source") or "alphapilot_control_console_v13_10_5",
            "environment": "local_auto_execution",
            "apiKeyUsed": False,
            "ordersCreated": False,
            "demoOrderCreated": False,
            "liveTrading": False,
            "withdrawEnabled": False,
        }
        created.append(item)
    if not created:
        return []
    records.extend(created)
    state["autoExecutionLifecycleEvents"] = records[-2000:]
    save_state(state)
    append_audit(
        "auto_execution_lifecycle_events_saved",
        {
            "count": len(created),
            "recordIds": sorted({str(item.get("recordId") or "") for item in created}),
            "eventTypes": sorted({str(item.get("eventType") or "") for item in created}),
            "apiKeyUsed": False,
            "ordersCreated": False,
            "liveTrading": False,
        },
    )
    return created


def list_auto_execution_lifecycle_events(limit: int = 200) -> list[dict[str, Any]]:
    state = load_state()
    records = state.get("autoExecutionLifecycleEvents") if isinstance(state.get("autoExecutionLifecycleEvents"), list) else []
    safe_limit = max(1, min(int(limit or 200), 2000))
    return [row for row in records if isinstance(row, dict)][-safe_limit:][::-1]
