from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from alphapilot_control_console.live_auto_execution_service import (
    _portfolio_snapshot,
    run_live_auto_execution_batch,
    scan_live_release,
)
from alphapilot_control_console.execution_runtime_lease import ExecutionRuntimeLeaseStore
from alphapilot_control_console.live_execution_store import LiveExecutionStore
from alphapilot_control_console.runtime_identity import RuntimeIdentity


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def profile() -> dict:
    return {
        "riskProfileId": "profile-live-1",
        "contentHash": "profile-hash-1",
        "profile": {
            "capitalLimitUsdt": 1000.0,
            "maxActiveStrategies": 2,
            "maxConcurrentPositions": 2,
            "maxPositionsPerStrategy": 1,
            "maxPositionsPerSymbol": 1,
            "maxOrderNotionalUsdt": 100.0,
            "maxLeverage": 1,
            "riskPerTradePercent": 0.25,
            "maxOpenRiskPercent": 0.5,
            "rewardRiskRatio": 2.0,
            "allowedStrategyIds": ["candidate-1"],
        },
    }


def release_export(*, include_strategy: bool = True) -> dict:
    active = profile()
    release = {
        "schemaVersion": "live_release_contract_v1",
        "strategyCandidateId": "candidate-1",
        "riskProfileId": active["riskProfileId"],
        "riskProfileHash": active["contentHash"],
        "executionBoundary": {
            "environment": "okx_live_canary_only",
            "manualReleaseApprovalRequired": True,
            "mechanicalExecutionAllowed": True,
            "withdrawAllowed": False,
        },
        "protectionPolicy": {
            "attachedTakeProfitRequired": True,
            "attachedStopLossRequired": True,
            "minimumRewardRiskRatio": 2.0,
            "privateStateReconciliationRequired": True,
            "restartRecoveryRequired": True,
            "unknownStatePausesEntries": True,
            "killSwitchRequired": True,
        },
    }
    if include_strategy:
        release["strategy"] = {
            "familyKey": "breakout",
            "marketDefinition": {"timeframe": "1h", "eligibleInstruments": ["BTC-USDT-SWAP"]},
            "forwardSignalPolicy": {"direction": "long", "rules": []},
        }
    return {
        "schemaVersion": "alphapilot_live_release_v1",
        "liveReleaseId": "release-1",
        "liveReleaseHash": hashlib.sha256(canonical(release).encode("utf-8")).hexdigest(),
        "status": "live_canary_approved",
        "release": release,
    }


def runtime_identity_factory(export: dict, active_profile: dict, claim: object) -> RuntimeIdentity:
    now = datetime.now(UTC)
    return RuntimeIdentity(
        runtimeId="test-live-runtime",
        environment="okx_live",
        processId=1,
        repositoryCommit="a" * 40,
        repositoryTag="v-test",
        moduleRootHashes={"execution": "b" * 64},
        releaseId=str(export["liveReleaseId"]),
        releaseHash=str(export["liveReleaseHash"]),
        riskOverlayHash=str(active_profile["contentHash"]),
        modelHash="c" * 64,
        modelPolicyHash="d" * 64,
        approvalHash="e" * 64,
        armHash="f" * 64,
        runtimeLeaseId=str(getattr(claim, "ownerId", "test-lease")),
        startedAt=(now - timedelta(seconds=2)).isoformat(),
        lastHeartbeatAt=(now - timedelta(seconds=1)).isoformat(),
        lastScanAt=now.isoformat(),
        nextScanAt=(now + timedelta(hours=1)).isoformat(),
    )


class FakeLiveClient:
    def __init__(self) -> None:
        self.orders: list[dict] = []

    def get_balance(self, _currency: str = "USDT") -> dict:
        return {"code": "0", "data": [{"details": [{"ccy": "USDT", "availEq": "1000"}]}]}

    def get_positions(self) -> dict:
        return {"code": "0", "data": []}

    def get_open_orders(self) -> dict:
        return {"code": "0", "data": []}

    def place_protected_order(self, payload: dict) -> dict:
        self.orders.append(dict(payload))
        return {"code": "0", "data": [{"sCode": "0", "ordId": "live-order-1"}]}

    def get_order(self, **_kwargs: object) -> dict:
        return {"code": "0", "data": [{"state": "live", "ordId": "live-order-1"}]}


class LiveAutoExecutionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store_path = Path(self.directory.name) / "live.sqlite"
        store = LiveExecutionStore(self.store_path)
        store.set_runtime_flag("killSwitch", False)
        store.set_runtime_flag("paused", False)
        store.set_runtime_flag("lastReconciliationMatched", True)
        store.close()
        self.environment = {
            "ALPHAPILOT_OKX_LIVE_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_READ_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_CANARY_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_ORDER_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_AUTOMATION_ENABLED": "1",
            "ALPHAPILOT_OKX_LIVE_API_KEY": "test-key",
            "ALPHAPILOT_OKX_LIVE_SECRET_KEY": "test-secret",
            "ALPHAPILOT_OKX_LIVE_PASSPHRASE": "test-passphrase",
        }

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_private_read_persists_sanitized_live_account_snapshot(self) -> None:
        class PositionClient(FakeLiveClient):
            def get_balance(self, _currency: str = "USDT") -> dict:
                return {
                    "code": "0",
                    "apiKey": "must-not-survive",
                    "data": [{"details": [{"ccy": "USDT", "eq": "1000", "availEq": "975"}]}],
                }

            def get_positions(self) -> dict:
                return {
                    "code": "0",
                    "data": [
                        {
                            "instId": "BTC-USDT-SWAP",
                            "pos": "1",
                            "posSide": "long",
                            "avgPx": "60000",
                            "markPx": "60200",
                            "upl": "2",
                            "secret": "must-not-survive",
                        }
                    ],
                }

        store = LiveExecutionStore(self.store_path)
        portfolio = _portfolio_snapshot(
            PositionClient(),
            store,
            profile(),
            [{"candidateId": "candidate-1", "instId": "BTC-USDT-SWAP", "dataFresh": True, "liquidityPassed": True}],
        )
        snapshot = store.get_runtime_flag("lastPortfolioSnapshot")
        store.close()

        self.assertEqual(portfolio["availableEquityUsdt"], 975.0)
        self.assertEqual(snapshot["positions"][0]["instrumentId"], "BTC-USDT-SWAP")
        self.assertEqual(snapshot["floatingPnlUsdt"], 2.0)
        self.assertNotIn("must-not-survive", str(snapshot))

    def test_release_without_frozen_strategy_definition_fails_before_order(self) -> None:
        client = FakeLiveClient()
        with patch(
            "alphapilot_control_console.live_auto_execution_service.discover_live_releases",
            return_value=([release_export(include_strategy=False)], []),
        ), patch(
            "alphapilot_control_console.live_auto_execution_service._active_live_profile",
            return_value=profile(),
        ):
            result = run_live_auto_execution_batch(
                ["release-1"],
                client=client,
                store_path=self.store_path,
                environment=self.environment,
            )

        self.assertFalse(result["ok"])
        self.assertIn("live_release_strategy_definition_missing", result["blockers"])
        self.assertEqual(client.orders, [])

    def test_live_scanner_inherits_the_active_profile_leverage_limit(self) -> None:
        captured: dict = {}

        def fake_scan(contract: dict, **_kwargs: object) -> dict:
            captured.update(contract)
            return {"signals": [], "rejections": [], "blockers": []}

        with patch(
            "alphapilot_control_console.live_auto_execution_service.scan_immutable_demo_release",
            side_effect=fake_scan,
        ):
            result = scan_live_release(release_export(), profile())

        self.assertEqual(result["blockers"], [])
        self.assertEqual(captured["riskEnvelope"]["defaultMaxLeverage"], 1)

    def test_armed_batch_submits_one_idempotent_protected_order(self) -> None:
        client = FakeLiveClient()
        scanner_signal = {
            "candidateId": "scanner-signal-1",
            "signalTime": "2026-07-12T10:00:00+00:00",
            "instId": "BTC-USDT-SWAP",
            "side": "buy",
            "posSide": "long",
            "tdMode": "isolated",
            "ordType": "market",
            "sz": "1",
            "entryPrice": 100.0,
            "takeProfitPrice": 102.0,
            "stopLossPrice": 99.0,
            "notionalUsdt": 50.0,
            "leverage": 1,
            "riskPercent": 0.25,
            "strategyFamilyId": "breakout",
            "correlationGroup": "BTC",
            "dataFresh": True,
            "liquidityPassed": True,
        }
        with patch(
            "alphapilot_control_console.live_auto_execution_service.discover_live_releases",
            return_value=([release_export()], []),
        ), patch(
            "alphapilot_control_console.live_auto_execution_service._active_live_profile",
            return_value=profile(),
        ), patch(
            "alphapilot_control_console.live_auto_execution_service.scan_immutable_demo_release",
            return_value={"signals": [scanner_signal], "rejections": [], "blockers": []},
        ):
            first = run_live_auto_execution_batch(
                ["release-1"],
                client=client,
                store_path=self.store_path,
                environment=self.environment,
                runtime_identity_factory=runtime_identity_factory,
            )
            second = run_live_auto_execution_batch(
                ["release-1"],
                client=client,
                store_path=self.store_path,
                environment=self.environment,
                runtime_identity_factory=runtime_identity_factory,
            )

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(first["createdOrderCount"], 1)
        self.assertEqual(len(client.orders), 1)
        protection = client.orders[0]["attachAlgoOrds"][0]
        self.assertEqual(protection["tpTriggerPx"], "102.0")
        self.assertEqual(protection["slTriggerPx"], "99.0")

    def test_existing_live_execution_lease_blocks_batch_before_order(self) -> None:
        lease_store = ExecutionRuntimeLeaseStore(self.store_path)
        claim = lease_store.acquire(
            environment="okx_live",
            owner_id="live-engineering-smoke",
            ttl_seconds=60,
        )
        client = FakeLiveClient()
        scanner_signal = {
            "candidateId": "scanner-signal-1",
            "signalTime": "2026-07-12T10:00:00+00:00",
            "sourceTimestamp": "2026-07-12T09:59:00+00:00",
            "availableAt": "2026-07-12T09:59:10+00:00",
            "decisionAt": "2026-07-12T10:00:00+00:00",
            "orderSendAt": "2026-07-12T10:00:01+00:00",
            "instId": "BTC-USDT-SWAP",
            "side": "buy",
            "posSide": "long",
            "tdMode": "isolated",
            "ordType": "market",
            "sz": "1",
            "entryPrice": 100.0,
            "takeProfitPrice": 102.0,
            "stopLossPrice": 99.0,
            "notionalUsdt": 50.0,
            "leverage": 1,
            "riskPercent": 0.25,
            "strategyFamilyId": "breakout",
            "correlationGroup": "BTC",
            "dataFresh": True,
            "liquidityPassed": True,
        }
        try:
            with patch(
                "alphapilot_control_console.live_auto_execution_service.discover_live_releases",
                return_value=([release_export()], []),
            ), patch(
                "alphapilot_control_console.live_auto_execution_service._active_live_profile",
                return_value=profile(),
            ), patch(
                "alphapilot_control_console.live_auto_execution_service.scan_immutable_demo_release",
                return_value={"signals": [scanner_signal], "rejections": [], "blockers": []},
            ):
                result = run_live_auto_execution_batch(
                    ["release-1"],
                    client=client,
                    store_path=self.store_path,
                    environment=self.environment,
                )
        finally:
            lease_store.release(claim)
            lease_store.close()

        self.assertFalse(result["ok"])
        self.assertEqual(result["blockers"], ["execution_runtime_lease_unavailable"])
        self.assertEqual(client.orders, [])


if __name__ == "__main__":
    unittest.main()
