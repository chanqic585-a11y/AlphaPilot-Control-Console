from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

CONTROL_CONSOLE_STATE_SOURCE = "alphapilot_control_console_v13_7_36"
DEFAULT_LOCAL_SANDBOX_AUTO_RUNNER = {
    "enabled": False,
    "intervalMinutes": 360,
    "maxRunsPerDay": 4,
    "status": "disabled",
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
    if not isinstance(state.get("manualExecutionTickets"), list):
        state["manualExecutionTickets"] = []
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


def list_paper_observation_tasks() -> dict[str, Any]:
    state = load_state()
    return state.get("paperObservationTasks", {})


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
    runner["intervalMinutes"] = max(1, min(int(runner.get("intervalMinutes") or 360), 1440))
    runner["maxRunsPerDay"] = max(1, min(int(runner.get("maxRunsPerDay") or 4), 288))
    runner["todayRunCount"] = max(0, int(runner.get("todayRunCount") or 0))
    runner["source"] = runner.get("source") or CONTROL_CONSOLE_STATE_SOURCE
    return runner


def update_local_sandbox_auto_runner_state(fields: dict[str, Any], event: dict[str, Any] | None = None) -> dict[str, Any]:
    state = load_state()
    current = get_local_sandbox_auto_runner_state()
    updates = fields if isinstance(fields, dict) else {}
    runner = {**current, **updates, "source": CONTROL_CONSOLE_STATE_SOURCE}
    runner["enabled"] = bool(runner.get("enabled"))
    runner["intervalMinutes"] = max(1, min(int(runner.get("intervalMinutes") or 360), 1440))
    runner["maxRunsPerDay"] = max(1, min(int(runner.get("maxRunsPerDay") or 4), 288))
    runner["todayRunCount"] = max(0, int(runner.get("todayRunCount") or 0))
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
