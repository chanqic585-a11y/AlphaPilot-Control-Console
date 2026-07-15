from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_validation_approval_store import (
    StrategyValidationApprovalStore,
)
from alphapilot_control_console.strategy_validation_demo_service import (
    run_strategy_validation_cycle,
)
from alphapilot_control_console.strategy_validation_demo_store import (
    StrategyValidationDemoStore,
)
from alphapilot_control_console.strategy_validation_forward_review import (
    build_strategy_validation_forward_review,
)
from alphapilot_control_console.strategy_validation_hashing import canonical_bytes
from alphapilot_control_console.strategy_validation_release_store import (
    StrategyValidationReleaseStore,
)
from alphapilot_control_console.strategy_validation_risk_gateway import (
    StrategyValidationRiskGateway,
)
from alphapilot_control_console.strategy_validation_risk_store import (
    StrategyValidationRiskStore,
)
from alphapilot_control_console.strategy_validation_runtime_admission import (
    StrategyValidationRuntimeAdmission,
)
from tests.strategy_validation_fixtures import make_release


class _AcceptedClient:
    def place_order(self, payload):
        return {"code": "0", "data": [{"ordId": "demo-order-1", "sCode": "0"}]}


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


class StrategyValidationEndToEndTests(unittest.TestCase):
    def test_formal_release_requires_approval_and_arm_before_reconciled_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = make_release()
            releases = StrategyValidationReleaseStore(
                root / "releases.sqlite", root / "contracts"
            )
            approvals = StrategyValidationApprovalStore(
                root / "approvals.sqlite", release_store=releases
            )
            runtime = StrategyValidationRuntimeAdmission(
                root / "runtime.sqlite",
                release_store=releases,
                approval_store=approvals,
            )
            ledger = StrategyValidationDemoStore(root / "demo.sqlite")
            risk_store = StrategyValidationRiskStore(root / "risk.sqlite")
            try:
                imported = releases.import_bytes(canonical_bytes(release))
                release_id = imported["releaseId"]
                self.assertFalse(runtime.evaluate(release_id, universeFresh=True)["eligible"])

                approvals.approve(
                    releaseId=release_id,
                    releaseHash=release["releaseHash"],
                    riskConfigHash=release["riskConfigHash"],
                    reason="explicit local Demo validation approval",
                    actor="human_local_operator",
                )
                self.assertFalse(runtime.state()["armed"])
                self.assertEqual(
                    runtime.evaluate(release_id, universeFresh=True)["status"], "not_armed"
                )
                runtime.arm(reason="explicit local Demo runtime ARM", actor="human_local_operator")

                result = run_strategy_validation_cycle(
                    approvedReleases=[release],
                    universe={"fresh": True, "eligibleInstrumentIds": ["BTC-USDT-SWAP"]},
                    client=_AcceptedClient(),
                    store=ledger,
                    riskGateway=StrategyValidationRiskGateway(risk_store),
                    admission=runtime,
                    matcher=lambda _release, _universe: {
                        "marketEventHash": "market-event-1",
                        "symbol": "BTC-USDT-SWAP",
                        "side": "buy",
                        "quantity": 1.0,
                        "currency": "USDT",
                        "referencePrice": 100.0,
                        "stopPrice": 98.0,
                        "targetPrice": 104.0,
                        "requestedRiskR": 0.25,
                        "riskSnapshot": _risk_snapshot(),
                    },
                )
                self.assertEqual(result["acceptedOrderCount"], 1)

                ledger.record_fill(
                    fillId="entry-fill-1",
                    exchangeOrderId="demo-order-1",
                    role="entry",
                    price=100.0,
                    quantity=1.0,
                    fee=0.1,
                    funding=0.0,
                    reconciled=True,
                )
                ledger.record_position_snapshot(
                    releaseId=release_id,
                    symbol="BTC-USDT-SWAP",
                    quantity=1.0,
                    averagePrice=100.0,
                    unrealizedPnl=1.0,
                    currency="USDT",
                    reconciled=True,
                )
                ledger.record_order_intent(
                    releaseId=release_id,
                    marketEventHash="market-event-exit-1",
                    clientOrderId="exit-client-order-1",
                    symbol="BTC-USDT-SWAP",
                    side="sell",
                    quantity=1.0,
                    currency="USDT",
                    referencePrice=104.0,
                    stopPrice=102.0,
                    targetPrice=108.0,
                )
                ledger.record_exchange_order(
                    clientOrderId="exit-client-order-1",
                    exchangeOrderId="demo-order-exit-1",
                    status="accepted",
                )
                ledger.record_fill(
                    fillId="exit-fill-1",
                    exchangeOrderId="demo-order-exit-1",
                    role="exit",
                    price=104.0,
                    quantity=1.0,
                    fee=0.1,
                    funding=0.0,
                    reconciled=True,
                )
                ledger.record_closed_trade(
                    closedTradeId="closed-trade-1",
                    releaseId=release_id,
                    marketEventHash="market-event-1",
                    entryFillId="entry-fill-1",
                    exitFillId="exit-fill-1",
                    netPnl=3.8,
                    netR=1.9,
                )

                review = build_strategy_validation_forward_review(
                    store=ledger, release_id=release_id
                )
                self.assertEqual(review["closedTradeCount"], 1)
                self.assertEqual(review["engineeringSmokeCount"], 0)
                self.assertEqual(review["shadowObservationCount"], 0)
                self.assertFalse(review["liveCandidateCreated"])
            finally:
                risk_store.close()
                ledger.close()
                runtime.close()
                approvals.close()
                releases.close()


if __name__ == "__main__":
    unittest.main()
