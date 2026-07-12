from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import alphapilot_control_console.evolution_demo_service as service
from alphapilot_control_console.demo_arbitrator import DemoArbitrationResult
from alphapilot_control_console.demo_execution_store import DemoExecutionStore


class EvolutionDemoServiceTests(unittest.TestCase):
    def test_resume_clears_ordinary_pause_and_records_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.sqlite"
            store = DemoExecutionStore(path)
            store.set_runtime_flag("paused", True)
            store.set_runtime_flag("pauseReason", "private_connection_disabled")
            store.close()

            service.resume_evolution_demo_runtime(path)

            reopened = DemoExecutionStore(path)
            self.assertFalse(reopened.get_runtime_flag("paused", True))
            self.assertIsNone(reopened.get_runtime_flag("pauseReason", "missing"))
            reopened.close()
            connection = sqlite3.connect(path)
            events = connection.execute(
                "SELECT eventType FROM DemoExecutionEvents ORDER BY eventId DESC LIMIT 1"
            ).fetchone()
            connection.close()
        self.assertEqual(events[0], "demo_resumed")

    def test_resume_does_not_clear_kill_switch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.sqlite"
            store = DemoExecutionStore(path)
            store.set_runtime_flag("paused", True)
            store.set_runtime_flag("killSwitch", True)
            store.close()

            with self.assertRaisesRegex(RuntimeError, "kill switch"):
                service.resume_evolution_demo_runtime(path)

            reopened = DemoExecutionStore(path)
            self.assertTrue(reopened.get_runtime_flag("paused", False))
            self.assertTrue(reopened.get_runtime_flag("killSwitch", False))
            reopened.close()

    def test_default_status_is_blocked_without_release_or_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            service, "STORE_PATH", Path(directory) / "demo.sqlite"
        ), patch.object(service, "_contract_paths", return_value=[]), patch.dict(os.environ, {}, clear=True):
            status = service.build_evolution_demo_status()

        self.assertFalse(status["summary"]["ready"])
        self.assertIn("no_eligible_demo_release", status["blockers"])
        self.assertIn("okx_demo_credentials_missing", status["blockers"])
        self.assertFalse(status["safetyBoundary"]["liveExecutionAllowed"])
        self.assertFalse(status["safetyBoundary"]["withdrawAllowed"])

    def test_contract_validation_rejects_risk_envelope_expansion(self) -> None:
        contract = {
            "schemaVersion": "alphapilot_control_console_demo_v1",
            "demoReleaseId": "release-1",
            "strategyCandidateId": "candidate-1",
            "status": "demo_eligible",
            "releaseContentHash": "release-hash",
            "riskEnvelope": {
                "initialEquityUsdt": 1000.0,
                "riskPerTradePercent": 0.25,
                "maxOpenRiskPercent": 1.0,
                "maxOrderNotionalUsdt": 500.0,
                "maxConcurrentPositions": 3,
            },
            "executionBoundary": {
                "environment": "okx_demo_only",
                "automaticDemoExecutionAllowed": True,
                "liveExecutionAllowed": False,
                "withdrawAllowed": False,
                "rawCredentialFieldsAllowed": False,
            },
        }
        contract["contractHash"] = service._contract_hash(contract)

        with self.assertRaisesRegex(ValueError, "maxOrderNotionalUsdt"):
            service.validate_demo_contract(contract)

    def test_override_contract_validation_rejects_live_promotion(self) -> None:
        contract = {
            "schemaVersion": "alphapilot_control_console_demo_v1",
            "demoReleaseId": "release-override",
            "strategyCandidateId": "candidate-1",
            "status": "demo_eligible",
            "releaseMode": "experimental_override",
            "releaseContentHash": "release-hash",
            "livePromotionAllowed": True,
            "riskEnvelope": {
                "initialEquityUsdt": 1000.0,
                "riskPerTradePercent": 0.25,
                "maxOpenRiskPercent": 1.0,
                "maxOrderNotionalUsdt": 250.0,
                "maxConcurrentPositions": 3,
                "rewardRiskRatio": 2.0,
            },
            "executionBoundary": {
                "environment": "okx_demo_only",
                "automaticDemoExecutionAllowed": True,
                "liveExecutionAllowed": False,
                "withdrawAllowed": False,
                "rawCredentialFieldsAllowed": False,
            },
        }
        contract["contractHash"] = service._contract_hash(contract)

        with self.assertRaisesRegex(PermissionError, "promotion"):
            service.validate_demo_contract(contract)

    def test_cycle_ignores_external_signals_and_uses_internal_scanner(self) -> None:
        ready_status = {"blockers": [], "summary": {"ready": True}}
        contract = {"demoReleaseId": "release-1"}

        class FakeStore:
            def close(self) -> None:
                return None

        class FakeEngine:
            def __init__(self, **_kwargs: object) -> None:
                pass

            def recover_open_records(self) -> list[object]:
                return []

        with patch.object(service, "build_evolution_demo_status", return_value=ready_status), patch.object(
            service, "discover_demo_contracts", return_value=([contract], [])
        ), patch.object(
            service,
            "scan_immutable_demo_release",
            return_value={"signals": [], "rejections": [], "blockers": []},
        ), patch.object(service, "DemoExecutionStore", return_value=FakeStore()), patch.object(
            service, "DemoExecutionEngine", FakeEngine
        ), patch.object(service, "OkxDemoClient", return_value=object()), patch.object(
            service, "load_okx_demo_credentials", return_value=object()
        ), patch.object(
            service,
            "_portfolio_from_demo_account",
            return_value={
                "availableEquityUsdt": 1000.0,
                "openPositionCount": 0,
                "openRiskPercent": 0.0,
                "dailyLossPercent": 0.0,
                "drawdownPercent": 0.0,
                "reconciliationMatched": True,
            },
        ):
            result = service.run_evolution_demo_cycle(
                {"demoReleaseId": "release-1", "signals": [{"side": "buy"}]}
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["externalSignalsIgnored"], 1)
        self.assertEqual(result["created"], [])

    def test_status_exposes_redacted_demo_closed_outcomes_for_operator_pnl(self) -> None:
        class FakeOutcomeStore:
            def list_outcomes(self) -> list[object]:
                return [
                    SimpleNamespace(
                        executionOutcomeId="outcome-1",
                        environment="okx_demo",
                        sourceRecordId="record-1",
                        releaseId="release-1",
                        releaseHash="release-hash",
                        strategyCandidateId="strategy-1",
                        dataSnapshotId="snapshot-1",
                        outcome={"trade": {"netPnl": 2.5, "feePaid": 0.2, "slippagePaid": 0.1}},
                        contentHash="outcome-hash",
                        createdAt="2026-07-11T00:00:00+00:00",
                    )
                ]

            def close(self) -> None:
                return None

        with tempfile.TemporaryDirectory() as directory, patch.object(
            service, "STORE_PATH", Path(directory) / "demo.sqlite"
        ), patch.object(service, "_contract_paths", return_value=[]), patch.object(
            service, "ExecutionOutcomeStore", return_value=FakeOutcomeStore(), create=True
        ), patch.dict(os.environ, {}, clear=True):
            status = service.build_evolution_demo_status()

        self.assertEqual(status["summary"]["closedOutcomeCount"], 1)
        self.assertEqual(status["summary"]["realizedNetPnl"], 2.5)
        self.assertEqual(status["recentOutcomes"][0]["strategyCandidateId"], "strategy-1")
        self.assertNotIn("exchangeResponse", status["recentOutcomes"][0])

    def test_cycle_enforces_per_strategy_symbol_limit_before_arbitration(self) -> None:
        ready_status = {"blockers": [], "summary": {"ready": True}}
        contract = {
            "demoReleaseId": "release-1",
            "strategyCandidateId": "strategy-1",
            "riskEnvelope": {
                "maxConcurrentPositions": 3,
                "maxPositionsPerStrategy": 2,
                "maxOpenRiskPercent": 1.0,
                "riskPerTradePercent": 0.25,
            },
        }
        signals = [
            {
                "candidateId": f"signal-{index}",
                "strategyCandidateId": "strategy-1",
                "instId": f"COIN{index}-USDT-SWAP",
                "side": "buy",
                "riskPercent": 0.25,
                "dataFresh": True,
                "liquidityPassed": True,
            }
            for index in range(5)
        ]

        class FakeStore:
            def close(self) -> None:
                return None

            def get_runtime_flag(self, _key: str, default: object = None) -> object:
                return default

        class FakeEngine:
            def __init__(self, **_kwargs: object) -> None:
                pass

            def recover_open_records(self) -> list[object]:
                return []

        with patch.object(service, "build_evolution_demo_status", return_value=ready_status), patch.object(
            service, "discover_demo_contracts", return_value=([contract], [])
        ), patch.object(
            service,
            "scan_immutable_demo_release",
            return_value={"signals": signals, "rejections": [], "blockers": []},
        ), patch.object(
            service,
            "save_demo_release_scan",
            return_value={},
            create=True,
        ) as save_scan, patch.object(
            service, "DemoExecutionStore", return_value=FakeStore()
        ), patch.object(
            service, "DemoExecutionEngine", FakeEngine
        ), patch.object(service, "OkxDemoClient", return_value=object()), patch.object(
            service, "load_okx_demo_credentials", return_value=object()
        ), patch.object(
            service,
            "_portfolio_from_demo_account",
            return_value={
                "availableEquityUsdt": 1000.0,
                "openPositionCount": 0,
                "openRiskPercent": 0.0,
                "positionsByStrategy": {},
                "dailyLossPercent": 0.0,
                "drawdownPercent": 0.0,
                "reconciliationMatched": True,
            },
        ), patch.object(
            service,
            "evaluate_demo_runtime_guard",
            return_value=SimpleNamespace(pauseRequired=False, reasonCodes=()),
        ), patch.object(
            service,
            "get_demo_strategy_runtime_settings",
            return_value={"maxConcurrentSymbols": 1},
            create=True,
        ), patch.object(
            service,
            "arbitrate_demo_signals",
            return_value=DemoArbitrationResult((), ()),
        ) as arbitrate:
            service.run_evolution_demo_cycle({"demoReleaseId": "release-1"})

        self.assertEqual(arbitrate.call_args.kwargs["maxPositions"], 1)
        save_scan.assert_called_once()
        self.assertEqual(save_scan.call_args.args[0], "strategy-1")

    def test_status_preserves_override_mode_and_dynamic_market_policy(self) -> None:
        contract = {
            "demoReleaseId": "release-override",
            "strategyCandidateId": "strategy-1",
            "status": "demo_eligible",
            "contractHash": "contract-hash",
            "releaseMode": "experimental_override",
            "livePromotionAllowed": False,
            "strategy": {
                "marketDefinition": {
                    "universePolicy": {
                        "mode": "okx_usdt_linear_perpetual_full_market"
                    }
                }
            },
        }

        class FakeOutcomeStore:
            def list_outcomes(self) -> list[object]:
                return []

            def close(self) -> None:
                return None

        with tempfile.TemporaryDirectory() as directory, patch.object(
            service, "STORE_PATH", Path(directory) / "demo.sqlite"
        ), patch.object(
            service, "RISK_PROFILE_STORE_PATH", Path(directory) / "risk.sqlite"
        ), patch.object(
            service, "discover_demo_contracts", return_value=([contract], [])
        ), patch.object(
            service, "ExecutionOutcomeStore", return_value=FakeOutcomeStore()
        ), patch.dict(os.environ, {}, clear=True):
            status = service.build_evolution_demo_status()

        projected = status["contracts"][0]
        self.assertEqual(projected["releaseMode"], "experimental_override")
        self.assertFalse(projected["livePromotionAllowed"])
        self.assertEqual(
            projected["marketDefinition"]["universePolicy"]["mode"],
            "okx_usdt_linear_perpetual_full_market",
        )


if __name__ == "__main__":
    unittest.main()
