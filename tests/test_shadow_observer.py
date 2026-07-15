from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.shadow_observation_store import ShadowObservationStore
from alphapilot_control_console.shadow_observer import observe_release_scan


class ShadowObserverTests(unittest.TestCase):
    def test_scan_is_reduced_to_signal_diagnostics_without_trade_payload(self) -> None:
        contract = {
            "demoReleaseId": "release-1",
            "strategyCandidateId": "strategy-1",
            "releaseContentHash": "definition-hash",
            "strategy": {
                "familyKey": "family-1",
                "marketDefinition": {"timeframe": "1h"},
                "forwardSignalPolicy": {"direction": "long"},
            },
        }
        scan = {
            "signals": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "entryPrice": 100.0,
                    "takeProfitPrice": 104.0,
                    "factorContext": {
                        "factors": {"rsi14": 55.0, "volumeRatio": 1.2},
                        "btcContext": {"regime": "bull"},
                    },
                }
            ],
            "rejections": [
                {
                    "instId": "ETH-USDT-SWAP",
                    "reason": "frozen_rules_not_matched",
                    "rules": [{"factorId": "rsi14", "value": 40.0}],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            store = ShadowObservationStore(Path(directory) / "shadow.sqlite")
            try:
                result = observe_release_scan(
                    contract,
                    scan,
                    observed_at="2026-07-15T00:00:00+00:00",
                    source_event_hash="event-hash",
                    demo_instrument_ids={"BTC-USDT-SWAP"},
                    store=store,
                )
                rows = store.query(release_id="release-1", limit=10)["rows"]
            finally:
                store.close()

        self.assertEqual(result["writtenCount"], 2)
        self.assertEqual({row["passOrReject"] for row in rows}, {"pass", "reject"})
        matched = next(row for row in rows if row["signalMatched"])
        self.assertEqual(matched["featureSnapshot"], {"rsi14": 55.0, "volumeRatio": 1.2})
        self.assertNotIn("entryPrice", matched["featureSnapshot"])
        self.assertNotIn("takeProfitPrice", matched["featureSnapshot"])
        self.assertEqual(matched["sourceDataHashes"]["sourceEventHash"], "event-hash")


if __name__ == "__main__":
    unittest.main()
