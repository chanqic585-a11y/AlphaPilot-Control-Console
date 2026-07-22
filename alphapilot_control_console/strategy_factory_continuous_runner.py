from __future__ import annotations

import json
import os
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .config import DATA_DIR
from .strategy_factory_orchestrator import (
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    build_strategy_factory_orchestrator,
)


DEFAULT_STATE_PATH = (
    DATA_DIR / "strategy_factory" / "continuous_research.json"
)
CONTINUOUS_STATE_SCHEMA = "strategy_factory_continuous_research_v1"
COMPLETION_STATUSES = TERMINAL_STATUSES | {"awaiting_formal_validation"}
DEFAULT_RESEARCH_CYCLE = (
    {"operation": "generate", "timeframe": "5m"},
    {"operation": "generate", "timeframe": "15m"},
    {"operation": "generate", "timeframe": "1h"},
    {"operation": "generate", "timeframe": "4h"},
    {"operation": "combine", "timeframe": "5m"},
    {"operation": "combine", "timeframe": "15m"},
    {"operation": "combine", "timeframe": "1h"},
    {"operation": "combine", "timeframe": "4h"},
)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


class StrategyFactoryContinuousRunner:
    """Sequential research-only runner; it never approves, ARMs, or orders."""

    def __init__(
        self,
        *,
        state_path: Path = DEFAULT_STATE_PATH,
        factory_builder: Callable[[], Any] = build_strategy_factory_orchestrator,
        cycle: tuple[dict[str, str], ...] = DEFAULT_RESEARCH_CYCLE,
        poll_interval_seconds: float = 5.0,
    ) -> None:
        if not cycle:
            raise ValueError("strategy_factory_continuous_cycle_empty")
        self.state_path = Path(state_path)
        self.factory_builder = factory_builder
        self.cycle = tuple(dict(item) for item in cycle)
        self.poll_interval_seconds = max(0.1, float(poll_interval_seconds))
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _default_state(self) -> dict[str, Any]:
        return {
            "schemaVersion": CONTINUOUS_STATE_SCHEMA,
            "enabled": False,
            "phase": "disabled",
            "nextIndex": 0,
            "currentRunId": None,
            "blockingRunId": None,
            "lastRunId": None,
            "lastResultClass": None,
            "lastError": None,
            "completedRunCount": 0,
            "completedCycleCount": 0,
            "cycle": [dict(item) for item in self.cycle],
            "updatedAt": _utc_now(),
        }

    def _read_state(self) -> dict[str, Any]:
        state = self._default_state()
        if self.state_path.is_file():
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("strategy_factory_continuous_state_invalid")
            state.update(payload)
        state["schemaVersion"] = CONTINUOUS_STATE_SCHEMA
        state["cycle"] = [dict(item) for item in self.cycle]
        state["nextIndex"] = int(state.get("nextIndex") or 0) % len(self.cycle)
        return state

    def _save_state(self, state: dict[str, Any]) -> dict[str, Any]:
        state["updatedAt"] = _utc_now()
        _write_json_atomic(self.state_path, state)
        return dict(state)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self._read_state()

    def enable(self) -> dict[str, Any]:
        with self._lock:
            state = self._read_state()
            state.update({"enabled": True, "phase": "ready", "lastError": None})
            return self._save_state(state)

    def disable(self) -> dict[str, Any]:
        with self._lock:
            state = self._read_state()
            state["enabled"] = False
            state["phase"] = (
                "disabled_after_current_run"
                if state.get("currentRunId")
                else "disabled"
            )
            return self._save_state(state)

    def _advance(self, state: dict[str, Any]) -> None:
        next_index = (int(state["nextIndex"]) + 1) % len(self.cycle)
        state["nextIndex"] = next_index
        if next_index == 0:
            state["completedCycleCount"] = int(
                state.get("completedCycleCount") or 0
            ) + 1

    def run_once(self) -> dict[str, Any]:
        with self._lock:
            state = self._read_state()
            enabled = bool(state.get("enabled"))
            if not enabled and not state.get("currentRunId"):
                if state.get("phase") != "disabled":
                    state["phase"] = "disabled"
                    return self._save_state(state)
                return state
            factory = self.factory_builder()
            try:
                current_run_id = str(state.get("currentRunId") or "")
                if current_run_id:
                    current = factory.refresh_run(current_run_id)
                    if current.get("status") in ACTIVE_STATUSES:
                        state.update(
                            {
                                "phase": (
                                    "running"
                                    if enabled
                                    else "disabled_after_current_run"
                                ),
                                "blockingRunId": None,
                                "lastError": None,
                            }
                        )
                        return self._save_state(state)
                    if current.get("status") not in COMPLETION_STATUSES:
                        state.update(
                            {
                                "phase": "waiting_current_run",
                                "lastError": None,
                            }
                        )
                        return self._save_state(state)
                    state.update(
                        {
                            "lastRunId": current_run_id,
                            "lastResultClass": current.get("resultClass"),
                            "currentRunId": None,
                            "completedRunCount": int(
                                state.get("completedRunCount") or 0
                            )
                            + 1,
                        }
                    )
                    self._advance(state)
                    if not enabled:
                        state.update(
                            {
                                "phase": "disabled",
                                "blockingRunId": None,
                                "lastError": None,
                            }
                        )
                        return self._save_state(state)

                for existing in factory.list_runs(limit=100):
                    if existing.get("status") not in ACTIVE_STATUSES:
                        continue
                    refreshed = factory.refresh_run(str(existing["runId"]))
                    if refreshed.get("status") in ACTIVE_STATUSES:
                        state.update(
                            {
                                "phase": "waiting_existing_run",
                                "blockingRunId": existing["runId"],
                                "lastError": None,
                            }
                        )
                        return self._save_state(state)

                cycle_item = self.cycle[int(state["nextIndex"])]
                payload = {
                    **cycle_item,
                    "mode": "standard",
                    "maxCandidateCount": 6,
                    "maxTrialBudget": 48,
                }
                created = factory.create_run(payload)
                started = factory.start_run(str(created["runId"]))
                state.update(
                    {
                        "phase": "running",
                        "currentRunId": started["runId"],
                        "blockingRunId": None,
                        "lastError": None,
                    }
                )
                return self._save_state(state)
            except (KeyError, OSError, RuntimeError, ValueError) as error:
                state.update(
                    {
                        "phase": "cycle_item_failed",
                        "currentRunId": None,
                        "blockingRunId": None,
                        "lastError": f"{type(error).__name__}:{error}",
                    }
                )
                self._advance(state)
                return self._save_state(state)
            finally:
                factory.close()

    def _loop(self) -> None:
        while not self._stop_event.wait(self.poll_interval_seconds):
            self.run_once()

    def start_background(self) -> dict[str, Any]:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._stop_event.clear()
                self._thread = threading.Thread(
                    target=self._loop,
                    name="alphapilot-strategy-factory-continuous-runner",
                    daemon=True,
                )
                self._thread.start()
            return self._read_state()

    def stop_background(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(1.0, self.poll_interval_seconds * 2))


_RUNNER_LOCK = threading.Lock()
_RUNNER: StrategyFactoryContinuousRunner | None = None


def get_strategy_factory_continuous_runner() -> StrategyFactoryContinuousRunner:
    global _RUNNER
    with _RUNNER_LOCK:
        if _RUNNER is None:
            _RUNNER = StrategyFactoryContinuousRunner()
        return _RUNNER


def start_strategy_factory_continuous_runner() -> dict[str, Any]:
    runner = get_strategy_factory_continuous_runner()
    return runner.start_background()


def stop_strategy_factory_continuous_runner() -> None:
    get_strategy_factory_continuous_runner().stop_background()


def get_strategy_factory_continuous_status() -> dict[str, Any]:
    return get_strategy_factory_continuous_runner().status()


def run_strategy_factory_continuous_action(action: str) -> dict[str, Any]:
    runner = get_strategy_factory_continuous_runner()
    if action == "enable":
        runner.enable()
        runner.start_background()
        return runner.run_once()
    if action == "disable":
        return runner.disable()
    raise ValueError("strategy_factory_continuous_action_invalid")
