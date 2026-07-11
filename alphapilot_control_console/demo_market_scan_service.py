"""Persist compact public OKX full-market scan summaries per strategy."""

from __future__ import annotations

from typing import Any, Callable

from . import state_store
from .okx_market_universe import fetch_okx_usdt_swap_universe


UniverseLoader = Callable[[int], dict[str, Any]]


def _strategy_id(value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("strategy_id_required")
    return normalized


def _compact_candidates(rows: Any, limit: int = 20) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows[:limit], start=1):
        if not isinstance(row, dict) or not str(row.get("instId") or "").strip():
            continue
        result.append(
            {
                "rank": int(row.get("rank") or index),
                "instId": str(row.get("instId")),
                "quoteVolumeProxy": row.get("quoteVolumeProxy"),
                "spreadPct": row.get("spreadPct"),
                "scanStatus": row.get("scanStatus") or "liquidity_eligible",
                "reason": row.get("reason"),
            }
        )
    return result


def _save_scan(strategy_id: str, scan: dict[str, Any]) -> dict[str, Any]:
    state = state_store.load_state()
    rows = state.get("demoStrategyMarketScans")
    scans = rows if isinstance(rows, dict) else {}
    scans[strategy_id] = scan
    state["demoStrategyMarketScans"] = scans
    state_store.save_state(state)
    state_store.append_audit(
        "demo_strategy_public_market_scan_saved",
        {
            "strategyId": strategy_id,
            "marketScope": scan.get("marketScope"),
            "totalInstrumentCount": scan.get("totalInstrumentCount"),
            "liquidityEligibleCount": scan.get("liquidityEligibleCount"),
            "strategyMatchedCount": scan.get("strategyMatchedCount"),
            "publicOnly": True,
            "createsOrder": False,
            "liveExecutionAllowed": False,
        },
    )
    return scan


def get_demo_strategy_market_scan(strategy_id: str) -> dict[str, Any]:
    normalized = _strategy_id(strategy_id)
    state = state_store.load_state()
    rows = state.get("demoStrategyMarketScans")
    scans = rows if isinstance(rows, dict) else {}
    value = scans.get(normalized)
    return dict(value) if isinstance(value, dict) else {}


def scan_demo_strategy_public_universe(
    strategy_id: str,
    *,
    screening_limit: int = 20,
    universe_loader: UniverseLoader = fetch_okx_usdt_swap_universe,
) -> dict[str, Any]:
    normalized = _strategy_id(strategy_id)
    universe = universe_loader(screening_limit)
    candidates = _compact_candidates(universe.get("screeningPool"))
    errors = list(universe.get("errors") or [])
    scan = {
        "strategyId": normalized,
        "marketScope": universe.get("marketScope") or "okx_usdt_linear_perpetual_full_market",
        "totalInstrumentCount": int(universe.get("totalInstrumentCount") or 0),
        "liveUsdtLinearSwapCount": int(universe.get("liveUsdtLinearSwapCount") or 0),
        "liquidityEligibleCount": int(universe.get("liquidityEligibleCount") or 0),
        "deepScreenedCount": 0,
        "strategyMatchedCount": None,
        "currentTopCandidate": candidates[0]["instId"] if candidates else None,
        "rankedCandidates": candidates,
        "progress": dict(universe.get("progress") or {}),
        "errors": errors,
        "matchStatus": "release_required_for_strategy_match",
        "updatedAt": state_store.now_iso(),
        "source": "demo_strategy_public_market_scan_v13_27_1_5",
        "publicOnly": True,
        "createsOrder": False,
        "liveExecutionAllowed": False,
    }
    _save_scan(normalized, scan)
    return {
        "ok": not errors and scan["totalInstrumentCount"] > 0,
        "scan": scan,
        "createsOrder": False,
        "liveExecutionAllowed": False,
    }


def save_demo_release_scan(strategy_id: str, release_scan: dict[str, Any]) -> dict[str, Any]:
    """Save a compact post-release strategy match without storing factor payloads."""

    normalized = _strategy_id(strategy_id)
    universe = release_scan.get("universe") if isinstance(release_scan.get("universe"), dict) else {}
    candidates = _compact_candidates(universe.get("rankedCandidates"))
    scan = {
        "strategyId": normalized,
        "marketScope": universe.get("marketScope") or "okx_usdt_linear_perpetual_full_market",
        "totalInstrumentCount": int(universe.get("totalInstrumentCount") or 0),
        "liveUsdtLinearSwapCount": int(universe.get("liveUsdtLinearSwapCount") or 0),
        "liquidityEligibleCount": int(universe.get("liquidityEligibleCount") or 0),
        "deepScreenedCount": int((release_scan.get("progress") or {}).get("completed") or 0),
        "strategyMatchedCount": int(universe.get("strategyMatchedCount") or 0),
        "currentTopCandidate": next(
            (row["instId"] for row in candidates if row.get("scanStatus") == "matched"),
            candidates[0]["instId"] if candidates else None,
        ),
        "rankedCandidates": candidates,
        "progress": dict(release_scan.get("progress") or {}),
        "errors": list(universe.get("errors") or []),
        "matchStatus": "strategy_match_completed",
        "updatedAt": state_store.now_iso(),
        "source": "demo_release_full_market_scan_v13_27_1_5",
        "publicOnly": True,
        "createsOrder": False,
        "liveExecutionAllowed": False,
    }
    return _save_scan(normalized, scan)
