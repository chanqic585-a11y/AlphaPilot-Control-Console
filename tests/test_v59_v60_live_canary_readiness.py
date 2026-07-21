from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class V59V60LiveCanaryReadinessBuilderTests(unittest.TestCase):
    def test_builder_runs_from_repository_root_and_emits_blocked_evidence(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            profile = {
                "allocatedCapitalUSDT": 1000.0,
                "maximumAcceptedLossUSDT": 1000.0,
                "riskPerTradePercent": 0.25,
                "riskPerTradeUSDT": 2.5,
                "maximumPortfolioOpenRiskPercent": 1.0,
                "maximumPortfolioOpenRiskUSDT": 10.0,
                "maximumConcurrentPositions": 1,
                "maximumInstrumentRisk": 0.5,
                "maximumLeverage": 1,
                "marginMode": "isolated",
                "dailyLossLimit": 10.0,
                "programLossLimit": 25.0,
                "hardKillLossLimit": 25.0,
                "scanTopN": 200,
            }
            source = {
                "releaseId": "demo-release",
                "releaseHash": "demo-hash",
                "riskOverlayHash": "demo-risk",
                "componentIds": ["candidate-a"],
            }
            smoke = {
                "status": "completed_canceled_and_reconciled",
                "contractHash": "smoke-hash",
                "orderAttemptCount": 1,
                "cancelConfirmed": True,
                "finalOpenPositionCount": 0,
                "finalOpenOrderCount": 0,
                "finalReconciliationMatched": True,
                "rawCredentialsPersisted": False,
                "privateAccountValuesPersisted": False,
                "withdrawAllowed": False,
            }
            observer = {
                "sidecarBindingHash": "observer-hash",
                "modelHash": "model-hash",
                "modelPolicyHash": "model-policy-hash",
                "releaseHash": "demo-hash",
                "releaseId": "demo-release",
            }
            readiness = {
                "schemaVersion": "adaptive_learning_live_readiness_v1",
                "passed": False,
                "status": "blocked_not_ready",
                "modelMode": "observer",
                "blockers": ["adaptive_evidence_not_ready:qlibCampaignReady"],
            }
            inputs = {
                "profile": profile,
                "source": source,
                "smoke": smoke,
                "observer": observer,
                "readiness": readiness,
            }
            paths = {}
            for name, payload in inputs.items():
                paths[name] = temp / f"{name}.json"
                paths[name].write_text(json.dumps(payload), encoding="utf-8")
            output = temp / "output"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "build_v59_v60_live_canary_readiness.py"),
                    "--profile",
                    str(paths["profile"]),
                    "--source-demo-release",
                    str(paths["source"]),
                    "--smoke-result",
                    str(paths["smoke"]),
                    "--observer-binding",
                    str(paths["observer"]),
                    "--adaptive-readiness",
                    str(paths["readiness"]),
                    "--output",
                    str(output),
                    "--generated-at",
                    "2026-07-21T07:00:00Z",
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env={**os.environ, "PYTHONUTF8": "1"},
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            status = json.loads(completed.stdout)
            self.assertEqual(status["status"], "blocked_waiting_exact_live_release_approval")
            release = json.loads((output / "experimental_live_release.json").read_text(encoding="utf-8"))
            self.assertFalse(release["adaptiveLearningReadinessPassed"])
            self.assertFalse(release["executionBoundary"]["withdrawAllowed"])
            self.assertTrue((output / "artifact_manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
