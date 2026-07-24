from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path

from alphapilot_control_console.demo_execution_store import DemoExecutionStore
from alphapilot_control_console.live_execution_store import LiveExecutionStore
from alphapilot_control_console.trading_terminal_projection import TradingTerminalProjection
from alphapilot_control_console.unified_auto_execution_store import UnifiedAutoExecutionStore


class TradingTerminalProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.runtime_path = self.root / "runtime.sqlite"
        self.demo_path = self.root / "demo.sqlite"
        self.live_path = self.root / "live.sqlite"

        runtime = UnifiedAutoExecutionStore(self.runtime_path)
        runtime.set_desired_enabled("okx_demo", True)
        runtime.record_arm("okx_demo", process_id=str(os.getpid()))
        runtime.update_runtime(
            "okx_demo",
            status="waiting",
            lastHeartbeatAt="2026-07-22T04:00:00+00:00",
            nextEvaluationAt="2026-07-22T05:00:00+00:00",
            lastError=None,
        )
        runtime.append_event(
            "okx_demo",
            "heartbeat_completed",
            {
                "evaluatedReleaseCount": 1,
                "matchedSignalCount": 2,
                "createdOrderCount": 1,
                "evaluationAudit": {
                    "state": "completed",
                    "funnel": {
                        "marketInstrumentCount": 200,
                        "liquidityEligibleInstrumentCount": 168,
                        "componentInstrumentEvaluationCount": 40,
                        "matchedSignalCount": 2,
                        "orderAttemptCount": 1,
                        "filledOrderCount": 1,
                        "openPositionCount": 1,
                    },
                    "releaseAudits": [
                        {
                            "releaseId": "release-v62",
                            "strategyId": "strategy-v62",
                            "timeframe": "1h",
                            "marketInstrumentCount": 200,
                            "liquidityEligibleCount": 168,
                            "deepScreenRequired": 40,
                            "deepScreenCompleted": 40,
                            "matchedSignalCount": 2,
                        },
                        {
                            "releaseId": "release-v62",
                            "strategyId": "strategy-v62",
                            "timeframe": "1h",
                            "marketInstrumentCount": 200,
                            "liquidityEligibleCount": 168,
                            "deepScreenRequired": 40,
                            "deepScreenCompleted": 40,
                            "matchedSignalCount": 2,
                        },
                    ],
                    "stageDurationsMs": {"evaluationMs": 850},
                },
            },
        )
        runtime.close()

        demo = DemoExecutionStore(self.demo_path)
        record = demo.create_intent(
            idempotencyKey="signal-v62",
            demoReleaseId="release-v62",
            signal={
                "strategyId": "strategy-v62",
                "instrumentId": "BTC-USDT-SWAP",
                "side": "buy",
            },
            orderPayload={"instId": "BTC-USDT-SWAP", "side": "buy", "sz": "1"},
        )
        demo.update_record(
            record.recordId,
            status="filled",
            exchangeOrderId="demo-order-1",
            exchangeResponse={"code": "0"},
        )
        demo.set_runtime_flag(
            "lastPortfolioSnapshot",
            {
                "status": "available",
                "accountEquityUsdt": 1198.25,
                "availableEquityUsdt": 987.5,
                "todayRealizedPnlUsdt": -1.25,
                "floatingPnlUsdt": 3.75,
                "positions": [
                    {
                        "strategyId": "strategy-v62",
                        "instrumentId": "BTC-USDT-SWAP",
                        "side": "long",
                        "quantity": 1.0,
                        "entryPrice": 100.0,
                        "markPrice": 103.75,
                        "floatingPnlUsdt": 3.75,
                    }
                ],
                "updatedAt": "2026-07-22T04:00:01+00:00",
            },
        )
        demo.close()

        live = LiveExecutionStore(self.live_path)
        live.close()
        self.projection = TradingTerminalProjection(
            runtime_store_path=self.runtime_path,
            demo_execution_store_path=self.demo_path,
            live_execution_store_path=self.live_path,
            risk_profile_store_path=self.root / "missing-risk.sqlite",
            strategy_policy_store_path=self.root / "missing-policy.sqlite",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_demo_summary_uses_runtime_and_sanitized_account_truth(self) -> None:
        summary = self.projection.summary("okx_demo")

        self.assertEqual(summary["runtimeStatus"], "waiting")
        self.assertTrue(summary["desiredEnabled"])
        self.assertTrue(summary["armed"])
        self.assertEqual(summary["accountDataStatus"], "available")
        self.assertEqual(summary["equity"], 1198.25)
        self.assertEqual(summary["availableBalance"], 987.5)
        self.assertEqual(summary["todayPnl"], -1.25)
        self.assertEqual(summary["floatingPnl"], 3.75)
        self.assertEqual(summary["openPositionCount"], 1)
        self.assertEqual(summary["strategyOrderCount"], 1)
        self.assertEqual(summary["scanFunnel"]["marketInstrumentCount"], 200)
        self.assertEqual(summary["scanFunnel"]["matchedSignalCount"], 2)

    def test_demo_lists_strategy_position_and_sanitized_order(self) -> None:
        strategies = self.projection.strategies("okx_demo")["strategies"]
        positions = self.projection.positions("okx_demo")["positions"]
        orders = self.projection.orders("okx_demo")["orders"]

        self.assertEqual(len(strategies), 1)
        self.assertEqual(strategies[0]["strategyId"], "strategy-v62")
        self.assertEqual(strategies[0]["latestScan"]["matchedSignalCount"], 2)
        self.assertIsNone(strategies[0]["todayPnl"])
        self.assertEqual(strategies[0]["floatingPnl"], 3.75)
        self.assertEqual(positions[0]["instrumentId"], "BTC-USDT-SWAP")
        self.assertEqual(orders[0]["exchangeOrderId"], "demo-order-1")
        self.assertNotIn("exchangeResponse", orders[0])

    def test_order_page_uses_keyset_pagination_without_duplicates(self) -> None:
        demo = DemoExecutionStore(self.demo_path)
        for index in range(1, 5):
            demo.create_intent(
                idempotencyKey=f"signal-page-{index}",
                demoReleaseId="release-v62",
                signal={
                    "strategyId": "strategy-v62",
                    "instrumentId": f"ASSET-{index}-USDT-SWAP",
                    "side": "buy",
                },
                orderPayload={
                    "instId": f"ASSET-{index}-USDT-SWAP",
                    "side": "buy",
                    "sz": "1",
                },
            )
        demo.close()

        first = self.projection.orders_page("okx_demo", limit=2)
        second = self.projection.orders_page(
            "okx_demo",
            limit=2,
            after=first["nextKey"],
        )
        third = self.projection.orders_page(
            "okx_demo",
            limit=2,
            after=second["nextKey"],
        )

        self.assertEqual(len(first["items"]), 2)
        self.assertEqual(len(second["items"]), 2)
        self.assertEqual(len(third["items"]), 1)
        self.assertTrue(first["hasMore"])
        self.assertTrue(second["hasMore"])
        self.assertFalse(third["hasMore"])
        record_ids = [
            item["recordId"]
            for page in (first, second, third)
            for item in page["items"]
        ]
        self.assertEqual(len(record_ids), len(set(record_ids)))
        self.assertEqual(first["totalCount"], 5)
        self.assertNotIn("exchangeResponse", first["items"][0])

    def test_summary_counts_orders_without_loading_full_record_payloads(self) -> None:
        def fail_if_loaded(environment: str) -> list[dict[str, object]]:
            raise AssertionError(f"full record load is forbidden for {environment}")

        self.projection._records = fail_if_loaded  # type: ignore[method-assign]

        summary = self.projection.summary("okx_demo")

        self.assertEqual(summary["strategyOrderCount"], 1)

    def test_strategy_page_does_not_load_all_execution_records(self) -> None:
        def fail_if_loaded(environment: str) -> list[dict[str, object]]:
            raise AssertionError(f"full record load is forbidden for {environment}")

        self.projection._records = fail_if_loaded  # type: ignore[method-assign]

        page = self.projection.strategies_page("okx_demo", limit=1)

        self.assertEqual(len(page["items"]), 1)
        self.assertFalse(page["hasMore"])
        self.assertEqual(page["items"][0]["strategyId"], "strategy-v62")
        self.assertIn("stateVersion", page)

    def test_position_and_runtime_event_pages_are_bounded(self) -> None:
        runtime = UnifiedAutoExecutionStore(self.runtime_path)
        runtime.append_event("okx_demo", "heartbeat_blocked", {"reason": "fixture"})
        runtime.close()

        positions = self.projection.positions_page("okx_demo", limit=1)
        events = self.projection.events_page("okx_demo", limit=1)

        self.assertEqual(len(positions["items"]), 1)
        self.assertFalse(positions["hasMore"])
        self.assertEqual(positions["items"][0]["instrumentId"], "BTC-USDT-SWAP")
        self.assertEqual(len(events["items"]), 1)
        self.assertTrue(events["hasMore"])
        self.assertNotIn("payloadJson", events["items"][0])

    def test_missing_live_snapshot_is_not_reported_as_zero(self) -> None:
        summary = self.projection.summary("okx_live")

        self.assertEqual(
            summary["accountDataStatus"],
            "unavailable_process_credentials_required",
        )
        self.assertIsNone(summary["equity"])
        self.assertIsNone(summary["todayPnl"])
        self.assertIsNone(summary["floatingPnl"])
        self.assertIsNone(summary["openPositionCount"])
        self.assertTrue(any(issue["code"] == "account_snapshot_unavailable" for issue in summary["issues"]))

    def test_stale_process_arm_is_not_reported_as_currently_armed(self) -> None:
        runtime = UnifiedAutoExecutionStore(self.runtime_path)
        runtime.record_arm("okx_demo", process_id="stale-process")
        runtime.close()

        summary = self.projection.summary("okx_demo")

        self.assertFalse(summary["armed"])
        self.assertTrue(
            any(issue["code"] == "process_arm_required" for issue in summary["issues"])
        )

    def test_projection_does_not_create_missing_databases(self) -> None:
        self.projection.summary("okx_demo")
        self.projection.summary("okx_live")

        self.assertFalse((self.root / "missing-risk.sqlite").exists())
        self.assertFalse((self.root / "missing-policy.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
