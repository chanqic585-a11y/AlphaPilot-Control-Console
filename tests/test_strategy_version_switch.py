from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_version_switch import (
    StrategyVersionSwitchStore,
)


class StrategyVersionSwitchTests(unittest.TestCase):
    def test_new_entries_switch_keeps_running_position_identity_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StrategyVersionSwitchStore(Path(directory) / "switch.sqlite")
            store.register(
                strategy_id="portfolio_alpha",
                release_id="release_v1",
                release_hash="hash_v1",
                actor="system_seed",
            )
            position_bindings = [
                {
                    "positionId": "position_1",
                    "releaseId": "release_v1",
                    "releaseHash": "hash_v1",
                    "riskOverlayHash": "risk_v1",
                }
            ]

            switched = store.switch_version(
                strategy_id="portfolio_alpha",
                release_id="release_v2",
                release_hash="hash_v2",
                mode="new_entries_only",
                open_position_bindings=position_bindings,
                actor="user_manual",
                reason="deploy_new_candidate",
            )
            state = store.get_state("portfolio_alpha")
            store.close()

        self.assertEqual(switched["newEntryReleaseId"], "release_v2")
        self.assertEqual(switched["newEntryReleaseHash"], "hash_v2")
        self.assertEqual(state["openPositionBindings"], position_bindings)
        self.assertEqual(state["openPositionBindings"][0]["releaseId"], "release_v1")
        self.assertFalse(switched["executionEnabled"])

    def test_pause_close_only_resume_and_rollback_are_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StrategyVersionSwitchStore(Path(directory) / "switch.sqlite")
            store.register(
                strategy_id="portfolio_alpha",
                release_id="release_v1",
                release_hash="hash_v1",
                actor="system_seed",
            )
            store.switch_version(
                strategy_id="portfolio_alpha",
                release_id="release_v2",
                release_hash="hash_v2",
                mode="new_entries_only",
                open_position_bindings=[],
                actor="user_manual",
                reason="unit_test",
            )
            paused = store.control(
                "portfolio_alpha", action="pause_new_entries", actor="user_manual"
            )
            close_only = store.control(
                "portfolio_alpha", action="close_only", actor="user_manual"
            )
            resumed = store.control(
                "portfolio_alpha", action="resume_new_entries", actor="user_manual"
            )
            rolled_back = store.rollback(
                "portfolio_alpha",
                open_position_bindings=[],
                actor="user_manual",
                reason="rollback_test",
            )
            events = store.list_events("portfolio_alpha")
            store.close()

        self.assertFalse(paused["allowNewEntries"])
        self.assertTrue(close_only["closeOnly"])
        self.assertTrue(resumed["allowNewEntries"])
        self.assertFalse(resumed["closeOnly"])
        self.assertEqual(rolled_back["newEntryReleaseId"], "release_v1")
        self.assertEqual(rolled_back["action"], "rolled_back")
        self.assertEqual([event["sequence"] for event in events], list(range(1, 7)))

    def test_flatten_then_switch_waits_while_positions_are_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StrategyVersionSwitchStore(Path(directory) / "switch.sqlite")
            store.register(
                strategy_id="portfolio_alpha",
                release_id="release_v1",
                release_hash="hash_v1",
                actor="system_seed",
            )
            pending = store.switch_version(
                strategy_id="portfolio_alpha",
                release_id="release_v2",
                release_hash="hash_v2",
                mode="flatten_then_switch",
                open_position_bindings=[{"positionId": "position_1"}],
                actor="user_manual",
                reason="flatten_first",
            )
            store.close()

        self.assertEqual(pending["status"], "pending_flatten")
        self.assertEqual(pending["newEntryReleaseId"], "release_v1")
        self.assertFalse(pending["allowNewEntries"])
        self.assertTrue(pending["closeOnly"])


if __name__ == "__main__":
    unittest.main()
