"""Backend-owned automatic execution heartbeat for Demo and Live environments."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

from .config import DATA_DIR
from .evolution_demo_service import resume_evolution_demo_runtime
from .live_canary_service import arm_live_canary
from .unified_auto_execution_adapters import (
    OkxDemoAutoExecutionAdapter,
    OkxLiveAutoExecutionAdapter,
)
from .unified_auto_execution_controller import UnifiedAutoExecutionController
from .unified_auto_execution_store import UnifiedAutoExecutionStore


AUTO_EXECUTION_STORE_PATH = DATA_DIR / "unified_auto_execution.sqlite"
ENVIRONMENTS = ("okx_demo", "okx_live")


class UnifiedAutoExecutionRunner:
    def __init__(
        self,
        *,
        controller: Any,
        interval_seconds: float = 15.0,
        live_arm: Callable[[dict[str, Any]], dict[str, Any]] = arm_live_canary,
        demo_resume: Callable[[], None] = resume_evolution_demo_runtime,
    ):
        self.controller = controller
        self.interval_seconds = max(0.01, float(interval_seconds))
        self.live_arm = live_arm
        self.demo_resume = demo_resume
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_results: dict[str, dict[str, Any]] = {}

    def start(self) -> threading.Thread:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self._thread
            self._stop_event.clear()
            self._wake_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="alphapilot-unified-auto-execution",
                daemon=True,
            )
            self._thread.start()
            return self._thread

    def stop(self, timeout_seconds: float = 5.0) -> None:
        with self._lock:
            thread = self._thread
            self._stop_event.set()
            self._wake_event.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(0.0, float(timeout_seconds)))

    def wake(self) -> None:
        self._wake_event.set()

    def is_running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            self._wake_event.wait(self.interval_seconds)
            self._wake_event.clear()

    def run_once(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for environment in ENVIRONMENTS:
            try:
                results[environment] = self.controller.heartbeat(environment)
            except Exception as error:
                results[environment] = {
                    "environment": environment,
                    "status": "runner_error",
                    "blockers": [f"runner_exception:{type(error).__name__}"],
                }
        with self._lock:
            self._last_results = results
        return results

    def status(self) -> dict[str, Any]:
        with self._lock:
            last_results = dict(self._last_results)
        environments: dict[str, dict[str, Any]] = {}
        for environment in ENVIRONMENTS:
            try:
                environments[environment] = {
                    **self.controller.status(environment),
                    "lastHeartbeatResult": last_results.get(environment) or {},
                }
            except Exception as error:
                environments[environment] = {
                    "environment": environment,
                    "status": "status_unavailable",
                    "blockers": [f"status_exception:{type(error).__name__}"],
                }
        return {
            "version": "V13.27.7",
            "source": "unified_auto_execution_runner_v1",
            "running": self.is_running(),
            "heartbeatIntervalSeconds": self.interval_seconds,
            "environments": environments,
            "lastHeartbeatResults": last_results,
            "safetyBoundary": {
                "perOrderConfirmationRequired": False,
                "liveProcessArmRequired": True,
                "environmentIsolationRequired": True,
                "withdrawAllowed": False,
                "rawCredentialStorageAllowed": False,
            },
        }

    def action(
        self,
        environment: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = payload if isinstance(payload, dict) else {}
        arm_result: dict[str, Any] | None = None
        if environment not in ENVIRONMENTS:
            return {"ok": False, "blockers": ["unsupported_auto_execution_environment"]}
        if action == "start":
            if environment == "okx_demo":
                self.demo_resume()
                self.controller.arm(environment)
            elif not self.controller.status(environment).get("armedForCurrentProcess"):
                return {"ok": False, "blockers": ["live_process_arm_required"], "runtime": self.status()}
            result = self.controller.start(environment)
        elif action == "arm":
            if environment == "okx_live":
                arm_result = self.live_arm(body)
            result = self.controller.arm(environment)
        elif action == "pause":
            result = self.controller.pause(environment, str(body.get("reason") or "operator_pause"))
        elif action == "stop":
            result = self.controller.stop(environment, str(body.get("reason") or "operator_stop"))
        elif action == "emergency_stop":
            result = self.controller.emergency_stop(
                environment,
                str(body.get("reason") or "operator_emergency_stop"),
            )
        else:
            return {"ok": False, "blockers": ["unsupported_auto_execution_action"]}
        self.wake()
        return {
            "ok": True,
            "action": action,
            "environment": environment,
            "result": result,
            "armResult": arm_result,
            "runtime": self.status(),
        }


_DEFAULT_LOCK = threading.Lock()
_DEFAULT_RUNNER: UnifiedAutoExecutionRunner | None = None


def _build_default_runner(
    store_path: Path | str = AUTO_EXECUTION_STORE_PATH,
) -> UnifiedAutoExecutionRunner:
    store = UnifiedAutoExecutionStore(store_path)
    controller = UnifiedAutoExecutionController(
        store=store,
        adapters={
            "okx_demo": OkxDemoAutoExecutionAdapter(),
            "okx_live": OkxLiveAutoExecutionAdapter(),
        },
    )
    return UnifiedAutoExecutionRunner(controller=controller)


def _default_runner() -> UnifiedAutoExecutionRunner:
    global _DEFAULT_RUNNER
    with _DEFAULT_LOCK:
        if _DEFAULT_RUNNER is None:
            _DEFAULT_RUNNER = _build_default_runner()
        return _DEFAULT_RUNNER


def start_unified_auto_execution_runner() -> dict[str, Any]:
    runner = _default_runner()
    runner.start()
    return runner.status()


def stop_unified_auto_execution_runner() -> None:
    global _DEFAULT_RUNNER
    with _DEFAULT_LOCK:
        runner = _DEFAULT_RUNNER
    if runner is not None:
        runner.stop()


def get_unified_auto_execution_status() -> dict[str, Any]:
    return _default_runner().status()


def run_unified_auto_execution_action(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload if isinstance(payload, dict) else {}
    runner = _default_runner()
    runner.start()
    return runner.action(
        str(body.get("environment") or ""),
        str(body.get("action") or ""),
        body,
    )
