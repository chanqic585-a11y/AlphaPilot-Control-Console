from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.v38_evidence import write_v38_evidence_bundle


class V38EvidenceTests(unittest.TestCase):
    def test_zero_release_evidence_keeps_v39_closed_and_v40_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            quant_root = root / "quant"
            output_root = root / "output"
            source_root = quant_root / "research" / "external_capabilities" / "vibe_trading"
            integration_root = quant_root / "reports" / "integration" / "v37g_v37h"
            campaign_root = quant_root / "reports" / "strategy_acquisition" / "v37i_v37j"
            source_root.mkdir(parents=True)
            integration_root.mkdir(parents=True)
            campaign_root.mkdir(parents=True)
            (source_root / "source_manifest.json").write_text(json.dumps({
                "repository": "HKUDS/Vibe-Trading",
                "commit": "7d42de944466e1a1f12f0df3933624fe665dee3c",
                "paths": [],
            }), encoding="utf-8")
            (source_root / "component_adoption_map.json").write_text("{}", encoding="utf-8")
            (integration_root / "source_inventory.json").write_text("[]", encoding="utf-8")
            (integration_root / "factor_registry.json").write_text("[]", encoding="utf-8")
            (campaign_root / "campaign_summary.json").write_text(json.dumps({
                "status": "completed_zero_qualified_candidates",
                "formalCandidateCount": 0,
            }), encoding="utf-8")
            (campaign_root / "candidate_inventory.json").write_text(json.dumps({"candidates": []}), encoding="utf-8")
            (campaign_root / "experiment_budget.json").write_text("{}", encoding="utf-8")
            (campaign_root / "failure_attribution.json").write_text("{}", encoding="utf-8")
            (campaign_root / "formal_route.json").write_text(json.dumps({
                "formalCandidateCount": 0,
                "releaseCount": 0,
                "demoArm": False,
            }), encoding="utf-8")

            result = write_v38_evidence_bundle(output_root, quant_root=quant_root)

            expected = {
                "workflow_validation_demo_audit.json",
                "demo_execution_audit.json",
                "reconciliation_audit.json",
                "strategy_lab_ui_audit.json",
                "release_inventory.json",
                "demo_approval_request.json",
                "demo_arm_audit.json",
                "final_route.json",
                "final_self_check.md",
                "artifact_manifest.json",
            }
            self.assertEqual(expected, {path.name for path in output_root.iterdir()})
            self.assertEqual(result["finalRoute"]["v39Status"], "not_run_zero_release")
            self.assertEqual(result["finalRoute"]["v40Status"], "disabled")
            self.assertFalse(result["demoArmAudit"]["armed"])
            self.assertEqual(result["releaseInventory"]["releaseCount"], 0)
            capability = result["demoExecutionAudit"]
            self.assertTrue(capability["capabilities"]["serverTimeOffset"])
            self.assertTrue(capability["capabilities"]["privateWebsocketRuntime"])
            self.assertTrue(capability["implementationVerified"])
            self.assertFalse(capability["privateNetworkVerified"])
            self.assertEqual(capability["runtimeActivation"], "not_started_zero_release")
            self.assertTrue(result["reconciliationAudit"]["wsRestReconciliationSupported"])
            self.assertFalse(result["reconciliationAudit"]["networkRequestMade"])
            manifest = json.loads((output_root / "artifact_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["artifacts"]), 9)
            self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest["artifacts"]))


if __name__ == "__main__":
    unittest.main()
