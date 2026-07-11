from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import alphapilot_control_console.usable_strategy_catalog as catalog


class UsableStrategyCatalogTests(unittest.TestCase):
    def test_low_frequency_catalog_restores_original_strategy_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "reports"
            reports.mkdir()
            factory_report = getattr(catalog, "LOW_FREQUENCY_FACTORY_REPORT", None)
            self.assertIsNotNone(factory_report, "low-frequency factory report is not loaded")
            (reports / catalog.LOW_FREQUENCY_TASK_PACK_REPORT).write_text(
                json.dumps(
                    {
                        "paperObservationTasks": [
                            {
                                "taskId": "task-108",
                                "strategyId": "legacy-108",
                                "candidateId": "lf_research_candidate_108",
                                "title": "1D 广谱低波突破 ATR2.0",
                                "family": "squeeze_breakout",
                                "timeframe": "1d",
                                "targetRewardRiskRatio": 2.0,
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (reports / factory_report).write_text(
                json.dumps(
                    {
                        "factory": {
                            "approvedCandidates": [
                                {
                                    "candidateId": "lf_research_candidate_108",
                                    "spec": {
                                        "atrMultiplier": 2.0,
                                        "minVolumeRatio": 1.1,
                                        "maxHoldBars": 16,
                                        "targetRewardRiskRatio": 2.0,
                                    },
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            (reports / catalog.SHORT_CYCLE_SELECTED_REPORT).write_text(
                json.dumps({"selectedCandidates": []}),
                encoding="utf-8",
            )

            row = catalog.build_usable_strategy_catalog(root)["strategies"][0]

        self.assertEqual(row["params"]["atrMultiplier"], 2.0)
        self.assertEqual(row["params"]["minVolumeRatio"], 1.1)
        self.assertEqual(row["params"]["targetRewardRiskRatio"], 2.0)
