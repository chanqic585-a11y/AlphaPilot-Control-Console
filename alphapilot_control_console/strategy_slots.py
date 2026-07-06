from __future__ import annotations

from typing import Any

from .config import DEFAULT_STRATEGY_SLOTS, SAFETY_BOUNDARY
from .importer import scan_quant_engine
from .state_store import now_iso


def list_strategy_slots() -> dict[str, Any]:
    scanned = scan_quant_engine()
    strategies_by_id = {item["strategyId"]: item for item in scanned["strategies"]}
    slots = []

    for slot in DEFAULT_STRATEGY_SLOTS:
        expected_id = slot["expectedStrategyId"]
        strategy = strategies_by_id.get(expected_id) if expected_id else None
        resolved_status = slot["status"]
        if strategy:
            resolved_status = strategy.get("consoleStatus") or strategy.get("suggestedStatus") or "research_only"
        slots.append({
            "slotId": slot["slotId"],
            "label": slot["label"],
            "role": slot["role"],
            "status": resolved_status,
            "expectedStrategyId": expected_id,
            "strategy": strategy,
            "empty": strategy is None,
            "manualImportOnly": True,
            "executionAllowed": False,
            "ordersAllowed": False,
        })

    return {
        "version": "V13.7.1",
        "source": "alphapilot_control_console_v13_7_1",
        "generatedAt": now_iso(),
        "safetyBoundary": SAFETY_BOUNDARY,
        "slots": slots,
    }
