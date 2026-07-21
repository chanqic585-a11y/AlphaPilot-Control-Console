from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.live_execution_engine import LiveExecutionEngine
from alphapilot_control_console.live_execution_store import LiveExecutionStore
from alphapilot_control_console.execution_outcome_store import ExecutionOutcomeStore
from alphapilot_control_console.risk_profile_store import RiskProfileStore


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class FakeClient:
    def __init__(self) -> None:
        self.orders: list[dict] = []

    def place_protected_order(self, payload: dict) -> dict:
        self.orders.append(payload)
        return {"code": "0", "data": [{"sCode": "0", "ordId": "live-123"}]}

    def get_balance(self, _: str) -> dict:
        return {"code": "0", "data": [{"details": [{"ccy": "USDT", "availEq": "1000"}]}]}

    def get_positions(self) -> dict:
        return {"code": "0", "data": []}

    def get_open_orders(self) -> dict:
        return {"code": "0", "data": []}

    def get_order(self, **_: object) -> dict:
        return {"code": "0", "data": [{"state": "filled", "ordId": "live-123"}]}

    def cancel_all_after(self, _: int) -> dict:
        return {"code": "0", "data": []}


class FakeAdaptiveAdapter:
    def __init__(self) -> None:
        self.closed: list[dict] = []

    def record_closed_outcome(self, outcome: dict, *, signal: dict) -> dict:
        self.closed.append({"outcome": outcome, "signal": signal})
        return {"status": "recorded", "learningSampleId": "sample-1"}


class LiveExecutionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = LiveExecutionStore(Path(self.directory.name) / "live.sqlite")
        profile_store = RiskProfileStore(Path(self.directory.name) / "profiles.sqlite")
        self.profile = profile_store.get_active_profile("live_canary")
        profile_store.close()
        assert self.profile is not None
        release = {
            "schemaVersion": "live_release_contract_v1",
            "strategyCandidateId": "candidate-1",
            "riskProfileId": self.profile["riskProfileId"],
            "riskProfileHash": self.profile["contentHash"],
            "executionBoundary": {
                "environment": "okx_live_canary_only",
                "mechanicalExecutionAllowed": True,
                "withdrawAllowed": False,
            },
        }
        self.contract = {
            "schemaVersion": "alphapilot_live_release_v1",
            "liveReleaseId": "release-1",
            "liveReleaseHash": hashlib.sha256(canonical(release).encode("utf-8")).hexdigest(),
            "status": "live_canary_approved",
            "release": release,
        }
        self.signal = {
            "candidateId": "candidate-1",
            "signalTime": "2026-07-11T00:00:00Z",
            "instId": "BTC-USDT-SWAP",
            "side": "buy",
            "tdMode": "isolated",
            "ordType": "market",
            "sz": "0.001",
            "entryPrice": 100.0,
            "takeProfitPrice": 102.0,
            "stopLossPrice": 99.0,
            "notionalUsdt": 50.0,
            "leverage": 1,
            "riskPercent": 0.2,
        }
        self.portfolio = {
            "availableEquityUsdt": 1000.0,
            "openPositionCount": 0,
            "openRiskPercent": 0.0,
            "dailyLossPercent": 0.0,
            "drawdownPercent": 0.0,
            "canaryLossUsdt": 0.0,
            "activeStrategyIds": [],
            "positionsByStrategy": {},
            "positionsBySymbol": {},
            "openRiskByStrategy": {},
            "openRiskBySymbol": {},
            "openRiskByDirection": {},
            "openRiskByCorrelationGroup": {},
            "dataFresh": True,
            "liquidityPassed": True,
            "cooldownActive": False,
            "reconciliationMatched": True,
        }
        self.client = FakeClient()
        self.engine = LiveExecutionEngine(client=self.client, store=self.store)
        self.store.set_runtime_flag("killSwitch", False)
        self.store.set_runtime_flag("paused", False)

    def tearDown(self) -> None:
        self.store.close()
        self.directory.cleanup()

    def test_approved_release_submits_one_idempotent_protected_order(self) -> None:
        first = self.engine.execute(contract=self.contract, activeProfile=self.profile, signal=self.signal, portfolio=self.portfolio)
        second = self.engine.execute(contract=self.contract, activeProfile=self.profile, signal=self.signal, portfolio=self.portfolio)

        self.assertEqual(first.recordId, second.recordId)
        self.assertEqual(len(self.client.orders), 1)
        self.assertEqual(first.status, "submitted")
        self.assertTrue(self.client.orders[0]["attachAlgoOrds"][0]["slTriggerPx"])

    def test_profile_hash_mismatch_and_missing_reconciliation_fail_closed(self) -> None:
        wrong = {**self.profile, "contentHash": "wrong"}
        with self.assertRaises(PermissionError):
            self.engine.execute(contract=self.contract, activeProfile=wrong, signal=self.signal, portfolio=self.portfolio)
        with self.assertRaises(RuntimeError):
            self.engine.execute(
                contract=self.contract,
                activeProfile=self.profile,
                signal=self.signal,
                portfolio={**self.portfolio, "reconciliationMatched": False},
            )

    def test_initial_store_is_fail_closed(self) -> None:
        another = LiveExecutionStore(Path(self.directory.name) / "fresh.sqlite")
        try:
            self.assertTrue(another.runtime_state()["killSwitchActive"])
            self.assertTrue(another.runtime_state()["paused"])
        finally:
            another.close()

    def test_closed_live_outcome_preserves_release_and_profile_lineage(self) -> None:
        outcome_store = ExecutionOutcomeStore(Path(self.directory.name) / "outcomes.sqlite")
        adaptive = FakeAdaptiveAdapter()
        engine = LiveExecutionEngine(
            client=self.client,
            store=self.store,
            outcomeStore=outcome_store,
            adaptiveAdapter=adaptive,
        )
        record = engine.execute(
            contract=self.contract,
            activeProfile=self.profile,
            signal=self.signal,
            portfolio=self.portfolio,
        )
        engine.reconcile_record(record.recordId)
        outcome = engine.record_closed_outcome(
            recordId=record.recordId,
            dataSnapshotId="snapshot-1",
            closeEvidence={
                "timeframe": "1h",
                "direction": "long",
                "entryAt": "2026-07-11T00:01:00+00:00",
                "exitAt": "2026-07-11T01:00:00+00:00",
                "entryPrice": 100.0,
                "exitPrice": 102.0,
                "quantity": 1.0,
                "grossPnl": 2.0,
                "feePaid": 0.1,
                "slippagePaid": 0.1,
                "netPnl": 1.8,
                "riskAmount": 1.0,
                "exitReason": "target",
                "sourcePayloadHash": "live-close-fill-hash",
            },
        )
        self.assertEqual(outcome.environment, "live")
        self.assertEqual(outcome.outcome["riskProfileId"], self.profile["riskProfileId"])
        self.assertEqual(len(adaptive.closed), 1)
        self.assertEqual(adaptive.closed[0]["outcome"]["sourceEntityId"], record.recordId)
        self.assertEqual(adaptive.closed[0]["signal"]["signalTime"], self.signal["signalTime"])
        outcome_store.close()


if __name__ == "__main__":
    unittest.main()
