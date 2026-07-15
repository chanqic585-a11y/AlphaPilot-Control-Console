from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_validation_demo_store import StrategyValidationDemoStore
from alphapilot_control_console.strategy_validation_forward_review import build_strategy_validation_forward_review


class StrategyValidationForwardReviewTests(unittest.TestCase):
    def test_only_reconciled_closed_strategy_validation_trades_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StrategyValidationDemoStore(Path(directory) / "demo.sqlite")
            empty = build_strategy_validation_forward_review(store=store)
            self.assertEqual(empty["closedTradeCount"], 0)
            self.assertEqual(empty["reviewStatus"], "collecting")

            for index in range(30):
                entry_client = f"entry-client-{index}"
                exit_client = f"exit-client-{index}"
                store.record_order_intent(
                    releaseId="release-1", marketEventHash=f"event-{index}", clientOrderId=entry_client,
                    symbol="BTC-USDT-SWAP", side="buy", quantity=1.0, currency="USDT",
                    referencePrice=100.0, stopPrice=98.0, targetPrice=104.0,
                )
                store.record_exchange_order(clientOrderId=entry_client, exchangeOrderId=f"entry-order-{index}", status="filled")
                store.record_fill(fillId=f"entry-fill-{index}", exchangeOrderId=f"entry-order-{index}", role="entry", price=100.0, quantity=1.0, fee=0.1, funding=0.0, reconciled=True)
                store.record_order_intent(
                    releaseId="release-1", marketEventHash=f"exit-event-{index}", clientOrderId=exit_client,
                    symbol="BTC-USDT-SWAP", side="sell", quantity=1.0, currency="USDT",
                    referencePrice=104.0, stopPrice=98.0, targetPrice=104.0,
                )
                store.record_exchange_order(clientOrderId=exit_client, exchangeOrderId=f"exit-order-{index}", status="filled")
                store.record_fill(fillId=f"exit-fill-{index}", exchangeOrderId=f"exit-order-{index}", role="exit", price=104.0, quantity=1.0, fee=0.1, funding=0.0, reconciled=True)
                store.record_closed_trade(
                    closedTradeId=f"trade-{index}", releaseId="release-1", marketEventHash=f"event-{index}",
                    entryFillId=f"entry-fill-{index}", exitFillId=f"exit-fill-{index}", netPnl=3.8, netR=1.9,
                )
            review = build_strategy_validation_forward_review(store=store)
            self.assertEqual(review["closedTradeCount"], 30)
            self.assertEqual(review["reviewStatus"], "preliminary_review_available")
            self.assertFalse(review["liveApprovalCreated"])
            store.close()


if __name__ == "__main__":
    unittest.main()
