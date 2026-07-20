"""Process-local lifecycle for the public-only prewarmed Demo market runtime."""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable

from .demo_prewarmed_market_state import ConfirmedCloseEvent, DemoPrewarmedMarketState
from .demo_release_scanner import (
    fetch_okx_public_instrument_metadata,
    fetch_okx_public_market_snapshot,
    fetch_okx_usdt_swap_universe,
)
from .dynamic_top200_universe import MAXIMUM_INSTRUMENT_COUNT
from .okx_public_market_runtime import OkxPublicMarketRuntime


_LOCK = threading.RLock()
_RUNTIME: OkxPublicMarketRuntime | None = None
_LAST_STARTUP: dict[str, Any] = {
    "started": False,
    "blockers": ["demo_market_runtime_not_started"],
}


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _build_runtime() -> OkxPublicMarketRuntime:
    return OkxPublicMarketRuntime(
        state=DemoPrewarmedMarketState(screening_limit=MAXIMUM_INSTRUMENT_COUNT),
        universe_loader=fetch_okx_usdt_swap_universe,
        snapshot_loader=fetch_okx_public_market_snapshot,
        metadata_loader=fetch_okx_public_instrument_metadata,
    )


def get_demo_market_runtime() -> OkxPublicMarketRuntime:
    global _RUNTIME
    with _LOCK:
        if _RUNTIME is None:
            _RUNTIME = _build_runtime()
        return _RUNTIME


def start_demo_market_runtime(
    *,
    close_listener: Callable[[ConfirmedCloseEvent], None] | None = None,
    force: bool = False,
    warm_timeout_seconds: float = 15.0,
    seed_attempts: int = 5,
    seed_retry_delay_seconds: float = 0.5,
) -> dict[str, Any]:
    global _LAST_STARTUP
    if not force and not _enabled("ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED"):
        _LAST_STARTUP = {
            "started": False,
            "disabled": True,
            "blockers": ["demo_automation_gate_disabled"],
        }
        return dict(_LAST_STARTUP)
    try:
        from .approved_top200_demo_runtime import load_approved_top200_demo_runtime

        approved_runtime = load_approved_top200_demo_runtime()
        contracts = [
            row
            for row in approved_runtime.get("componentContracts") or []
            if isinstance(row, dict)
        ]
        if approved_runtime.get("approved") is not True or not contracts:
            _LAST_STARTUP = {
                "started": False,
                "blockers": ["approved_top200_demo_runtime_unavailable"],
            }
            return dict(_LAST_STARTUP)
        runtime = get_demo_market_runtime()
        refreshed: dict[str, Any] = {}
        attempt_count = 0
        for attempt_count in range(1, max(1, int(seed_attempts)) + 1):
            refreshed = runtime.refresh_subscriptions(contracts)
            if refreshed.get("seeded"):
                break
            if attempt_count < max(1, int(seed_attempts)):
                time.sleep(max(0.0, float(seed_retry_delay_seconds)))
        if not refreshed.get("seeded"):
            _LAST_STARTUP = {
                "started": False,
                "blockers": ["demo_market_runtime_seed_failed"],
                "seedAttemptCount": attempt_count,
                "refresh": refreshed,
            }
            return dict(_LAST_STARTUP)
        if close_listener is not None:
            runtime.add_close_listener(close_listener)
        runtime.start()
        deadline = time.monotonic() + max(0.0, float(warm_timeout_seconds))
        runtime_status = runtime.status()
        while not runtime_status.get("warm") and time.monotonic() < deadline:
            time.sleep(0.05)
            runtime_status = runtime.status()
        if not runtime_status.get("warm"):
            _LAST_STARTUP = {
                "started": False,
                "blockers": ["demo_market_runtime_warming"],
                "refresh": refreshed,
                "runtime": runtime_status,
            }
            return dict(_LAST_STARTUP)
        _LAST_STARTUP = {
            "started": True,
            "blockers": [],
            "seedAttemptCount": attempt_count,
            "refresh": refreshed,
            "runtime": runtime_status,
        }
    except Exception as error:
        _LAST_STARTUP = {
            "started": False,
            "blockers": [f"demo_market_runtime_start_failed:{type(error).__name__}"],
        }
    return dict(_LAST_STARTUP)


def stop_demo_market_runtime() -> None:
    with _LOCK:
        runtime = _RUNTIME
    if runtime is not None:
        runtime.stop()


def get_demo_market_runtime_status() -> dict[str, Any]:
    with _LOCK:
        startup = dict(_LAST_STARTUP)
        runtime = _RUNTIME
    return {
        "startup": startup,
        "runtime": runtime.status() if runtime is not None else {},
    }
