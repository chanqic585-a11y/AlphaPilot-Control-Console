from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alphapilot_control_console.demo_instrument_universe import (
    DemoUniversePolicy,
    build_demo_instrument_universe,
    load_or_refresh_demo_instrument_universe,
)
from alphapilot_control_console.demo_instrument_universe_store import DemoInstrumentUniverseStore


NOW = datetime(2026, 7, 15, 0, 0, tzinfo=UTC)


def public_universe() -> dict:
    return {
        "screeningPool": [
            {"instId": "BTC-USDT-SWAP", "quoteVolumeProxy": 900.0, "spreadPct": 0.0001},
            {"instId": "ETH-USDT-SWAP", "quoteVolumeProxy": 800.0, "spreadPct": 0.0002},
            {"instId": "SOL-USDT-SWAP", "quoteVolumeProxy": 700.0, "spreadPct": 0.0003},
        ],
        "liquidityEligibleCount": 3,
        "rejections": [
            {"instId": "THIN-USDT-SWAP", "reason": "spread_too_wide"},
        ],
        "generatedAt": NOW.isoformat(),
    }


def private_response() -> dict:
    return {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT-SWAP",
                "instType": "SWAP",
                "baseCcy": "BTC",
                "quoteCcy": "USDT",
                "settleCcy": "USDT",
                "state": "live",
                "minSz": "0.01",
                "lotSz": "0.01",
                "tickSz": "0.1",
                "ctVal": "0.01",
            },
            {
                "instId": "ETH-USDT-SWAP",
                "instType": "SWAP",
                "baseCcy": "ETH",
                "quoteCcy": "USDT",
                "settleCcy": "USDT",
                "state": "suspend",
            },
            {
                "instId": "BTC-USDT-SWAP",
                "instType": "SWAP",
                "baseCcy": "BTC",
                "quoteCcy": "USDT",
                "settleCcy": "USDT",
                "state": "live",
            },
            {"instId": "MALFORMED-USDT-SWAP", "instType": "SWAP"},
        ],
    }


class DemoInstrumentUniverseTests(unittest.TestCase):
    def test_builds_exact_stable_intersection_and_exclusion_counts(self) -> None:
        result = build_demo_instrument_universe(
            publicUniverse=public_universe(),
            accountInstrumentsResponse=private_response(),
            policy=DemoUniversePolicy(environment="demo"),
            now=NOW,
        )

        self.assertEqual(result["status"], "usable")
        self.assertEqual(result["environment"], "demo")
        self.assertEqual(result["publicUniverseCount"], 3)
        self.assertEqual(result["demoAccountInstrumentCount"], 2)
        self.assertEqual(result["intersectionCount"], 1)
        self.assertEqual(result["liquidityEligibleCount"], 1)
        self.assertEqual(result["eligibleInstrumentIds"], ["BTC-USDT-SWAP"])
        self.assertEqual(result["instrumentConstraints"]["BTC-USDT-SWAP"]["minSz"], "0.01")
        self.assertEqual(result["excludedNotInDemoAccount"], 1)
        self.assertEqual(result["excludedUnavailableState"], 1)
        self.assertEqual(result["excludedDataMissing"], 1)
        self.assertEqual(result["excludedLiquidity"], 1)
        self.assertFalse(result["stale"])

    def test_fails_closed_for_invalid_private_payloads_and_environment(self) -> None:
        invalid_responses = (
            {"code": "50110", "data": []},
            {"code": "0", "data": []},
            {"code": "0", "data": "bad"},
        )
        for response in invalid_responses:
            with self.subTest(response=response):
                result = build_demo_instrument_universe(
                    publicUniverse=public_universe(),
                    accountInstrumentsResponse=response,
                    policy=DemoUniversePolicy(environment="demo"),
                    now=NOW,
                )
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["eligibleInstrumentIds"], [])
                self.assertTrue(result["blockers"])

        with self.assertRaises(ValueError):
            DemoUniversePolicy(environment="live")  # type: ignore[arg-type]

    def test_cache_persists_only_sanitized_projection_and_expires(self) -> None:
        result = build_demo_instrument_universe(
            publicUniverse=public_universe(),
            accountInstrumentsResponse=private_response(),
            policy=DemoUniversePolicy(environment="demo", cacheTtlSeconds=300),
            now=NOW,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "universe.sqlite"
            store = DemoInstrumentUniverseStore(path)
            store.save(result)
            cached = store.load_latest(environment="demo", now=NOW + timedelta(seconds=299))
            expired = store.load_latest(environment="demo", now=NOW + timedelta(seconds=301))
            store.close()

            self.assertIsNotNone(cached)
            self.assertIsNone(expired)
            connection = sqlite3.connect(path)
            raw = connection.execute("SELECT projectionJson FROM DemoInstrumentUniverseCache").fetchone()[0]
            connection.close()

        payload = json.loads(raw)
        self.assertNotIn("accountInstrumentsResponse", payload)
        self.assertNotIn("secret", raw.lower())
        self.assertNotIn("passphrase", raw.lower())
        self.assertEqual(payload["eligibleInstrumentIds"], ["BTC-USDT-SWAP"])

    def test_loader_uses_fresh_cache_and_fails_closed_when_refresh_is_unavailable(self) -> None:
        class Client:
            calls = 0

            def get_account_instruments(self, _kind: str) -> dict:
                self.calls += 1
                if self.calls > 1:
                    raise RuntimeError("credentials unavailable")
                return private_response()

        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "universe.sqlite"
            client = Client()
            first = load_or_refresh_demo_instrument_universe(
                client,
                fresh=True,
                publicUniverseLoader=public_universe,
                storePath=store_path,
                now=NOW,
            )
            cached = load_or_refresh_demo_instrument_universe(
                client,
                fresh=False,
                publicUniverseLoader=lambda: (_ for _ in ()).throw(AssertionError("cache should be used")),
                storePath=store_path,
                now=NOW + timedelta(seconds=10),
            )
            blocked = load_or_refresh_demo_instrument_universe(
                client,
                fresh=True,
                publicUniverseLoader=public_universe,
                storePath=store_path,
                now=NOW + timedelta(seconds=20),
            )

        self.assertEqual(first["status"], "usable")
        self.assertTrue(cached["cached"])
        self.assertEqual(blocked["status"], "blocked")
        self.assertIn("demo_account_instruments_unavailable", blocked["blockers"])


if __name__ == "__main__":
    unittest.main()
