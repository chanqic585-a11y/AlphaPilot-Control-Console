from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.top200_minimal_ui_projection import (
    Top200MinimalUiProjection,
)


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "web" / "top200-minimal-ui.js").read_text(encoding="utf-8")


def _write_json(root: Path, name: str, payload: dict) -> None:
    (root / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


class V59V60LiveReadinessUiTests(unittest.TestCase):
    def test_live_projection_is_truthful_and_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_json(
                root,
                "experimental_live_release.json",
                {
                    "releaseId": "experimental_live_canary_fixture",
                    "releaseHash": "experimental_live_release_fixture",
                    "riskOverlayHash": "live_risk_overlay_fixture",
                    "adaptiveLearningReadinessHash": "adaptive_readiness_fixture",
                    "adaptiveLearningReadinessPassed": False,
                    "status": "blocked_waiting_exact_live_release_approval",
                    "generatedAt": "2026-07-21T07:00:20Z",
                },
            )
            _write_json(
                root,
                "exact_live_approval_request.json",
                {
                    "approvalRequestHash": "approval_request_fixture",
                    "allocatedCapitalUSDT": 1000.0,
                    "maximumAcceptedLossUSDT": 1000.0,
                    "riskPerTradeUSDT": 2.5,
                    "maximumPortfolioOpenRiskUSDT": 10.0,
                    "maximumConcurrentPositions": 1,
                    "maximumLeverage": 1,
                    "status": "blocked_waiting_exact_live_release_approval",
                },
            )
            _write_json(
                root,
                "adaptive_learning_live_readiness.json",
                {
                    "passed": False,
                    "status": "blocked_not_ready",
                    "modelMode": "observer",
                    "blockers": [
                        "adaptive_evidence_not_ready:qlibCampaignReady",
                        "live_model_mode_not_decision_participating",
                    ],
                },
            )
            _write_json(
                root,
                "live_engineering_smoke_binding.json",
                {
                    "contractHash": "live_engineering_smoke_fixture",
                    "status": "completed_canceled_and_reconciled",
                    "checks": {
                        "cancelConfirmed": True,
                        "zeroOpenPositions": True,
                        "zeroOpenOrders": True,
                    },
                },
            )
            _write_json(
                root,
                "live_execution_state.json",
                {
                    "approvalStatus": "not_run",
                    "armStatus": "not_run",
                    "strategyOrderStatus": "not_run",
                    "liveEnabled": False,
                    "withdrawAllowed": False,
                },
            )
            _write_json(
                root,
                "live_experiment_profile.json",
                {
                    "allocatedCapitalUSDT": 1000.0,
                    "maximumAcceptedLossUSDT": 1000.0,
                    "riskPerTradeUSDT": 2.5,
                    "maximumPortfolioOpenRiskUSDT": 10.0,
                    "maximumConcurrentPositions": 1,
                    "maximumLeverage": 1,
                    "marginMode": "isolated",
                    "scanTopN": 200,
                },
            )
            for name in (
                "live_order_ledger.json",
                "live_fill_ledger.json",
                "live_position_ledger.json",
            ):
                _write_json(root, name, {"status": "not_run", "records": []})

            projection = Top200MinimalUiProjection(
                root,
                live_readiness_root=root,
            )
            summary = projection.live_canary_readiness()

        self.assertEqual(summary["status"], "blocked_not_ready")
        self.assertEqual(summary["engineeringSmoke"]["status"], "passed")
        self.assertEqual(summary["adaptiveLearning"]["blockerCount"], 2)
        self.assertEqual(summary["execution"]["approvalStatus"], "not_run")
        self.assertFalse(summary["execution"]["liveEnabled"])
        self.assertFalse(summary["execution"]["withdrawAllowed"])
        self.assertEqual(summary["nextAction"], "complete_adaptive_learning_readiness")
        self.assertEqual(summary["risk"]["maximumLeverage"], 1)
        self.assertEqual(summary["orders"]["status"], "not_run")
        self.assertEqual(summary["positions"]["count"], 0)
        self.assertIn("releaseHash", summary["audit"])

    def test_live_page_keeps_primary_status_compact_and_audit_collapsed(self) -> None:
        self.assertIn('id="top200MinimalLive"', HTML)
        self.assertIn('id="top200LiveReadinessBadge"', HTML)
        self.assertIn('id="top200LiveNextAction"', HTML)
        self.assertIn('<details id="liveAdvancedControls"', HTML)
        self.assertIn('id="top200LiveAudit"', HTML)
        self.assertIn('fetchJson("/api/live/canary-readiness")', SCRIPT)
        self.assertIn("renderLiveCanaryReadiness", SCRIPT)

        compact = HTML.split('id="top200MinimalLive"', 1)[1].split(
            'id="liveAdvancedControls"', 1
        )[0]
        self.assertNotIn("ARM_OKX_LIVE_CANARY", compact)
        self.assertNotIn("启动自动运行", compact)
        self.assertNotIn("创建订单", compact)


if __name__ == "__main__":
    unittest.main()
