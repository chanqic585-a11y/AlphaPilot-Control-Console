from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import alphapilot_control_console.evolution_demo_service as service


class EvolutionDemoServiceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
