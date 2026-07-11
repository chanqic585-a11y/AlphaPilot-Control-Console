from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import alphapilot_control_console.state_store as state_store
from alphapilot_control_console.demo_strategy_runtime_settings import (
    effective_symbol_limit,
    get_demo_strategy_runtime_settings,
    update_demo_strategy_runtime_settings,
)


class DemoStrategyRuntimeSettingsTests(unittest.TestCase):
    def test_default_is_one_and_update_is_persisted_with_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            state_store, "STATE_PATH", Path(directory) / "console_state.json"
        ), patch.object(state_store, "AUDIT_PATH", Path(directory) / "audit.jsonl"):
            default = get_demo_strategy_runtime_settings("strategy-1")
            updated = update_demo_strategy_runtime_settings("strategy-1", 4)
            loaded = get_demo_strategy_runtime_settings("strategy-1")
            audit_text = state_store.AUDIT_PATH.read_text(encoding="utf-8")

        self.assertEqual(default["maxConcurrentSymbols"], 1)
        self.assertEqual(updated["maxConcurrentSymbols"], 4)
        self.assertEqual(loaded["maxConcurrentSymbols"], 4)
        self.assertIn("demo_strategy_runtime_settings_updated", audit_text)
        self.assertNotIn("apiKey", audit_text)
        self.assertFalse(updated["liveExecutionAllowed"])

    def test_effective_limit_uses_the_smallest_risk_and_capacity_limit(self) -> None:
        result = effective_symbol_limit(
            requested=3,
            portfolio_limit=2,
            remaining_slots=1,
            risk_slots=2,
            matched_count=5,
        )

        self.assertEqual(result["effective"], 1)
        self.assertEqual(result["requested"], 3)
        self.assertEqual(result["bindingLimit"], "remaining_slots")

    def test_fractional_symbol_limit_is_rejected_instead_of_truncated(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_concurrent_symbols_must_be_integer"):
            update_demo_strategy_runtime_settings("strategy-1", 2.5)


if __name__ == "__main__":
    unittest.main()
