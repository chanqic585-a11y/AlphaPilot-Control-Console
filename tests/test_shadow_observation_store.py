from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.shadow_observation_store import ShadowObservationStore


FORBIDDEN = (
    "order",
    "fill",
    "position",
    "capital",
    "equity",
    "pnl",
    "profit",
    "loss",
    "mfe",
    "mae",
    "return",
    "outcome",
    "targethit",
    "stophit",
    "closedtrade",
    "promotion",
)


def observation() -> dict:
    return {
        "releaseId": "release-1",
        "strategyId": "strategy-1",
        "strategyFamilyId": "family-1",
        "timestamp": "2026-07-15T00:00:00+00:00",
        "symbol": "BTC-USDT-SWAP",
        "direction": "long",
        "timeframe": "1h",
        "signalMatched": True,
        "passOrReject": "pass",
        "reasonZh": "冻结规则匹配",
        "featureSnapshot": {"rsi14": 54.2, "volumeRatio": 1.4},
        "marketRegime": "bull",
        "publicUniverseIncluded": True,
        "demoUniverseIncluded": True,
        "liquidityPassed": True,
        "dataQualityPassed": True,
        "riskGatePassed": None,
        "wouldAttemptDemoOrder": True,
        "sourceDataHashes": {
            "definitionHash": "definition-hash",
            "sourceEventHash": "source-event-hash",
        },
    }


class ShadowObservationStoreTests(unittest.TestCase):
    def test_schema_contains_no_performance_or_lifecycle_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shadow.sqlite"
            store = ShadowObservationStore(path)
            store.close()
            connection = sqlite3.connect(path)
            columns = [row[1] for row in connection.execute("PRAGMA table_info(ShadowObservations)")]
            connection.close()

        for column in columns:
            if column == "wouldAttemptDemoOrder":
                continue
            normalized = column.lower()
            self.assertFalse(any(fragment in normalized for fragment in FORBIDDEN), column)

    def test_append_is_idempotent_for_release_symbol_candle_and_definition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ShadowObservationStore(Path(directory) / "shadow.sqlite")
            try:
                first = store.append(observation())
                second = store.append(observation())
                result = store.query(release_id="release-1", limit=100)
            finally:
                store.close()

        self.assertEqual(first["shadowObservationId"], second["shadowObservationId"])
        self.assertEqual(result["summary"]["observationCount"], 1)
        self.assertEqual(result["summary"]["matchedCount"], 1)
        serialized = json.dumps(result, ensure_ascii=False).lower()
        for fragment in ("pnl", "profit", "loss", "mfe", "mae", "equity", "position"):
            self.assertNotIn(fragment, serialized)


if __name__ == "__main__":
    unittest.main()
