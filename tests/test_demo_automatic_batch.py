from __future__ import annotations

import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import alphapilot_control_console.evolution_demo_service as service
from alphapilot_control_console.demo_execution_store import DemoExecutionRecord


def contract(release_id: str, strategy_id: str) -> dict:
    return {
        "demoReleaseId": release_id,
        "strategyCandidateId": strategy_id,
        "strategy": {"marketDefinition": {"timeframe": "1h"}},
        "riskEnvelope": {
            "maxConcurrentPositions": 3,
            "maxPositionsPerStrategy": 1,
            "maxOpenRiskPercent": 1.0,
            "riskPerTradePercent": 0.25,
        },
    }


def signal(release_id: str, strategy_id: str, candidate_id: str, score: float) -> dict:
    return {
        "candidateId": candidate_id,
        "demoReleaseId": release_id,
        "strategyCandidateId": strategy_id,
        "strategyFamilyId": strategy_id,
        "instId": "BTC-USDT-SWAP",
        "side": "buy",
        "score": score,
        "riskPercent": 0.25,
        "dataFresh": True,
        "liquidityPassed": True,
        "correlationGroup": "BTC",
    }


class FakeStore:
    def __init__(self) -> None:
        self.paused = False

    def close(self) -> None:
        return None

    def get_runtime_flag(self, key: str, default: object = None) -> object:
        return self.paused if key == "paused" else default


class FakeEngine:
    executed: list[tuple[str, str]] = []

    def __init__(self, **_kwargs: object) -> None:
        pass

    def recover_open_records(self) -> list[DemoExecutionRecord]:
        return []

    def pause(self, _reason: str) -> None:
        return None

    def execute(self, *, contract: dict, signal: dict, portfolio: dict) -> DemoExecutionRecord:
        del portfolio
        self.executed.append((contract["demoReleaseId"], signal["candidateId"]))
        return DemoExecutionRecord(
            recordId="record-" + signal["candidateId"],
            idempotencyKey="idempotency-" + signal["candidateId"],
            demoReleaseId=contract["demoReleaseId"],
            status="submitted",
            signal=dict(signal),
            orderPayload={},
            exchangeOrderId="order-1",
            exchangeResponse={"code": "0"},
            createdAt="2026-07-12T00:00:00+00:00",
            updatedAt="2026-07-12T00:00:00+00:00",
        )


class DemoAutomaticBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeEngine.executed = []
        self.contracts = [contract("release-a", "strategy-a"), contract("release-b", "strategy-b")]
        self.store = FakeStore()
        self.ready = {"blockers": [], "summary": {"ready": True}}
        self.portfolio = {
            "availableEquityUsdt": 1000.0,
            "openPositionCount": 0,
            "openRiskPercent": 0.0,
            "positionsByStrategy": {},
            "positionsBySymbol": {},
            "openRiskByStrategy": {},
            "openRiskBySymbol": {},
            "openRiskByDirection": {},
            "openRiskByCorrelationGroup": {},
            "dailyLossPercent": 0.0,
            "drawdownPercent": 0.0,
            "reconciliationMatched": True,
        }

    def _patches(self, scans: dict[str, dict]):
        return (
            patch.object(service, "build_evolution_demo_status", return_value=self.ready),
            patch.object(service, "discover_demo_contracts", return_value=(self.contracts, [])),
            patch.object(
                service,
                "scan_immutable_demo_release",
                side_effect=lambda row: scans[row["demoReleaseId"]],
            ),
            patch.object(service, "save_demo_release_scan", return_value={}),
            patch.object(service, "DemoExecutionStore", return_value=self.store),
            patch.object(service, "DemoExecutionEngine", FakeEngine),
            patch.object(service, "OkxDemoClient", return_value=object()),
            patch.object(service, "load_okx_demo_credentials", return_value=object()),
            patch.object(service, "_portfolio_from_demo_account", return_value=dict(self.portfolio)),
            patch.object(
                service,
                "evaluate_demo_runtime_guard",
                return_value=SimpleNamespace(pauseRequired=False, reasonCodes=()),
            ),
            patch.object(
                service,
                "get_demo_strategy_runtime_settings",
                return_value={"maxConcurrentSymbols": 1},
            ),
        )

    def test_batch_scans_all_due_releases_and_arbitrates_before_ordering(self) -> None:
        scans = {
            "release-a": {
                "signals": [signal("release-a", "strategy-a", "signal-a", 90)],
                "rejections": [],
                "blockers": [],
            },
            "release-b": {
                "signals": [signal("release-b", "strategy-b", "signal-b", 80)],
                "rejections": [],
                "blockers": [],
            },
        }
        patches = self._patches(scans)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10]:
            result = service.run_evolution_demo_batch_cycle(["release-a", "release-b"])

        self.assertTrue(result["ok"])
        self.assertEqual(result["scannedReleaseCount"], 2)
        self.assertEqual(result["matchedSignalCount"], 2)
        self.assertEqual(result["createdOrderCount"], 1)
        self.assertEqual(FakeEngine.executed, [("release-a", "signal-a")])
        reasons = [row.get("reason") for row in result["rejectedSignals"]]
        self.assertIn("duplicate_symbol_signal", reasons)

    def test_no_signal_is_a_successful_evaluation_not_a_runtime_failure(self) -> None:
        scans = {
            row["demoReleaseId"]: {"signals": [], "rejections": [], "blockers": []}
            for row in self.contracts
        }
        patches = self._patches(scans)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10]:
            result = service.run_evolution_demo_batch_cycle(["release-a", "release-b"])

        self.assertTrue(result["ok"])
        self.assertEqual(result["createdOrderCount"], 0)
        self.assertEqual(result["matchedSignalCount"], 0)
        self.assertEqual(FakeEngine.executed, [])


if __name__ == "__main__":
    unittest.main()
