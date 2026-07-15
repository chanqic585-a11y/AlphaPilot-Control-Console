from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.backtest_screening_projection import build_backtest_screening_projection


class BacktestScreeningProjectionTests(unittest.TestCase):
    def test_projection_is_read_only_hash_verified_and_accepts_zero_formal_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = root / "reports" / "backtest_screening" / "campaign-1"
            campaign.mkdir(parents=True)
            summary = {"campaignId": "campaign-1", "formalPassCount": 0, "candidateCount": 6}
            raw = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode("utf-8")
            (campaign / "campaign_summary.json").write_bytes(raw)
            manifest = {
                "artifacts": [{"path": "campaign_summary.json", "sha256": hashlib.sha256(raw).hexdigest()}]
            }
            (campaign / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            projection = build_backtest_screening_projection("campaign-1", quant_root=root)

            self.assertEqual(projection["formalPassCount"], 0)
            self.assertEqual(projection["releaseCount"], 0)
            self.assertTrue(projection["hashesVerified"])
            with self.assertRaises(ValueError):
                build_backtest_screening_projection("../escape", quant_root=root)


if __name__ == "__main__":
    unittest.main()
