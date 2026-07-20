from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.v41_v45_evidence import write_v41_v45_evidence_bundle


PRODUCT_FILES = {
    "demo_private_preflight.json",
    "demo_universe_audit.json",
    "engineering_smoke_contract.json",
    "engineering_smoke_approval_overlay.json",
    "engineering_smoke_order_ledger.jsonl",
    "engineering_smoke_fill_ledger.jsonl",
    "engineering_smoke_position_ledger.jsonl",
    "engineering_smoke_cancel_audit.json",
    "engineering_smoke_fill_close_audit.json",
    "private_websocket_audit.json",
    "rest_reconciliation_audit.json",
    "restart_recovery_audit.json",
    "kill_switch_audit.json",
    "strategy_evidence_isolation_audit.json",
    "ui_screenshot_manifest.json",
}


class V41V45EvidenceTests(unittest.TestCase):
    def test_missing_process_credentials_produces_truthful_blocked_track_p(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            quant = root / "quant"
            campaign = quant / "reports" / "mechanism_breakthrough" / "v41_v45_fixture"
            research = campaign / "research"
            research.mkdir(parents=True)
            (campaign / "program_state.json").write_text(json.dumps({
                "trackRStatus": "completed_zero_qualified_candidates",
                "trackPStatus": "pending",
            }), encoding="utf-8")
            (campaign / "program_budget.json").write_text(json.dumps({
                "campaignsUsed": 2,
                "formalRunsUsed": 0,
            }), encoding="utf-8")
            (campaign / "integration_merge_receipt.json").write_text("{}", encoding="utf-8")
            (research / "campaign_summary.json").write_text(json.dumps({
                "campaignId": "campaign-v41-fixture",
                "status": "completed_zero_qualified_candidates",
                "candidateCount": 4,
                "prefilterSurvivorCount": 0,
                "formalCandidateCount": 0,
                "formalRunCount": 0,
                "releaseCount": 0,
                "lockedOosReadCount": 0,
                "networkCalls": 0,
                "budget": {
                    "fullBacktestsUsed": 4,
                    "fullBacktestsRemainingAfter": 87,
                },
            }), encoding="utf-8")
            (research / "release_inventory.json").write_text(json.dumps({
                "status": "not_run",
                "releaseCount": 0,
                "releases": [],
            }), encoding="utf-8")
            (research / "formal_gate_matrix.csv").write_text(
                "candidateId,gateName,actual,operator,required,passed,status\n",
                encoding="utf-8",
            )
            (research / "artifact_manifest.json").write_text("{}", encoding="utf-8")

            output = root / "delivery"
            result = write_v41_v45_evidence_bundle(
                output,
                quant_root=quant,
                environment={},
            )

            self.assertEqual(result["masterStatus"], "research_complete_demo_smoke_blocked")
            self.assertEqual(result["trackPStatus"], "blocked_demo_credentials_not_injected")
            self.assertEqual(result["trackRStatus"], "completed_zero_qualified_candidates")
            self.assertEqual(PRODUCT_FILES, {path.name for path in (output / "product").iterdir()})
            preflight = json.loads((output / "product" / "demo_private_preflight.json").read_text(encoding="utf-8"))
            self.assertEqual(preflight["status"], "blocked_demo_credentials_not_injected")
            self.assertFalse(preflight["credentialsInjected"])
            self.assertFalse(preflight["networkRequestMade"])
            isolation = json.loads((output / "product" / "strategy_evidence_isolation_audit.json").read_text(encoding="utf-8"))
            self.assertFalse(isolation["strategyEvidenceChanged"])
            self.assertFalse(isolation["strategyQualification"])
            self.assertFalse(isolation["promotionEvidenceEligible"])
            order_status = json.loads((output / "product" / "engineering_smoke_order_ledger.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(order_status["status"], "not_run")
            self.assertEqual(order_status["recordType"], "stage_status")
            self.assertEqual(result["releaseCount"], 0)
            self.assertEqual(result["formalRunCount"], 0)
            self.assertEqual(result["lockedOosReadCount"], 0)
            self.assertEqual(result["budget"]["fullBacktestsUsed"], 4)
            self.assertEqual(result["budget"]["fullBacktestsRemainingAfter"], 87)
            release_status = json.loads(
                (output / "release" / "candidate_releases" / "status.json").read_text(encoding="utf-8")
            )
            self.assertEqual(release_status["status"], "not_run_no_qualified_formal_candidate")
            self.assertEqual(release_status["releaseCount"], 0)
            self.assertTrue((output / "AlphaPilot_V41-V45_Final_Closeout_CN.md").is_file())
            self.assertTrue((output / "artifact_manifest.json").is_file())

            serialized = "\n".join(path.read_text(encoding="utf-8") for path in output.rglob("*") if path.is_file())
            self.assertNotIn("apiSecret", serialized)
            self.assertNotIn("passphrase", serialized.lower())


if __name__ == "__main__":
    unittest.main()
