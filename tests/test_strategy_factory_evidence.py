from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_factory_evidence import (
    project_strategy_factory_execution_evidence,
)


class StrategyFactoryEvidenceTests(unittest.TestCase):
    def test_projects_complete_formal_chain_counts_without_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            campaign_id = "campaign-a"
            campaign_root = root / campaign_id
            campaign_root.mkdir()
            (campaign_root / "campaign_summary.json").write_text(
                json.dumps(
                    {
                        "developmentReplayStatus": "completed",
                        "trialCount": 3,
                        "formalJobCount": 1,
                        "formalClaimCount": 1,
                        "formalAttemptCount": 1,
                        "formalResultCount": 1,
                        "resultReadCount": 1,
                    }
                ),
                encoding="utf-8",
            )

            result = project_strategy_factory_execution_evidence(
                output_root=root,
                campaign_id=campaign_id,
                config={"candidateIds": ["candidate-a"]},
                receipt={},
                created_at="2026-07-23T00:00:00+00:00",
                started_at="2026-07-23T00:00:01+00:00",
                updated_at="2026-07-23T00:00:02+00:00",
                completed_at="2026-07-23T00:00:03+00:00",
            )

            self.assertEqual(result["formal"]["formalJobCount"], 1)
            self.assertEqual(result["formal"]["formalClaimCount"], 1)
            self.assertEqual(result["formal"]["formalAttemptCount"], 1)
            self.assertEqual(result["formal"]["formalResultCount"], 1)
            self.assertEqual(result["formal"]["resultReadCount"], 1)
            self.assertEqual(result["formal"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
