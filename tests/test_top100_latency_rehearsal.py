from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.top100_latency_rehearsal import run_top100_latency_rehearsal


class Top100LatencyRehearsalTests(unittest.TestCase):
    def test_rehearsal_scans_top100_and_never_calls_private_or_order_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "rehearsal.json"
            result = run_top100_latency_rehearsal(
                iterations=2,
                release_count=2,
                report_path=report_path,
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["version"], "V13.27.9")
            self.assertEqual(result["deepScreeningLimit"], 100)
            self.assertEqual(result["privateCallCount"], 0)
            self.assertEqual(result["orderCallCount"], 0)
            self.assertEqual(result["iterations"], 2)
            self.assertGreater(result["matchedSignalCount"], 0)
            self.assertGreaterEqual(result["latencyMs"]["p95"], 0)
            self.assertTrue(report_path.exists())


if __name__ == "__main__":
    unittest.main()
