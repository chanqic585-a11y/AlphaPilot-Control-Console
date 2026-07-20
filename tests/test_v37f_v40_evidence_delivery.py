from __future__ import annotations

import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from alphapilot_control_console.v37f_v40_evidence_delivery import build_evidence_delivery


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V37FV40EvidenceDeliveryTests(unittest.TestCase):
    def test_builds_one_outer_zip_with_four_stage_zips_and_truthful_zero_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            quant = root / "quant"
            console = root / "console"
            docs = root / "docs"
            screenshots = root / "screenshots"
            output = root / "delivery"
            requirements = root / "requirements.md"
            requirements.write_text("# Delivery requirements\n", encoding="utf-8")

            v37f = quant / "reports" / "integration" / "v37f"
            _write_json(v37f / "integration_merge_receipt.json", {
                "allRequiredBranchesIntegrated": True,
                "historicalArtifactModificationCount": 0,
                "branchReceipts": [{
                    "branch": "feature/example",
                    "commit": "a" * 40,
                    "isAncestorOfIntegratedHead": True,
                    "sourceRef": "origin/feature/example",
                    "status": "integrated",
                }],
            })
            _write_json(v37f / "budget_reconciliation.json", {
                "budgetReset": False,
                "developmentTrialsUsed": 48,
                "formalRunsUsed": 8,
                "fullBacktestsUsed": 1,
                "remainingByAuthoritativePolicy": {"fullBacktests": {"value": 95}},
            })
            _write_json(v37f / "formal_gate_parity_audit.json", {
                "status": "passed",
                "singleSource": "FormalGateEvaluation",
                "foldGateUsesForbiddenOutcomesOnly": True,
            })
            _write_json(v37f / "v37e_gate_semantics_clarification_sidecar.json", {})
            _write_json(v37f / "artifact_manifest.json", {"artifacts": []})

            v37gh = quant / "reports" / "integration" / "v37g_v37h"
            _write_json(v37gh / "vibe_trading_source_manifest.json", {
                "repository": "HKUDS/Vibe-Trading",
                "commit": "7d42de944466e1a1f12f0df3933624fe665dee3c",
                "license": "MIT",
                "copiedCode": [],
                "cleanRoomRewrite": True,
                "runtimeDependency": False,
            })
            _write_json(v37gh / "vibe_component_adoption_map.json", {
                "adoptNow": ["a", "b"], "reject": ["c"], "defer": ["d"],
            })
            _write_json(v37gh / "source_inventory.json", [{"artifactId": "source-1"}])
            _write_json(v37gh / "mechanism_inventory.json", [{"artifactId": "mechanism-1"}])
            _write_json(v37gh / "factor_registry.json", [{"factorId": "factor-1", "formula": "x"}])
            _write_json(v37gh / "candidate_dedup_decision.json", [
                {"candidateId": "duplicate", "classification": "exact_duplicate"},
                {"candidateId": "independent", "classification": "independent"},
            ])
            _write_json(v37gh / "generated_candidate_sandbox_audit.json", {
                "boundaryClaim": "research_execution_guard_not_os_security_boundary",
            })
            _write_json(v37gh / "strategy_artifact_store_schema.json", {"migrationVersion": 8})
            _write_json(v37gh / "artifact_manifest.json", {"artifacts": []})

            v37ij = quant / "reports" / "strategy_acquisition" / "v37i_v37j"
            _write_json(v37ij / "campaign_summary.json", {
                "status": "completed_zero_qualified_candidates",
                "campaignCount": 2,
                "familyCount": 4,
                "candidateCount": 5,
                "prefilterSurvivorCount": 0,
                "formalCandidateCount": 0,
                "formalRunCount": 0,
                "lockedOosReadCount": 0,
                "releaseCount": 0,
                "demoArm": False,
                "orderCount": 0,
            })
            candidates = [{
                "campaign_id": "campaign-1",
                "candidate_id": "v37i_funding_carry_source_replication",
                "candidate_hash": "candidate-hash",
                "family_id": "funding",
                "mechanism": "funding carry",
                "parameter_trials": [{"threshold": 1}],
                "source_equivalence_class": "source_faithful_reproduction",
                "similarity_classification": "same_family_variant",
                "result": {"status": "prefilter_failed", "reasonCode": "economic_prefilter_failed"},
            }]
            _write_json(v37ij / "candidate_inventory.json", {"candidates": candidates, "candidateCount": 1})
            _write_json(v37ij / "campaign_inventory.json", {"campaigns": [], "campaignCount": 2})
            _write_json(v37ij / "experiment_budget.json", {
                "developmentTrialsUsed": 12, "fullBacktestsUsed": 4,
                "fullBacktestsRemainingAfter": 91,
            })
            _write_json(v37ij / "failure_attribution.json", {
                "failures": [{"candidateId": candidates[0]["candidate_id"], "reasonCode": "economic_prefilter_failed"}],
            })
            _write_json(v37ij / "formal_route.json", {
                "status": "completed_zero_qualified_candidates",
                "formalCandidateCount": 0,
                "releaseCount": 0,
                "demoArm": False,
                "lockedOosReadCount": 0,
            })
            _write_json(v37ij / "development_data_audit.json", {"lockedOosReadCount": 0})
            _write_json(v37ij / "statistical_matrix.json", {"status": "not_run_no_prefilter_survivors"})
            (v37ij / "prefilter_matrix.csv").write_text("candidate_id,status\nexample,failed\n", encoding="utf-8")
            (v37ij / "formal_matrix.csv").write_text("candidate_id,status\n", encoding="utf-8")
            (v37ij / "source_equivalence_matrix.csv").write_text("candidate_id,status\nexample,ready\n", encoding="utf-8")
            _write_json(v37ij / "artifact_manifest.json", {"artifacts": []})

            v38 = console / "reports" / "v38"
            for name, payload in {
                "workflow_validation_demo_audit.json": {"ok": True, "releaseClassification": "diagnostic_only"},
                "demo_execution_audit.json": {"privateNetworkVerified": False, "networkRequestMade": False},
                "reconciliation_audit.json": {"networkRequestMade": False},
                "strategy_lab_ui_audit.json": {"status": "ready", "readOnly": True},
                "release_inventory.json": {"releaseCount": 0, "releases": []},
                "demo_approval_request.json": {"status": "not_required_zero_release", "requests": []},
                "demo_arm_audit.json": {"armed": False, "orderCount": 0},
                "final_route.json": {"v38Status": "completed_zero_release", "v39Status": "not_run_zero_release", "v40Status": "disabled"},
            }.items():
                _write_json(v38 / name, payload)

            (docs / "README.md").parent.mkdir(parents=True, exist_ok=True)
            (docs / "README.md").write_text("# Docs\n", encoding="utf-8")
            screenshots.mkdir(parents=True)
            (screenshots / "strategy-lab-desktop.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")

            result = build_evidence_delivery(
                quant_root=quant,
                console_root=console,
                docs_root=docs,
                requirements_path=requirements,
                screenshot_root=screenshots,
                output_root=output,
                repository_snapshots={
                    name: {
                        "repositoryPath": str(path),
                        "branch": f"feature/{name}",
                        "headCommit": "b" * 40,
                        "originMain": "c" * 40,
                        "ahead": 1,
                        "behind": 0,
                        "worktreeClean": True,
                        "preExistingChangesPreserved": True,
                        "mergeCommits": [],
                        "tags": [],
                        "pushStatus": "verified",
                        "remoteShaVerified": True,
                        "mergedToMain": False,
                    }
                    for name, path in (("Quant", quant), ("Console", console), ("Docs", docs))
                },
                test_summary={
                    "quant": {"passed": 1, "failed": 0, "skipped": 0, "subtests": 0},
                    "console": {"passed": 1, "failed": 0, "skipped": 0, "subtests": 0},
                    "docs": {"status": "passed"},
                },
            )

            expected_entries = {
                "AlphaPilot_V37F-V40_Final_Closeout_CN.md",
                "final_route.json",
                "final_self_check.json",
                "final_self_check.md",
                "artifact_manifest.json",
                "evidence_delivery_index.json",
            }
            self.assertTrue(expected_entries.issubset({path.name for path in output.iterdir()}))
            self.assertTrue(result["outerZip"].is_file())

            final_self_check = json.loads((output / "final_self_check.json").read_text(encoding="utf-8"))
            self.assertEqual(final_self_check["finalRoute"], "completed_zero_qualified_candidates")
            self.assertEqual(final_self_check["research"]["formalCandidateCount"], 0)
            self.assertEqual(final_self_check["release"]["releaseCount"], 0)
            self.assertEqual(final_self_check["demo"]["strategyDemoStatus"], "not_run")
            self.assertEqual(final_self_check["live"]["status"], "not_run")
            self.assertIsNone(final_self_check["demo"]["strategyOrderCount"])

            with zipfile.ZipFile(result["outerZip"]) as outer:
                outer_names = set(outer.namelist())
                for name in expected_entries:
                    self.assertIn(name, outer_names)
                stage_zip_names = {name for name in outer_names if name.endswith(".zip")}
                self.assertEqual(4, len(stage_zip_names))
                self.assertIsNone(outer.testzip())

            candidate_zip = output / "AlphaPilot-V37I-V37J-Candidate-and-Formal-Evidence.zip"
            with zipfile.ZipFile(candidate_zip) as archive:
                names = set(archive.namelist())
                self.assertIn("funding_carry_result.json", names)
                self.assertIn("turtle_donchian_result.json", names)
                self.assertIn("pair_relative_value_result.json", names)
                self.assertIn("funding_event_result.json", names)
                self.assertIn("formal_not_run.json", names)

            demo_zip = output / "AlphaPilot-V38-Demo-Function-and-UI-Evidence.zip"
            with zipfile.ZipFile(demo_zip) as archive:
                manifest = json.loads(archive.read("ui_screenshot_manifest.json"))
                statuses = {item["logicalName"]: item["status"] for item in manifest["screenshots"]}
                self.assertEqual(statuses["strategy_lab_source_registry"], "implemented")
                self.assertEqual(statuses["order_and_position"], "not_implemented")

            index = json.loads((output / "evidence_delivery_index.json").read_text(encoding="utf-8"))
            self.assertTrue(all(item["containsSensitiveData"] is False for item in index["artifacts"]))
            self.assertTrue(all(len(item["sha256"]) == 64 for item in index["artifacts"]))

            git_inventory = output / "changed_file_inventory.csv"
            with git_inventory.open("r", encoding="utf-8", newline="") as handle:
                self.assertGreaterEqual(len(list(csv.DictReader(handle))), 0)


if __name__ == "__main__":
    unittest.main()
