from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_validation_demo_service import run_strategy_validation_cycle
from alphapilot_control_console.strategy_validation_demo_store import StrategyValidationDemoStore
from alphapilot_control_console.strategy_validation_risk_gateway import StrategyValidationRiskGateway
from alphapilot_control_console.strategy_validation_risk_store import StrategyValidationRiskStore
from tests.strategy_validation_fixtures import make_release


class _Admission:
    def evaluate(self, release_id: str, *, universeFresh: bool, riskPaused: bool = False):
        return {"eligible": universeFresh and not riskPaused, "status": "eligible"}


class _Client:
    def __init__(self):
        self.orders = []

    def place_order(self, payload):
        self.orders.append(payload)
        return {"code": "0", "data": [{"ordId": "exchange-order-1", "sCode": "0"}]}


def _risk_snapshot() -> dict:
    return {
        "openRiskR": 0.0,
        "singleSymbolRiskR": 0.0,
        "correlatedClusterRiskR": 0.0,
        "openPositionCount": 0,
        "dailyLossR": 0.0,
        "weeklyLossR": 0.0,
        "consecutiveLosses": 0,
        "demoDrawdownPct": 0.0,
        "marginUtilizationPct": 10.0,
        "reconciliationHealthy": True,
        "dataFresh": True,
    }


class StrategyValidationDemoServiceTests(unittest.TestCase):
    def test_match_creates_real_order_record_and_duplicate_event_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = StrategyValidationDemoStore(root / "demo.sqlite")
            risk_store = StrategyValidationRiskStore(root / "risk.sqlite")
            gateway = StrategyValidationRiskGateway(risk_store)
            release = make_release()
            client = _Client()

            def matcher(_release, _universe):
                return {
                    "marketEventHash": "event-1",
                    "symbol": "BTC-USDT-SWAP",
                    "side": "buy",
                    "quantity": 1.0,
                    "currency": "USDT",
                    "referencePrice": 100.0,
                    "stopPrice": 98.0,
                    "targetPrice": 104.0,
                    "requestedRiskR": 0.25,
                    "riskSnapshot": _risk_snapshot(),
                }

            first = run_strategy_validation_cycle(
                approvedReleases=[release], universe={"fresh": True, "eligibleInstrumentIds": ["BTC-USDT-SWAP"]},
                client=client, store=ledger, riskGateway=gateway, admission=_Admission(), matcher=matcher,
            )
            second = run_strategy_validation_cycle(
                approvedReleases=[release], universe={"fresh": True, "eligibleInstrumentIds": ["BTC-USDT-SWAP"]},
                client=client, store=ledger, riskGateway=gateway, admission=_Admission(), matcher=matcher,
            )

            self.assertEqual(first["acceptedOrderCount"], 1)
            self.assertEqual(second["duplicateEventCount"], 1)
            self.assertEqual(len(client.orders), 1)
            self.assertEqual(ledger.summary()["fillCount"], 0)
            risk_store.close()
            ledger.close()

    def test_no_match_and_risk_rejection_do_not_call_exchange(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = StrategyValidationDemoStore(root / "demo.sqlite")
            risk_store = StrategyValidationRiskStore(root / "risk.sqlite")
            gateway = StrategyValidationRiskGateway(risk_store)
            release = make_release()
            client = _Client()
            no_match = run_strategy_validation_cycle(
                approvedReleases=[release], universe={"fresh": True, "eligibleInstrumentIds": ["BTC-USDT-SWAP"]},
                client=client, store=ledger, riskGateway=gateway, admission=_Admission(),
                matcher=lambda _release, _universe: None,
            )
            risky = run_strategy_validation_cycle(
                approvedReleases=[release], universe={"fresh": True, "eligibleInstrumentIds": ["BTC-USDT-SWAP"]},
                client=client, store=ledger, riskGateway=gateway, admission=_Admission(),
                matcher=lambda _release, _universe: {
                    "marketEventHash": "event-risky", "symbol": "BTC-USDT-SWAP", "side": "buy",
                    "quantity": 1.0, "currency": "USDT", "referencePrice": 100.0,
                    "stopPrice": 98.0, "targetPrice": 104.0, "requestedRiskR": 1.0,
                    "riskSnapshot": _risk_snapshot(),
                },
            )
            self.assertEqual(no_match["matchedSignalCount"], 0)
            self.assertEqual(risky["riskRejectedCount"], 1)
            self.assertEqual(client.orders, [])
            risk_store.close()
            ledger.close()


if __name__ == "__main__":
    unittest.main()
