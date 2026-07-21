from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.adaptive_learning_governance_evidence import (
    generate_adaptive_learning_governance_evidence,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AdaptiveLearningGovernanceEvidenceTests(unittest.TestCase):
    def test_generator_disposes_observer_release_without_mutating_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            _write_json(
                source / "experimental_live_release.json",
                {
                    "releaseId": "experimental-live-fixture",
                    "releaseHash": "experimental-live-hash",
                    "riskOverlayHash": "risk-hash",
                    "modelHash": "observer-model-hash",
                    "modelPolicyHash": "observer-policy-hash",
                    "status": "blocked_waiting_exact_live_release_approval",
                    "executionBoundary": {
                        "mechanicalExecutionAllowedAfterExactApproval": True,
                        "withdrawAllowed": False,
                    },
                },
            )
            _write_json(
                source / "exact_live_approval_request.json",
                {
                    "releaseId": "experimental-live-fixture",
                    "releaseHash": "experimental-live-hash",
                    "riskOverlayHash": "risk-hash",
                    "approvalRequestHash": "approval-request-hash",
                    "status": "blocked_waiting_exact_live_release_approval",
                },
            )
            _write_json(
                source / "experimental_live_risk_overlay.json",
                {
                    "riskOverlayHash": "risk-hash",
                    "profileId": "risk-profile-v1",
                    "profileHash": "risk-profile-hash",
                    "profile": {"allocatedCapitalUSDT": 1000.0},
                },
            )
            _write_json(
                source / "adaptive_learning_live_readiness.json",
                {
                    "passed": False,
                    "status": "blocked_not_ready",
                    "modelMode": "observer",
                    "blockers": ["adaptive_evidence_not_ready:qlibOfflineCampaignReady"],
                },
            )
            _write_json(
                source / "observer_sidecar_binding.json",
                {
                    "modelHash": "observer-model-hash",
                    "modelPolicyHash": "observer-policy-hash",
                    "sidecarBindingHash": "observer-sidecar-hash",
                },
            )
            source_hashes = {
                path.name: _sha256(path)
                for path in source.iterdir()
                if path.is_file()
            }

            result = generate_adaptive_learning_governance_evidence(
                source,
                output,
                generated_at="2026-07-21T08:00:00Z",
            )

            self.assertEqual(result["status"], "draft_blocked_adaptive_learning_not_ready")
            self.assertEqual(
                source_hashes,
                {
                    path.name: _sha256(path)
                    for path in source.iterdir()
                    if path.is_file()
                },
            )
            disposition = json.loads(
                (output / "current_experimental_live_draft_disposition.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(disposition["releaseHash"], "experimental-live-hash")
            self.assertEqual(
                disposition["status"],
                "draft_blocked_adaptive_learning_not_ready",
            )
            self.assertFalse(disposition["approvalRequestActionable"])
            self.assertFalse(
                disposition["mechanicalExecutionAllowedAfterExactApproval"]
            )
            self.assertTrue(disposition["immutableSourceArtifactsPreserved"])

            technical = json.loads(
                (output / "adaptive_learning_technical_readiness_gate.json").read_text(
                    encoding="utf-8"
                )
            )
            approval = json.loads(
                (output / "exact_live_release_approval_gate.json").read_text(
                    encoding="utf-8"
                )
            )
            arm = json.loads(
                (output / "live_arm_gate.json").read_text(encoding="utf-8")
            )
            self.assertFalse(technical["passed"])
            self.assertFalse(technical["exactApprovalEvaluated"])
            self.assertNotIn("exactHumanApproval", technical["evidenceStatus"])
            self.assertFalse(approval["passed"])
            self.assertFalse(approval["approvalRequestActionable"])
            self.assertFalse(arm["passed"])
            self.assertEqual(arm["armStatus"], "not_run")
            self.assertFalse(arm["liveEnabled"])
            self.assertFalse(arm["withdrawAllowed"])

            latency = json.loads(
                (output / "execution_latency_policy_binding.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("maximumSignalAgeSeconds", latency)
            self.assertLess(
                latency["maximumSignalAgeMs"],
                latency["criticalLatencyFailureMs"],
            )
            self.assertEqual(latency["criticalLatencyFailureMs"], 20_000)

            risk = json.loads(
                (output / "draft_risk_profile.json").read_text(encoding="utf-8")
            )
            self.assertEqual(risk["status"], "draft")
            self.assertTrue(risk["allRiskParametersAdjustableBeforeApproval"])
            self.assertTrue(risk["riskChangeRequiresNewRiskOverlayHash"])
            self.assertTrue((output / "technical_gap_matrix.json").is_file())
            self.assertTrue((output / "artifact_manifest.json").is_file())
            self.assertTrue((output / "final_closeout_cn.md").is_file())


if __name__ == "__main__":
    unittest.main()
