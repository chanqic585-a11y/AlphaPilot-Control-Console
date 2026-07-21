from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.manual_intervention_store import ManualInterventionStore


class ManualInterventionStoreTests(unittest.TestCase):
    def test_intervention_is_append_only_and_does_not_execute(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ManualInterventionStore(Path(directory) / "interventions.sqlite")
            first = store.record(
                environment="okx_demo",
                action="tighten_stop",
                operator="user_manual",
                strategy_id="strategy_1",
                instrument_id="BTC-USDT-SWAP",
                position_id="position_1",
                before={"side": "long", "stopLoss": 100.0},
                after={"side": "long", "stopLoss": 101.0},
                reason="reduce_open_risk",
            )
            second = store.record(
                environment="okx_demo",
                action="pause_strategy",
                operator="user_manual",
                strategy_id="strategy_1",
                instrument_id=None,
                position_id=None,
                before={"allowNewEntries": True},
                after={"allowNewEntries": False},
                reason="manual_review",
            )
            events = store.list_events("okx_demo")
            store.close()

        self.assertTrue(first["manualIntervention"])
        self.assertFalse(first["executionEnabled"])
        self.assertFalse(second["executionEnabled"])
        self.assertEqual([event["sequence"] for event in events], [1, 2])

    def test_stop_can_only_be_tightened(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ManualInterventionStore(Path(directory) / "interventions.sqlite")
            with self.assertRaises(ValueError):
                store.record(
                    environment="okx_demo",
                    action="tighten_stop",
                    operator="user_manual",
                    strategy_id="strategy_1",
                    instrument_id="BTC-USDT-SWAP",
                    position_id="position_1",
                    before={"side": "long", "stopLoss": 100.0},
                    after={"side": "long", "stopLoss": 99.0},
                    reason="invalid_widening",
                )
            store.close()


if __name__ == "__main__":
    unittest.main()
