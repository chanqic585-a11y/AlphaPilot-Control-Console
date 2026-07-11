"""Local audited per-strategy limits for OKX Demo execution."""

from __future__ import annotations

from typing import Any

from . import state_store


DEFAULT_MAX_CONCURRENT_SYMBOLS = 1
MAX_CONFIGURABLE_SYMBOLS = 10


def _strategy_id(value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("strategy_id_required")
    return normalized


def get_demo_strategy_runtime_settings(strategy_id: str) -> dict[str, Any]:
    normalized = _strategy_id(strategy_id)
    state = state_store.load_state()
    settings = state.get("demoStrategyRuntimeSettings")
    rows = settings if isinstance(settings, dict) else {}
    saved = rows.get(normalized) if isinstance(rows.get(normalized), dict) else {}
    return {
        "strategyId": normalized,
        "maxConcurrentSymbols": max(
            1,
            min(int(saved.get("maxConcurrentSymbols") or DEFAULT_MAX_CONCURRENT_SYMBOLS), MAX_CONFIGURABLE_SYMBOLS),
        ),
        "updatedAt": saved.get("updatedAt"),
        "source": saved.get("source") or "demo_strategy_runtime_settings_v13_27_1_5",
        "okxDemoOnly": True,
        "liveExecutionAllowed": False,
    }


def update_demo_strategy_runtime_settings(
    strategy_id: str,
    max_concurrent_symbols: Any,
) -> dict[str, Any]:
    normalized = _strategy_id(strategy_id)
    if isinstance(max_concurrent_symbols, bool):
        raise ValueError("max_concurrent_symbols_must_be_integer")
    numeric = float(max_concurrent_symbols)
    if not numeric.is_integer():
        raise ValueError("max_concurrent_symbols_must_be_integer")
    requested = int(numeric)
    if requested < 1 or requested > MAX_CONFIGURABLE_SYMBOLS:
        raise ValueError("max_concurrent_symbols_out_of_range")
    state = state_store.load_state()
    rows = state.get("demoStrategyRuntimeSettings")
    settings = rows if isinstance(rows, dict) else {}
    previous = settings.get(normalized) if isinstance(settings.get(normalized), dict) else {}
    now = state_store.now_iso()
    record = {
        "strategyId": normalized,
        "maxConcurrentSymbols": requested,
        "updatedAt": now,
        "source": "demo_strategy_runtime_settings_v13_27_1_5",
        "okxDemoOnly": True,
        "liveExecutionAllowed": False,
    }
    settings[normalized] = record
    state["demoStrategyRuntimeSettings"] = settings
    state_store.save_state(state)
    state_store.append_audit(
        "demo_strategy_runtime_settings_updated",
        {
            "strategyId": normalized,
            "previousMaxConcurrentSymbols": previous.get("maxConcurrentSymbols") or DEFAULT_MAX_CONCURRENT_SYMBOLS,
            "maxConcurrentSymbols": requested,
            "okxDemoOnly": True,
            "createsOrder": False,
            "liveExecutionAllowed": False,
        },
    )
    return record


def effective_symbol_limit(
    *,
    requested: int,
    portfolio_limit: int,
    remaining_slots: int,
    risk_slots: int,
    matched_count: int,
) -> dict[str, Any]:
    limits = {
        "requested": max(0, min(int(requested), MAX_CONFIGURABLE_SYMBOLS)),
        "portfolio_limit": max(0, int(portfolio_limit)),
        "remaining_slots": max(0, int(remaining_slots)),
        "risk_slots": max(0, int(risk_slots)),
        "matched_count": max(0, int(matched_count)),
    }
    effective = min(limits.values())
    binding = next(key for key, value in limits.items() if value == effective)
    return {
        **limits,
        "effective": effective,
        "bindingLimit": binding,
        "okxDemoOnly": True,
        "liveExecutionAllowed": False,
    }
