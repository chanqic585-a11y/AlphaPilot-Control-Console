from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.demo_engineering_smoke_contract import build_demo_engineering_smoke_contract
from alphapilot_control_console.demo_engineering_smoke_service import (
    build_demo_engineering_smoke_status,
    reconcile_demo_engineering_smoke,
    run_demo_engineering_smoke,
)
from alphapilot_control_console.runtime_identity import RuntimeIdentity


def universe() -> dict:
    return {
        "status": "usable",
        "environment": "demo",
        "eligibleInstrumentIds": ["BTC-USDT-SWAP"],
        "selectedInstrumentId": "BTC-USDT-SWAP",
        "instrumentConstraints": {"BTC-USDT-SWAP": {"minSz": "0.01", "lotSz": "0.01"}},
        "publicManifestHash": "public-hash",
        "authenticatedInstrumentHash": "private-hash",
        "blockers": [],
    }


def runtime_identity(contract: dict) -> RuntimeIdentity:
    return RuntimeIdentity(
        runtimeId="engineering-smoke-test-runtime",
        environment="okx_demo",
        processId=1,
        repositoryCommit="test-commit",
        repositoryTag="test-tag",
        moduleRootHashes={"demo_engineering_smoke": "test-module-hash"},
        releaseId=str(contract["releaseId"]),
        releaseHash=str(contract["releaseHash"]),
        riskOverlayHash="engineering-smoke-risk-overlay",
        modelHash="engineering-smoke-model",
        modelPolicyHash="engineering-smoke-model-policy",
        approvalHash="engineering-smoke-approval",
        armHash="engineering-smoke-arm",
        runtimeLeaseId="engineering-smoke-lease",
        startedAt="2026-07-15T00:00:00+00:00",
        lastHeartbeatAt="2026-07-15T00:01:00+00:00",
        lastScanAt="2026-07-15T00:02:00+00:00",
        nextScanAt="2026-07-15T00:03:00+00:00",
    )


class SuccessfulClient:
    def __init__(self) -> None:
        self.placeCalls: list[dict] = []
        self.orderCalls = 0
        self.positionCalls = 0
        self.cancelCalls = 0

    def set_leverage(self, **_kwargs: object) -> dict:
        return {"code": "0", "data": [{}]}

    def place_order(self, payload: dict) -> dict:
        self.placeCalls.append(dict(payload))
        suffix = "open" if len(self.placeCalls) == 1 else "close"
        return {"code": "0", "data": [{"ordId": suffix, "clOrdId": payload["clOrdId"], "sCode": "0", "sMsg": ""}]}

    def get_order(self, **kwargs: object) -> dict:
        self.orderCalls += 1
        return {"code": "0", "data": [{"ordId": kwargs.get("ordId") or "open", "state": "filled", "accFillSz": "0.01"}]}

    def get_positions(self, instrumentId: str | None = None, instrumentType: str | None = None) -> dict:
        self.positionCalls += 1
        if self.positionCalls == 1:
            return {"code": "0", "data": [{"instId": instrumentId, "pos": "0.01", "posSide": "net"}]}
        return {"code": "0", "data": []}

    def cancel_order(self, **_kwargs: object) -> dict:
        self.cancelCalls += 1
        return {"code": "0", "data": [{"sCode": "0"}]}


class DemoEngineeringSmokeServiceTests(unittest.TestCase):
    def _contract(self, directory: str) -> dict:
        return build_demo_engineering_smoke_contract(
            createdAt="2026-07-15T00:00:00+00:00",
            outputDir=Path(directory) / "contracts",
        )

    def test_runs_one_minimum_size_lifecycle_and_reconciles_flat(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "engineering.sqlite"
            client = SuccessfulClient()
            contract = self._contract(temporary)
            result = run_demo_engineering_smoke(
                client=client,
                contract=contract,
                universe=universe(),
                deterministicTrigger=True,
                storePath=path,
                runtimeIdentity=runtime_identity(contract),
            )
            status = build_demo_engineering_smoke_status(storePath=path)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["instrumentId"], "BTC-USDT-SWAP")
        self.assertEqual(result["minimumOrderSize"], "0.01")
        self.assertEqual(result["orderStatus"], "filled")
        self.assertEqual(result["positionStatus"], "flat")
        self.assertEqual(result["exitStatus"], "filled")
        self.assertEqual(result["reconciliationStatus"], "passed")
        self.assertEqual(len(client.placeCalls), 2)
        self.assertEqual(client.placeCalls[0]["sz"], "0.01")
        self.assertTrue(client.placeCalls[1]["reduceOnly"])
        self.assertEqual(status["summary"]["orderAttemptCount"], 1)
        self.assertEqual(status["summary"]["orphanCount"], 0)

    def test_duplicate_completed_trigger_does_not_place_another_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "engineering.sqlite"
            client = SuccessfulClient()
            contract = self._contract(temporary)
            options = dict(
                client=client,
                contract=contract,
                universe=universe(),
                deterministicTrigger=True,
                storePath=path,
                runtimeIdentity=runtime_identity(contract),
            )
            first = run_demo_engineering_smoke(**options)
            duplicate = run_demo_engineering_smoke(**options)

        self.assertEqual(first["runId"], duplicate["runId"])
        self.assertEqual(len(client.placeCalls), 2)
        self.assertEqual(duplicate["duplicateAttemptCount"], 1)

    def test_fails_closed_for_empty_or_unavailable_universe_and_non_deterministic_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            contract = self._contract(temporary)
            path = Path(temporary) / "engineering.sqlite"
            blocked_inputs = (
                ({"status": "blocked", "eligibleInstrumentIds": []}, True),
                ({**universe(), "selectedInstrumentId": "ETH-USDT-SWAP"}, True),
                (universe(), False),
            )
            for current_universe, trigger in blocked_inputs:
                with self.subTest(universe=current_universe, trigger=trigger):
                    with self.assertRaises((ValueError, PermissionError, RuntimeError)):
                        run_demo_engineering_smoke(
                            client=SuccessfulClient(),
                            contract=contract,
                            universe=current_universe,
                            deterministicTrigger=trigger,
                            storePath=path,
                        )

    def test_order_rejection_retries_at_most_three_times(self) -> None:
        class RejectedClient(SuccessfulClient):
            def place_order(self, payload: dict) -> dict:
                self.placeCalls.append(dict(payload))
                return {"code": "1", "msg": "rejected", "data": [{"sCode": "51000", "sMsg": "bad request"}]}

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "engineering.sqlite"
            client = RejectedClient()
            contract = self._contract(temporary)
            options = dict(
                client=client,
                contract=contract,
                universe=universe(),
                deterministicTrigger=True,
                storePath=path,
                runtimeIdentity=runtime_identity(contract),
            )
            results = [run_demo_engineering_smoke(**options) for _ in range(4)]

        self.assertEqual(len(client.placeCalls), 3)
        self.assertTrue(all(result["status"] == "failed" for result in results))
        self.assertEqual(results[-1]["errorCode"], "retry_exhausted")

    def test_status_timeout_is_failed_even_when_cancel_reconciles_flat(self) -> None:
        class TimeoutClient(SuccessfulClient):
            def get_order(self, **kwargs: object) -> dict:
                self.orderCalls += 1
                return {"code": "0", "data": [{"ordId": kwargs.get("ordId") or "open", "state": "live"}]}

            def get_positions(self, instrumentId: str | None = None, instrumentType: str | None = None) -> dict:
                self.positionCalls += 1
                return {"code": "0", "data": []}

        with tempfile.TemporaryDirectory() as temporary:
            contract = self._contract(temporary)
            result = run_demo_engineering_smoke(
                client=TimeoutClient(),
                contract=contract,
                universe=universe(),
                deterministicTrigger=True,
                storePath=Path(temporary) / "engineering.sqlite",
                runtimeIdentity=runtime_identity(contract),
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["errorCode"], "order_status_timeout")
        self.assertEqual(result["exitStatus"], "canceled")

    def test_orphan_position_or_reconciliation_mismatch_fails(self) -> None:
        class OrphanClient(SuccessfulClient):
            def get_positions(self, instrumentId: str | None = None, instrumentType: str | None = None) -> dict:
                self.positionCalls += 1
                return {"code": "0", "data": [{"instId": instrumentId, "pos": "0.01", "posSide": "net"}]}

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "engineering.sqlite"
            client = OrphanClient()
            contract = self._contract(temporary)
            result = run_demo_engineering_smoke(
                client=client,
                contract=contract,
                universe=universe(),
                deterministicTrigger=True,
                storePath=path,
                runtimeIdentity=runtime_identity(contract),
            )
            reconciled = reconcile_demo_engineering_smoke(client=client, storePath=path)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["positionStatus"], "orphan")
        self.assertEqual(result["reconciliationStatus"], "mismatch")
        self.assertGreaterEqual(reconciled["summary"]["orphanCount"], 1)


if __name__ == "__main__":
    unittest.main()
