from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import alphapilot_control_console.exchange_demo_simulation as exchange_demo
import alphapilot_control_console.local_sandbox_runner as local_runner
import alphapilot_control_console.sandbox_auto_runner as auto_runner
import alphapilot_control_console.state_store as state_store
import alphapilot_control_console.strategy_stage_service as stage_service
from alphapilot_control_console.local_simulation_retirement import LocalSimulationRetiredError


def _catalog() -> dict:
    strategies = []
    for index in range(10):
        strategy_id = f"strategy-{index + 1}"
        strategies.append({
            "strategyId": strategy_id,
            "taskId": f"task-{index + 1}",
            "name": f"策略 {index + 1}",
            "timeframe": "1h" if index < 5 else "1d",
            "direction": "short" if index < 5 else "long_research",
            "score": 100 - index,
            "targetR": 2.0,
            "selectedPairs": [f"COIN{index + 1}/USDT:USDT"],
            "metrics": {
                "tradeCount": 40 + index,
                "winRatePct": 50 + index / 10,
                "profitFactor": 1.4 + index / 100,
                "totalR": 10 + index,
            },
            "testMetrics": {},
        })
    return {"summary": {"totalUsableStrategies": 10}, "strategies": strategies}


class StrategyStageServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.state_patch = patch.object(state_store, "STATE_PATH", root / "console_state.json")
        self.audit_patch = patch.object(state_store, "AUDIT_PATH", root / "audit_log.jsonl")
        self.state_patch.start()
        self.audit_patch.start()

    def tearDown(self) -> None:
        self.audit_patch.stop()
        self.state_patch.stop()
        self.temp_dir.cleanup()

    def test_promotion_moves_visibility_without_deleting_samples(self) -> None:
        state = state_store.load_state()
        state["paperObservationLogs"] = {
            "task-1": [{"logId": "sample-1", "outcomeR": 2.0, "createdAt": "2026-07-11T00:00:00Z"}]
        }
        state_store.save_state(state)

        with patch.object(stage_service, "build_usable_strategy_catalog", return_value=_catalog()):
            result = stage_service.promote_strategies_to_demo_trial()

        self.assertEqual(result["promotedCount"], 10)
        self.assertEqual(result["stageBoard"]["summary"]["localSandboxCount"], 0)
        self.assertEqual(result["stageBoard"]["summary"]["demoTrialCount"], 10)
        self.assertEqual(state_store.list_paper_observation_logs("task-1")[0]["logId"], "sample-1")

    def test_demo_pool_contains_all_promoted_strategies_once(self) -> None:
        with patch.object(stage_service, "build_usable_strategy_catalog", return_value=_catalog()):
            stage_service.promote_strategies_to_demo_trial()
            board = stage_service.build_strategy_stage_board()

        with patch.object(exchange_demo, "build_strategy_stage_board", return_value=board):
            trial_pool, _ = exchange_demo._build_demo_trial_pool()
            candidates, summary = exchange_demo._build_strategy_candidates(limit=10)

        self.assertEqual(len(trial_pool), 10)
        self.assertEqual(summary["demoTrialCount"], 10)
        self.assertEqual(len(candidates), 10)
        self.assertEqual(len({row["strategyId"] for row in candidates}), 10)
        self.assertTrue(all(row["targetR"] == 2.0 for row in trial_pool))
        self.assertTrue(all(row["formalDemoRelease"] is False for row in trial_pool))

    def test_promoted_strategies_are_not_run_in_local_sandbox(self) -> None:
        with patch.object(local_runner, "save_local_sandbox_run") as save_run:
            with self.assertRaisesRegex(LocalSimulationRetiredError, "local_simulation_retired"):
                local_runner.run_local_sandbox({"quantEnginePath": self.temp_dir.name})
        save_run.assert_not_called()

    def test_auto_runner_defaults_to_five_minutes_and_daily_capacity(self) -> None:
        self.assertEqual(state_store.DEFAULT_LOCAL_SANDBOX_AUTO_RUNNER["intervalMinutes"], 5)
        self.assertEqual(state_store.DEFAULT_LOCAL_SANDBOX_AUTO_RUNNER["maxRunsPerDay"], 288)
        current = {
            **state_store.DEFAULT_LOCAL_SANDBOX_AUTO_RUNNER,
            "enabled": True,
            "intervalMinutes": 360,
            "maxRunsPerDay": 4,
            "status": "daily_limit_reached",
            "todayRunCount": 13,
            "todayKey": auto_runner._beijing_date_key(),
            "nextRunAt": "2099-01-01T00:00:00+00:00",
        }
        with patch.object(auto_runner, "get_local_sandbox_auto_runner_state", return_value=current), patch.object(
            auto_runner,
            "update_local_sandbox_auto_runner_state",
            side_effect=lambda payload, event=None: payload,
        ):
            updated = auto_runner.LocalSandboxAutoRunner().update_settings({
                "enabled": True,
                "intervalMinutes": 5,
                "maxRunsPerDay": 288,
            })

        self.assertEqual(updated["intervalMinutes"], 5)
        self.assertEqual(updated["maxRunsPerDay"], 288)
        self.assertEqual(updated["status"], "waiting")
        self.assertNotEqual(updated["nextRunAt"], current["nextRunAt"])


if __name__ == "__main__":
    unittest.main()
