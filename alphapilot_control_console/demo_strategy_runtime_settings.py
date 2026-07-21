"""Local audited per-strategy limits for OKX Demo execution."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import state_store
from .risk_profile_store import RISK_PROFILE_STORE_PATH, RiskProfileStore


DEFAULT_MAX_CONCURRENT_SYMBOLS = 1
MAX_CONFIGURABLE_SYMBOLS = 10
DEFAULT_DEMO_LEVERAGE = 1
MAX_DEMO_LEVERAGE = 5


def apply_runtime_risk_profile(
    contract: dict[str, Any],
    profile: dict[str, Any],
    *,
    runtime_overlay_hash: str,
) -> dict[str, Any]:
    """Build an execution view; the immutable release contract stays untouched."""
    updated = deepcopy(contract)
    envelope = (
        dict(updated.get("riskEnvelope"))
        if isinstance(updated.get("riskEnvelope"), dict)
        else {}
    )
    envelope.update({
        "initialEquityUsdt": float(profile["capitalLimitUsdt"]),
        "capitalLimitUsdt": float(profile["capitalLimitUsdt"]),
        "riskPerTradePercent": float(profile["riskPerTradePercent"]),
        "riskPerTradeUsdt": float(profile["riskPerTradeUsdt"]),
        "maxOpenRiskPercent": float(profile["maxOpenRiskPercent"]),
        "maxOpenRiskUsdt": float(profile["maxOpenRiskUsdt"]),
        "maxConcurrentPositions": int(profile["maxConcurrentPositions"]),
        "maxSymbolOpenRiskPercent": float(profile["maxSymbolOpenRiskPercent"]),
        "maxDirectionOpenRiskPercent": float(profile["maxDirectionOpenRiskPercent"]),
        "maxCorrelatedOpenRiskPercent": float(profile["maxCorrelatedOpenRiskPercent"]),
        "maxPortfolioBeta": float(profile["maxPortfolioBeta"]),
        "maxLeverage": int(profile["maxLeverage"]),
        "defaultMaxLeverage": int(profile["maxLeverage"]),
        "marginMode": str(profile["marginMode"]),
        "dailyLossStopPercent": float(profile["dailyLossStopPercent"]),
        "maxDrawdownStopPercent": float(profile["maxDrawdownStopPercent"]),
        "canaryLossStopUsdt": float(profile["canaryLossStopUsdt"]),
        "runtimeRiskOverlayHash": runtime_overlay_hash,
        "runtimeRiskAppliesTo": "new_orders_only",
    })
    updated["riskEnvelope"] = envelope
    binding = (
        deepcopy(updated.get("portfolioRuntimeBinding"))
        if isinstance(updated.get("portfolioRuntimeBinding"), dict)
        else {}
    )
    universe = (
        dict(binding.get("universePolicy"))
        if isinstance(binding.get("universePolicy"), dict)
        else {}
    )
    if universe:
        immutable_cap = int(universe.get("maximumInstrumentCount") or 200)
        universe["maximumInstrumentCount"] = min(
            immutable_cap,
            int(profile["scanTopN"]),
        )
        binding["universePolicy"] = universe
        updated["portfolioRuntimeBinding"] = binding
    updated["runtimeRiskBinding"] = {
        "runtimeRiskOverlayHash": runtime_overlay_hash,
        "appliesTo": "new_orders_only",
        "immutableSourceContractHash": contract.get("contractHash"),
        "releaseMutation": False,
    }
    return updated


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
    risk_store = RiskProfileStore(RISK_PROFILE_STORE_PATH)
    try:
        runtime_overlay = risk_store.get_active_runtime_overlay("okx_demo")
        active_profile = risk_store.get_active_profile("okx_demo")
    finally:
        risk_store.close()
    return {
        "strategyId": normalized,
        "maxConcurrentSymbols": max(
            1,
            min(int(saved.get("maxConcurrentSymbols") or DEFAULT_MAX_CONCURRENT_SYMBOLS), MAX_CONFIGURABLE_SYMBOLS),
        ),
        "leverage": max(
            1,
            min(int(saved.get("leverage") or DEFAULT_DEMO_LEVERAGE), MAX_DEMO_LEVERAGE),
        ),
        "updatedAt": saved.get("updatedAt"),
        "source": saved.get("source") or "demo_strategy_runtime_settings_v13_27_1_5",
        "okxDemoOnly": True,
        "liveExecutionAllowed": False,
        "runtimeRiskOverlayId": (
            runtime_overlay.get("runtimeRiskOverlayId") if runtime_overlay else None
        ),
        "runtimeRiskOverlayHash": (
            runtime_overlay.get("contentHash") if runtime_overlay else None
        ),
        "effectiveRiskProfile": (
            runtime_overlay.get("effectiveProfile") if runtime_overlay else None
        ),
        "effectiveRiskProfileId": (
            runtime_overlay.get("baseRiskProfileId")
            if runtime_overlay
            else active_profile.get("riskProfileId") if active_profile else None
        ),
        "runtimeRiskAppliesTo": "new_orders_only",
        "runningPositionsKeepOpeningProfile": True,
    }


def update_demo_strategy_runtime_settings(
    strategy_id: str,
    max_concurrent_symbols: Any,
    leverage: Any = DEFAULT_DEMO_LEVERAGE,
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
    if isinstance(leverage, bool):
        raise ValueError("leverage_must_be_integer")
    numeric_leverage = float(leverage)
    if not numeric_leverage.is_integer():
        raise ValueError("leverage_must_be_integer")
    requested_leverage = int(numeric_leverage)
    if requested_leverage < 1 or requested_leverage > MAX_DEMO_LEVERAGE:
        raise ValueError("leverage_out_of_range")
    state = state_store.load_state()
    rows = state.get("demoStrategyRuntimeSettings")
    settings = rows if isinstance(rows, dict) else {}
    previous = settings.get(normalized) if isinstance(settings.get(normalized), dict) else {}
    now = state_store.now_iso()
    record = {
        "strategyId": normalized,
        "maxConcurrentSymbols": requested,
        "leverage": requested_leverage,
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
            "previousLeverage": previous.get("leverage") or DEFAULT_DEMO_LEVERAGE,
            "leverage": requested_leverage,
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
