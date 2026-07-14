from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

from .unified_auto_execution_runner import run_unified_auto_execution_action


_TRUE_VALUES = {"1", "true", "yes", "on"}
_TRANSIENT_STARTUP_BLOCKERS = {
    "demo_market_runtime_warming",
    "demo_market_runtime_warm_timeout",
    "demo_market_runtime_seed_failed",
}


def _enabled(environ: Mapping[str, str], name: str) -> bool:
    return str(environ.get(name, "")).strip().lower() in _TRUE_VALUES


def arm_okx_demo_runtime_on_startup(
    *,
    environ: Mapping[str, str] | None = None,
    action_runner: Callable[[dict[str, Any]], dict[str, Any]] = run_unified_auto_execution_action,
) -> dict[str, Any]:
    source = os.environ if environ is None else environ
    if not _enabled(source, "ALPHAPILOT_OKX_DEMO_LAUNCHER_CONFIRMED"):
        return {
            "status": "not_requested",
            "blocker": "launcher_confirmation_missing",
        }

    required_gates = (
        "ALPHAPILOT_OKX_DEMO_ENABLED",
        "ALPHAPILOT_OKX_DEMO_ORDER_ENABLED",
        "ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED",
    )
    if not all(_enabled(source, name) for name in required_gates):
        return {
            "status": "not_requested",
            "blocker": "demo_gate_disabled",
        }

    try:
        result = action_runner({
            "environment": "okx_demo",
            "action": "start",
            "source": "confirmed_demo_launcher_startup",
        })
    except Exception:
        return {
            "status": "blocked",
            "blocker": "startup_arm_failed",
        }
    if not result.get("ok"):
        blockers = result.get("blockers") if isinstance(result.get("blockers"), list) else []
        blocker = next((str(value) for value in blockers if str(value)), "startup_arm_failed")
        return {
            "status": "blocked",
            "blocker": blocker,
            "result": result,
        }
    return {
        "status": "requested",
        "result": result,
    }


def _transient_startup_blocker(result: Mapping[str, Any]) -> bool:
    blocker = str(result.get("blocker") or "")
    return (
        blocker in _TRANSIENT_STARTUP_BLOCKERS
        or blocker.startswith("demo_market_runtime_start_failed:")
    )


def recover_okx_demo_runtime_on_startup(
    *,
    initial_result: dict[str, Any],
    credential_ready: bool,
    environ: Mapping[str, str] | None = None,
    action_runner: Callable[[dict[str, Any]], dict[str, Any]] = run_unified_auto_execution_action,
    sleeper: Callable[[float], None] = time.sleep,
    retry_delay_seconds: float = 5.0,
    max_attempts: int = 30,
) -> dict[str, Any]:
    """Retry only transient public-market startup failures without weakening ARM gates."""

    if not credential_ready or not _transient_startup_blocker(initial_result):
        return {"status": "not_scheduled", "attemptCount": 0}

    last_result = dict(initial_result)
    for attempt in range(1, max(1, int(max_attempts)) + 1):
        sleeper(max(0.0, float(retry_delay_seconds)))
        last_result = arm_okx_demo_runtime_on_startup(
            environ=environ,
            action_runner=action_runner,
        )
        if (
            last_result.get("status") == "requested"
            and isinstance(last_result.get("result"), dict)
            and last_result["result"].get("ok")
        ):
            return {
                "status": "recovered",
                "attemptCount": attempt,
                "result": last_result,
            }
        if not _transient_startup_blocker(last_result):
            return {
                "status": "blocked",
                "attemptCount": attempt,
                "result": last_result,
            }
    return {
        "status": "exhausted",
        "attemptCount": max(1, int(max_attempts)),
        "result": last_result,
    }


def start_okx_demo_runtime_startup_recovery(
    *,
    initial_result: dict[str, Any],
    credential_ready: bool,
) -> dict[str, Any]:
    """Start a daemon recovery worker only for a validated Demo credential and transient warmup."""

    if not credential_ready or not _transient_startup_blocker(initial_result):
        return {"status": "not_scheduled"}
    thread = threading.Thread(
        target=recover_okx_demo_runtime_on_startup,
        kwargs={
            "initial_result": initial_result,
            "credential_ready": credential_ready,
        },
        name="alphapilot-demo-startup-recovery",
        daemon=True,
    )
    thread.start()
    return {"status": "scheduled", "threadName": thread.name}
