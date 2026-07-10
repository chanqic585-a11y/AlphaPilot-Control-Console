from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import SAFETY_BOUNDARY
from .importer import scan_quant_engine
from .local_sandbox_runner import run_local_sandbox
from .sandbox_learning import build_learning_snapshot
from .sandbox_observation_reporter import build_local_sandbox_daily_report
from .state_store import (
    get_local_sandbox_auto_runner_state,
    list_local_sandbox_auto_run_events,
    list_local_sandbox_learning_snapshots,
    now_iso,
    update_local_sandbox_auto_runner_state,
)


CONTROL_CONSOLE_VERSION = "V13.8.4"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_4"
BEIJING_TZ = timezone(timedelta(hours=8))


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _beijing_date_key(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(BEIJING_TZ).strftime("%Y-%m-%d")


def _iso_in_minutes(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=max(1, minutes))).isoformat()


def _next_beijing_midnight_iso() -> str:
    now_bj = datetime.now(timezone.utc).astimezone(BEIJING_TZ)
    tomorrow = (now_bj + timedelta(days=1)).date()
    midnight_bj = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=BEIJING_TZ)
    return midnight_bj.astimezone(timezone.utc).isoformat()


class LocalSandboxAutoRunner:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        current = get_local_sandbox_auto_runner_state()
        if current.get("enabled"):
            update_local_sandbox_auto_runner_state({"status": "waiting", "nextRunAt": now_iso()})
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="alphapilot-local-sandbox-auto-runner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def status(self) -> dict[str, Any]:
        runner = get_local_sandbox_auto_runner_state()
        return {
            "autoRunner": runner,
            "events": list_local_sandbox_auto_run_events(20),
            "learningSnapshots": list_local_sandbox_learning_snapshots(10),
            "threadAlive": bool(self._thread and self._thread.is_alive()),
            "version": CONTROL_CONSOLE_VERSION,
            "source": CONTROL_CONSOLE_SOURCE,
            "safetyBoundary": SAFETY_BOUNDARY,
            "safetyNote": "Auto runner only creates local sandbox observation logs and reports; it does not connect exchanges or create orders.",
        }

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = get_local_sandbox_auto_runner_state()
        enabled = bool(payload.get("enabled")) if "enabled" in payload else bool(current.get("enabled"))
        interval = payload.get("intervalMinutes", current.get("intervalMinutes") or 5)
        max_runs = payload.get("maxRunsPerDay", current.get("maxRunsPerDay") or 288)
        try:
            interval_minutes = int(interval)
        except (TypeError, ValueError):
            interval_minutes = 5
        try:
            max_runs_per_day = int(max_runs)
        except (TypeError, ValueError):
            max_runs_per_day = 288
        interval_minutes = max(1, min(interval_minutes, 1440))
        max_runs_per_day = max(1, min(max_runs_per_day, 288))
        now = datetime.now(timezone.utc)
        today_key = _beijing_date_key(now)
        today_run_count = int(current.get("todayRunCount") or 0)
        if current.get("todayKey") != today_key:
            today_run_count = 0
        next_run_at = current.get("nextRunAt")
        settings_changed = (
            interval_minutes != int(current.get("intervalMinutes") or 5)
            or max_runs_per_day != int(current.get("maxRunsPerDay") or 288)
        )
        can_resume_today = today_run_count < max_runs_per_day
        if enabled and (not current.get("enabled") or settings_changed or (current.get("status") == "daily_limit_reached" and can_resume_today)):
            next_run_at = now.isoformat()
        if not enabled:
            next_run_at = None
        status = "waiting" if enabled else "disabled"
        return update_local_sandbox_auto_runner_state(
            {
                "enabled": enabled,
                "intervalMinutes": interval_minutes,
                "maxRunsPerDay": max_runs_per_day,
                "status": status,
                "todayKey": today_key,
                "todayRunCount": today_run_count,
                "nextRunAt": next_run_at,
                "lastError": None if enabled else current.get("lastError"),
            },
            {
                "eventType": "settings_updated",
                "enabled": enabled,
                "intervalMinutes": interval_minutes,
                "maxRunsPerDay": max_runs_per_day,
            },
        )

    def run_once(self, reason: str = "manual") -> dict[str, Any]:
        with self._lock:
            current = get_local_sandbox_auto_runner_state()
            update_local_sandbox_auto_runner_state(
                {"status": "running", "lastError": None},
                {"eventType": "run_started", "reason": reason},
            )
            try:
                replay_cursor = int(current.get("replayCursor") or 0) + 1
                run = run_local_sandbox({
                    "maxTasks": 20,
                    "trigger": f"auto_runner_{reason}",
                    "replayCursor": replay_cursor,
                    "replayMode": current.get("replayMode") or "rolling_window",
                })
                if not int(run.get("taskCount") or 0):
                    now = datetime.now(timezone.utc)
                    today_key = _beijing_date_key(now)
                    today_run_count = int(current.get("todayRunCount") or 0)
                    if current.get("todayKey") != today_key:
                        today_run_count = 0
                    today_run_count += 1
                    interval = int(current.get("intervalMinutes") or 5)
                    runner = update_local_sandbox_auto_runner_state(
                        {
                            "enabled": bool(current.get("enabled")),
                            "status": "waiting_for_candidates" if current.get("enabled") else "disabled",
                            "todayKey": today_key,
                            "todayRunCount": today_run_count,
                            "lastRunAt": now.isoformat(),
                            "nextRunAt": _iso_in_minutes(interval) if current.get("enabled") else None,
                            "lastError": None,
                            "consecutiveFailures": 0,
                        },
                        {
                            "eventType": "run_skipped_no_sandbox_candidates",
                            "reason": reason,
                            "promotedTaskCount": run.get("promotedTaskCount"),
                        },
                    )
                    return {
                        "autoRunner": runner,
                        "localSandboxRun": run,
                        "localSandboxDailyReport": None,
                        "learningSnapshot": None,
                        "safetyBoundary": SAFETY_BOUNDARY,
                    }
                latest = scan_quant_engine()
                report = build_local_sandbox_daily_report(latest.get("strategyLearningLoop") or {})
                learning = build_learning_snapshot(run, report)
                now = datetime.now(timezone.utc)
                today_key = _beijing_date_key(now)
                today_run_count = int(current.get("todayRunCount") or 0)
                if current.get("todayKey") != today_key:
                    today_run_count = 0
                today_run_count += 1
                interval = int(current.get("intervalMinutes") or 5)
                runner = update_local_sandbox_auto_runner_state(
                    {
                        "enabled": bool(current.get("enabled")),
                        "status": "waiting" if current.get("enabled") else "disabled",
                        "todayKey": today_key,
                        "todayRunCount": today_run_count,
                        "lastRunAt": now.isoformat(),
                        "nextRunAt": _iso_in_minutes(interval) if current.get("enabled") else None,
                        "lastRunId": run.get("runId"),
                        "lastReportId": report.get("reportId"),
                        "lastLearningSnapshotId": learning.get("snapshotId"),
                        "replayCursor": replay_cursor,
                        "lastReplayCursor": replay_cursor,
                        "lastReplayWindowId": run.get("rows", [{}])[0].get("replayWindowId") if run.get("rows") else None,
                        "lastReplayWindowCount": run.get("replayWindowCount") or 0,
                        "lastError": None,
                        "consecutiveFailures": 0,
                    },
                    {
                        "eventType": "run_completed",
                        "reason": reason,
                        "runId": run.get("runId"),
                        "reportId": report.get("reportId"),
                        "learningSnapshotId": learning.get("snapshotId"),
                        "generatedLogCount": run.get("generatedLogCount"),
                        "closedSampleCount": run.get("closedSampleCount"),
                        "skippedDuplicateCount": run.get("skippedDuplicateCount"),
                        "replayCursor": replay_cursor,
                        "replayWindowCount": run.get("replayWindowCount"),
                    },
                )
                return {
                    "autoRunner": runner,
                    "localSandboxRun": run,
                    "localSandboxDailyReport": report,
                    "learningSnapshot": learning,
                    "safetyBoundary": SAFETY_BOUNDARY,
                }
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                failures = int(current.get("consecutiveFailures") or 0) + 1
                runner = update_local_sandbox_auto_runner_state(
                    {
                        "status": "error",
                        "lastError": str(exc),
                        "consecutiveFailures": failures,
                        "nextRunAt": _iso_in_minutes(int(current.get("intervalMinutes") or 5)),
                    },
                    {
                        "eventType": "run_failed",
                        "reason": reason,
                        "error": str(exc),
                        "consecutiveFailures": failures,
                    },
                )
                return {"autoRunner": runner, "error": str(exc), "safetyBoundary": SAFETY_BOUNDARY}

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:  # pragma: no cover - last resort for a long-running thread
                update_local_sandbox_auto_runner_state(
                    {"status": "error", "lastError": str(exc)},
                    {"eventType": "tick_failed", "error": str(exc)},
                )
            self._stop_event.wait(15)

    def _tick(self) -> None:
        current = get_local_sandbox_auto_runner_state()
        now = datetime.now(timezone.utc)
        today_key = _beijing_date_key(now)
        if current.get("todayKey") != today_key:
            current = update_local_sandbox_auto_runner_state(
                {"todayKey": today_key, "todayRunCount": 0},
                {"eventType": "daily_counter_reset", "todayKey": today_key},
            )
        if not current.get("enabled"):
            if current.get("status") != "disabled":
                update_local_sandbox_auto_runner_state({"status": "disabled", "nextRunAt": None})
            return
        today_run_count = int(current.get("todayRunCount") or 0)
        max_runs = int(current.get("maxRunsPerDay") or 288)
        if today_run_count >= max_runs:
            update_local_sandbox_auto_runner_state({"status": "daily_limit_reached", "nextRunAt": _next_beijing_midnight_iso()})
            return
        next_run_at = _parse_datetime(current.get("nextRunAt"))
        if next_run_at is None:
            update_local_sandbox_auto_runner_state({"status": "waiting", "nextRunAt": now.isoformat()})
            return
        if now >= next_run_at.astimezone(timezone.utc):
            self.run_once("scheduled")
        elif current.get("status") not in {"waiting", "running", "waiting_for_candidates"}:
            update_local_sandbox_auto_runner_state({"status": "waiting"})


AUTO_RUNNER = LocalSandboxAutoRunner()


def start_local_sandbox_auto_runner() -> None:
    AUTO_RUNNER.start()


def stop_local_sandbox_auto_runner() -> None:
    AUTO_RUNNER.stop()


def get_local_sandbox_auto_runner_status() -> dict[str, Any]:
    return AUTO_RUNNER.status()


def update_local_sandbox_auto_runner_settings(payload: dict[str, Any]) -> dict[str, Any]:
    settings = AUTO_RUNNER.update_settings(payload if isinstance(payload, dict) else {})
    return AUTO_RUNNER.status() | {"autoRunner": settings}


def run_local_sandbox_auto_runner_now() -> dict[str, Any]:
    return AUTO_RUNNER.run_once("manual_request")
