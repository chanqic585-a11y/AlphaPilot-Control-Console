from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_validation_demo_store import StrategyValidationDemoStore


class StrategyValidationDemoStoreTests(unittest.TestCase):
    def test_market_event_and_exchange_identifiers_are_unique(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StrategyValidationDemoStore(Path(directory) / "demo.sqlite")
            intent = store.record_order_intent(
                releaseId="release-1", marketEventHash="event-1", clientOrderId="client-1",
                symbol="BTC-USDT-SWAP", side="buy", quantity=1.0, currency="USDT",
                referencePrice=100.0, stopPrice=98.0, targetPrice=104.0,
            )
            self.assertEqual(intent["status"], "created")
            with self.assertRaises(ValueError):
                store.record_order_intent(
                    releaseId="release-1", marketEventHash="event-1", clientOrderId="client-2",
                    symbol="BTC-USDT-SWAP", side="buy", quantity=1.0, currency="USDT",
                    referencePrice=100.0, stopPrice=98.0, targetPrice=104.0,
                )
            store.close()

    def test_closed_trade_requires_reconciled_entry_and_exit_fills(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StrategyValidationDemoStore(Path(directory) / "demo.sqlite")
            store.record_order_intent(
                releaseId="release-1", marketEventHash="event-1", clientOrderId="entry-client",
                symbol="BTC-USDT-SWAP", side="buy", quantity=1.0, currency="USDT",
                referencePrice=100.0, stopPrice=98.0, targetPrice=104.0,
            )
            store.record_exchange_order(
                clientOrderId="entry-client", exchangeOrderId="entry-order", status="filled"
            )
            store.record_fill(
                fillId="entry-fill", exchangeOrderId="entry-order", role="entry",
                price=100.0, quantity=1.0, fee=0.1, funding=0.0, reconciled=True,
            )
            with self.assertRaises(ValueError):
                store.record_closed_trade(
                    closedTradeId="trade-1", releaseId="release-1", marketEventHash="event-1",
                    entryFillId="entry-fill", exitFillId="missing", netPnl=3.8, netR=1.9,
                )
            store.record_order_intent(
                releaseId="release-1", marketEventHash="event-exit", clientOrderId="exit-client",
                symbol="BTC-USDT-SWAP", side="sell", quantity=1.0, currency="USDT",
                referencePrice=104.0, stopPrice=98.0, targetPrice=104.0,
            )
            store.record_exchange_order(
                clientOrderId="exit-client", exchangeOrderId="exit-order", status="filled"
            )
            store.record_fill(
                fillId="exit-fill", exchangeOrderId="exit-order", role="exit",
                price=104.0, quantity=1.0, fee=0.1, funding=0.0, reconciled=True,
            )
            result = store.record_closed_trade(
                closedTradeId="trade-1", releaseId="release-1", marketEventHash="event-1",
                entryFillId="entry-fill", exitFillId="exit-fill", netPnl=3.8, netR=1.9,
            )
            self.assertEqual(result["reconciliationStatus"], "reconciled")
            store.close()


if __name__ == "__main__":
    unittest.main()
