from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.v55_demo_operation_evidence import (
    generate_v55_demo_operation_evidence,
)


class V55DemoOperationEvidenceTests(unittest.TestCase):
    def test_generates_engineering_only_latency_and_pre_arm_scan_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            result = generate_v55_demo_operation_evidence(
                root,
                generated_at="2026-07-21T00:00:00Z",
                release_identity={
                    "releaseId": "release-fixture",
                    "releaseHash": "release-hash-fixture",
                    "riskOverlayHash": "risk-hash-fixture",
                },
            )

            self.assertEqual(result["status"], "complete_pre_arm")
            expected = {
                "execution_latency_profile.json",
                "latency_benchmark.json",
                "latency_ledger.jsonl",
                "stale_signal_audit.json",
                "first_scan_audit.json",
                "artifact_manifest.json",
            }
            self.assertEqual({path.name for path in root.iterdir()}, expected)

            benchmark = json.loads((root / "latency_benchmark.json").read_text(encoding="utf-8"))
            self.assertTrue(benchmark["engineeringOnly"])
            self.assertFalse(benchmark["strategyEvidenceEligible"])
            self.assertEqual(benchmark["status"], "passed")

            stale = json.loads((root / "stale_signal_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(stale["staleRejectedCount"], 1)
            self.assertEqual(stale["criticalRejectedCount"], 1)

            first_scan = json.loads((root / "first_scan_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(first_scan["status"], "not_run_pre_arm")
            self.assertEqual(first_scan["strategyOrderCount"], 0)
            self.assertEqual(first_scan["releaseId"], "release-fixture")

            manifest = json.loads((root / "artifact_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["fileCount"], 5)
            self.assertTrue(all(row["sha256"] for row in manifest["files"]))


if __name__ == "__main__":
    unittest.main()
