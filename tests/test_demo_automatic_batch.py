from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import alphapilot_control_console.evolution_demo_service as service
from alphapilot_control_console.demo_execution_store import DemoExecutionRecord


NOW = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)


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
            "maxLeverage": 5,
            "defaultMaxLeverage": 5,
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
        "entryPrice": 100.0,
        "stopLossPrice": 98.0,
        "takeProfitPrice": 104.5,
        "signalTime": NOW.isoformat(),
        "notionalUsdt": 50.0,
        "leverage": 1,
        "tdMode": "isolated",
        "ordType": "market",
        "sz": "1",
    }


def close_event() -> SimpleNamespace:
    return SimpleNamespace(
        sequenceId="1h:1783900800000",
        timeframe="1h",
        receivedAt=NOW.isoformat(),
    )


class FakeFrozenSnapshot:
    def __init__(self, quotes: dict[str, dict] | None = None) -> None:
        self.quotes = quotes or {}

    def load_universe(self, _limit: int) -> dict:
        return {"screeningPool": []}

    def load_snapshot(self, instrument: str, timeframe: str, _limit: int) -> dict:
        return {"ok": True, "instId": instrument, "timeframe": timeframe}

    def load_metadata(self, instrument: str) -> dict:
        return {"ok": True, "instId": instrument}

    def quote(self, instrument: str) -> dict:
        return dict(self.quotes.get(instrument) or {})


class FakeMarketRuntime:
    def __init__(self) -> None:
        self.freeze_calls: list[str] = []
        self.frozen = FakeFrozenSnapshot()

    def status(self) -> dict:
        return {"warm": True, "source": "fake_prewarmed_runtime"}

    def freeze_for_timeframe(self, timeframe: str, **_kwargs: object) -> FakeFrozenSnapshot:
        self.freeze_calls.append(timeframe)
        return self.frozen

    def quote(self, instrument: str) -> dict:
        return self.frozen.quote(instrument)


class FakeAccountClient:
    def __init__(self, instruments: set[str]) -> None:
        self.instruments = set(instruments)
        self.leverage_calls: list[dict] = []

    def get_account_instruments(self, instrumentType: str = "SWAP") -> dict:
        self.instrumentType = instrumentType
        return {
            "code": "0",
            "data": [
                {"instId": instrument, "state": "live"}
                for instrument in sorted(self.instruments)
            ],
        }

    def set_leverage(
        self,
        *,
        instrumentId: str,
        leverage: int,
        marginMode: str,
        positionSide: str | None = None,
    ) -> dict:
        self.leverage_calls.append(
            {
                "instrumentId": instrumentId,
                "leverage": leverage,
                "marginMode": marginMode,
                "positionSide": positionSide,
            }
        )
        return {"code": "0", "data": [{"lever": str(leverage), "instId": instrumentId}]}


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
        self.market_runtime = FakeMarketRuntime()
        self.account_client = FakeAccountClient({"BTC-USDT-SWAP"})

    def _patches(self, scans: dict[str, dict]):
        return (
            patch.object(service, "build_evolution_demo_status", return_value=self.ready),
            patch.object(service, "discover_demo_contracts", return_value=(self.contracts, [])),
            patch.object(
                service,
                "scan_immutable_demo_release",
                side_effect=lambda row, **_kwargs: scans[row["demoReleaseId"]],
            ),
            patch.object(service, "save_demo_release_scan", return_value={}),
            patch.object(service, "DemoExecutionStore", return_value=self.store),
            patch.object(service, "DemoExecutionEngine", FakeEngine),
            patch.object(service, "OkxDemoClient", return_value=self.account_client),
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
                return_value={"maxConcurrentSymbols": 1, "leverage": 3},
            ),
            patch.object(
                service,
                "get_demo_market_runtime",
                return_value=self.market_runtime,
                create=True,
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
        self.market_runtime.frozen.quotes["BTC-USDT-SWAP"] = {
            "bidPrice": 100.0,
            "askPrice": 100.01,
            "receivedAt": NOW.isoformat(),
            "spreadPct": 0.0001,
            "liquidityPassed": True,
        }
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11], patch.object(service, "_utc_now", return_value=NOW + timedelta(seconds=4), create=True):
            result = service.run_evolution_demo_batch_cycle(
                ["release-a", "release-b"],
                close_event=close_event(),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["scannedReleaseCount"], 2)
        self.assertEqual(result["matchedSignalCount"], 2)
        self.assertEqual(result["createdOrderCount"], 1)
        self.assertEqual(result["orderAttemptCount"], 1)
        self.assertEqual(result["orderOutcomes"], [{"status": "submitted", "exchangeCode": "0"}])
        self.assertEqual(FakeEngine.executed, [("release-a", "signal-a")])
        self.assertEqual(
            self.account_client.leverage_calls,
            [{
                "instrumentId": "BTC-USDT-SWAP",
                "leverage": 3,
                "marginMode": "isolated",
                "positionSide": None,
            }],
        )
        reasons = [row.get("reason") for row in result["rejectedSignals"]]
        self.assertIn("duplicate_symbol_signal", reasons)

    def test_batch_filters_public_matches_not_available_to_demo_account(self) -> None:
        unavailable = {
            **signal("release-a", "strategy-a", "signal-unavailable", 95),
            "instId": "TRUMP-USDT-SWAP",
        }
        supported = signal("release-b", "strategy-b", "signal-supported", 90)
        scans = {
            "release-a": {"signals": [unavailable], "rejections": [], "blockers": []},
            "release-b": {"signals": [supported], "rejections": [], "blockers": []},
        }
        self.market_runtime.frozen.quotes["BTC-USDT-SWAP"] = {
            "bidPrice": 100.0,
            "askPrice": 100.01,
            "receivedAt": NOW.isoformat(),
            "spreadPct": 0.0001,
            "liquidityPassed": True,
        }
        patches = self._patches(scans)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11], patch.object(service, "_utc_now", return_value=NOW + timedelta(seconds=4), create=True):
            result = service.run_evolution_demo_batch_cycle(
                ["release-a", "release-b"],
                close_event=close_event(),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["matchedSignalCount"], 2)
        self.assertEqual(result["tradableSignalCount"], 1)
        self.assertEqual(result["createdOrderCount"], 1)
        self.assertEqual(FakeEngine.executed, [("release-b", "signal-supported")])
        rejected = [row for row in result["rejectedSignals"] if row.get("reason") == "demo_instrument_unavailable"]
        self.assertEqual([row["instId"] for row in rejected], ["TRUMP-USDT-SWAP"])

    def test_51001_race_rejection_does_not_count_exposure_or_stop_later_signal(self) -> None:
        class RaceAwareEngine(FakeEngine):
            def execute(self, *, contract: dict, signal: dict, portfolio: dict) -> DemoExecutionRecord:
                if signal["instId"] == "TRUMP-USDT-SWAP":
                    self.executed.append((contract["demoReleaseId"], signal["candidateId"]))
                    return DemoExecutionRecord(
                        recordId="record-rejected",
                        idempotencyKey="idempotency-rejected",
                        demoReleaseId=contract["demoReleaseId"],
                        status="rejected",
                        signal=dict(signal),
                        orderPayload={},
                        exchangeOrderId=None,
                        exchangeResponse={"code": "1", "data": [{"sCode": "51001"}]},
                        createdAt="2026-07-12T00:00:00+00:00",
                        updatedAt="2026-07-12T00:00:00+00:00",
                    )
                return super().execute(contract=contract, signal=signal, portfolio=portfolio)

        first = {
            **signal("release-a", "strategy-a", "signal-race", 95),
            "instId": "TRUMP-USDT-SWAP",
            "correlationGroup": "TRUMP",
        }
        second = {
            **signal("release-b", "strategy-b", "signal-supported", 90),
            "instId": "ETH-USDT-SWAP",
            "correlationGroup": "ETH",
        }
        scans = {
            "release-a": {"signals": [first], "rejections": [], "blockers": []},
            "release-b": {"signals": [second], "rejections": [], "blockers": []},
        }
        self.account_client.instruments = {"TRUMP-USDT-SWAP", "ETH-USDT-SWAP"}
        for instrument in self.account_client.instruments:
            self.market_runtime.frozen.quotes[instrument] = {
                "bidPrice": 100.0,
                "askPrice": 100.01,
                "receivedAt": NOW.isoformat(),
                "spreadPct": 0.0001,
                "liquidityPassed": True,
            }
        patches = list(self._patches(scans))
        patches[5] = patch.object(service, "DemoExecutionEngine", RaceAwareEngine)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11], patch.object(service, "_utc_now", return_value=NOW + timedelta(seconds=4), create=True):
            result = service.run_evolution_demo_batch_cycle(
                ["release-a", "release-b"],
                close_event=close_event(),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["orderAttemptCount"], 2)
        self.assertEqual(result["createdOrderCount"], 1)
        self.assertEqual([row["status"] for row in result["orderOutcomes"]], ["rejected", "submitted"])
        reasons = [row.get("reason") for row in result["rejectedSignals"]]
        self.assertIn("demo_instrument_unavailable", reasons)

    def test_no_signal_is_a_successful_evaluation_not_a_runtime_failure(self) -> None:
        scans = {
            row["demoReleaseId"]: {"signals": [], "rejections": [], "blockers": []}
            for row in self.contracts
        }
        patches = self._patches(scans)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11]:
            result = service.run_evolution_demo_batch_cycle(
                ["release-a", "release-b"],
                close_event=close_event(),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["createdOrderCount"], 0)
        self.assertEqual(result["matchedSignalCount"], 0)
        self.assertEqual(FakeEngine.executed, [])

    def test_five_releases_share_one_frozen_timeframe_snapshot(self) -> None:
        self.contracts = [contract(f"release-{index}", f"strategy-{index}") for index in range(5)]
        scans = {
            row["demoReleaseId"]: {"signals": [], "rejections": [], "blockers": []}
            for row in self.contracts
        }
        scanner_calls: list[dict] = []
        patches = self._patches(scans)
        patches = list(patches)
        patches[2] = patch.object(
            service,
            "scan_immutable_demo_release",
            side_effect=lambda row, **kwargs: scanner_calls.append(kwargs) or scans[row["demoReleaseId"]],
        )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11]:
            result = service.run_evolution_demo_batch_cycle(
                [row["demoReleaseId"] for row in self.contracts],
                close_event=close_event(),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(self.market_runtime.freeze_calls, ["1h"])
        self.assertEqual(len(scanner_calls), 5)
        self.assertTrue(all(call["snapshot_loader"].__self__ is self.market_runtime.frozen for call in scanner_calls))
        self.assertEqual(result["marketRuntimeStatus"]["source"], "fake_prewarmed_runtime")

    def test_latency_policy_allows_target_and_valid_late_but_rejects_drift_and_expiry(self) -> None:
        scans = {
            "release-a": {
                "signals": [signal("release-a", "strategy-a", "signal-a", 90)],
                "rejections": [],
                "blockers": [],
            },
            "release-b": {"signals": [], "rejections": [], "blockers": []},
        }
        cases = (
            (4, 100.02, 1, "on_target"),
            (12, 100.02, 1, "conditional"),
            (12, 100.30, 0, "conditional_price_drift_exceeded"),
            (31, 100.02, 0, "signal_expired"),
        )
        for elapsed, ask, expected_orders, expected_result in cases:
            with self.subTest(elapsed=elapsed, ask=ask):
                FakeEngine.executed = []
                self.market_runtime.frozen.quotes["BTC-USDT-SWAP"] = {
                    "bidPrice": ask - 0.01,
                    "askPrice": ask,
                    "receivedAt": (NOW + timedelta(seconds=max(0, elapsed - 0.5))).isoformat(),
                    "spreadPct": 0.0001,
                    "liquidityPassed": True,
                }
                patches = self._patches(scans)
                with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11], patch.object(service, "_utc_now", return_value=NOW + timedelta(seconds=elapsed), create=True):
                    result = service.run_evolution_demo_batch_cycle(
                        ["release-a", "release-b"],
                        close_event=close_event(),
                    )

                self.assertEqual(result["createdOrderCount"], expected_orders)
                if expected_orders:
                    self.assertEqual(result["latencyMetrics"]["selected"][0]["latencyClass"], expected_result)
                else:
                    reasons = [row.get("reason") for row in result["rejectedSignals"]]
                    self.assertIn(expected_result, reasons)


if __name__ == "__main__":
    unittest.main()
