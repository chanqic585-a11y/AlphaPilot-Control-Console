from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_lab_projection import build_strategy_lab_projection


class StrategyLabProjectionTests(unittest.TestCase):
    def test_projection_joins_vibe_sources_factor_lab_and_bounded_campaigns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_root = root / "research" / "external_capabilities" / "vibe_trading"
            integration_root = root / "reports" / "integration" / "v37g_v37h"
            campaign_root = root / "reports" / "strategy_acquisition" / "v37i_v37j"
            source_root.mkdir(parents=True)
            integration_root.mkdir(parents=True)
            campaign_root.mkdir(parents=True)

            self._write_json(source_root / "source_manifest.json", {
                "repository": "HKUDS/Vibe-Trading",
                "commit": "7d42de944466e1a1f12f0df3933624fe665dee3c",
                "license": "MIT",
                "runtimeDependency": False,
                "paths": [{"path": "agent/source.py", "blobSha": "abc"}],
            })
            self._write_json(source_root / "component_adoption_map.json", {
                "adoptNow": [{"component": "alpha-compare"}],
                "defer": [{"component": "decay-monitoring"}],
                "reject": ["whole-repository-merge"],
            })
            self._write_json(integration_root / "source_inventory.json", [{
                "artifactId": "source-1",
                "name": "Pinned source",
                "artifactType": "strategy_reference",
                "status": "mechanism_extracted",
                "familyId": "family-a",
            }])
            self._write_json(integration_root / "factor_registry.json", [{
                "factorId": "funding",
                "name": "Funding persistence",
                "theme": "funding",
                "pointInTimeReady": True,
            }])
            self._write_csv(integration_root / "source_equivalence_matrix.csv", [
                {"candidateId": "candidate-a", "classification": "mechanism_related"},
            ])
            self._write_csv(integration_root / "artifact_similarity_summary.csv", [
                {"leftArtifactId": "a", "rightArtifactId": "b", "classification": "different"},
            ])
            self._write_csv(integration_root / "factor_bench_matrix.csv", [
                {"factorId": "funding", "status": "research_only"},
            ])
            self._write_json(campaign_root / "campaign_summary.json", {
                "status": "completed_zero_qualified_candidates",
                "campaignCount": 2,
                "candidateCount": 5,
                "formalCandidateCount": 0,
            })
            self._write_json(campaign_root / "candidate_inventory.json", {
                "candidates": [{
                    "candidate_id": "candidate-a",
                    "family_id": "family-a",
                    "status": "prefilter_failed",
                    "source_path": "source.json",
                }],
                "lockedOosReadCount": 0,
            })
            self._write_json(campaign_root / "experiment_budget.json", {
                "campaignsUsed": 2,
                "familiesUsed": 4,
                "candidatesRegistered": 5,
            })
            self._write_json(campaign_root / "failure_attribution.json", {
                "failureCount": 1,
                "byReason": {"economic_prefilter_failed": 1},
            })
            self._write_json(campaign_root / "formal_route.json", {
                "formalCandidateCount": 0,
                "releaseCount": 0,
                "demoArm": False,
            })

            result = build_strategy_lab_projection(root)

            self.assertTrue(result["readOnly"])
            self.assertEqual(result["sourceRegistry"]["repository"], "HKUDS/Vibe-Trading")
            self.assertEqual(result["sourceRegistry"]["sourceCount"], 1)
            self.assertEqual(result["summary"]["factorCount"], 1)
            self.assertEqual(result["summary"]["candidateCount"], 1)
            self.assertEqual(result["summary"]["formalCandidateCount"], 0)
            self.assertEqual(result["route"]["status"], "zero_qualified_candidates")
            self.assertFalse(result["route"]["demoArm"])
            self.assertEqual(result["decayState"]["status"], "inactive_insufficient_real_evidence")
            self.assertFalse(result["capabilities"]["canMutateFrozenCandidate"])
            self.assertFalse(result["capabilities"]["canCreateOrder"])

    def test_missing_evidence_returns_blocked_read_only_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = build_strategy_lab_projection(Path(temporary_directory))

        self.assertEqual(result["status"], "blocked_missing_evidence")
        self.assertTrue(result["readOnly"])
        self.assertGreater(len(result["missingEvidence"]), 0)
        self.assertEqual(result["summary"]["candidateCount"], 0)

    def test_projection_exposes_latest_mechanism_campaign_and_formal_gate_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            research = (
                root
                / "reports"
                / "mechanism_breakthrough"
                / "v41_v45_fixture"
                / "research"
            )
            research.mkdir(parents=True)
            self._write_json(research / "campaign_summary.json", {
                "campaignId": "campaign-v41-fixture",
                "status": "completed_zero_qualified_candidates",
                "candidateCount": 4,
                "prefilterSurvivorCount": 0,
                "formalCandidateCount": 0,
                "formalRunCount": 0,
                "releaseCount": 0,
                "lockedOosReadCount": 0,
            })
            (research / "formal_gate_matrix.csv").write_text(
                "candidateId,gateName,actual,operator,required,passed,status\n",
                encoding="utf-8",
            )

            result = build_strategy_lab_projection(root)

            mechanism = result["mechanismCampaign"]
            self.assertEqual(mechanism["campaignId"], "campaign-v41-fixture")
            self.assertEqual(mechanism["status"], "completed_zero_qualified_candidates")
            self.assertEqual(mechanism["formalCandidateCount"], 0)
            self.assertEqual(mechanism["formalGateStatus"], "not_run_zero_prefilter_survivors")
            self.assertEqual(result["formalGateMatrix"], [])

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload), encoding="utf-8")

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
