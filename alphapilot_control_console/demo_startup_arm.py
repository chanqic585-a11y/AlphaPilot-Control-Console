from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from .unified_auto_execution_runner import run_unified_auto_execution_action


_TRUE_VALUES = {"1", "true", "yes", "on"}


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
    return {
        "status": "requested",
        "result": result,
    }
