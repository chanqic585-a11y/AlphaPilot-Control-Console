from __future__ import annotations

import json
import unittest

from alphapilot_control_console.demo_evaluation_audit import build_demo_evaluation_audit
from alphapilot_control_console.unified_auto_execution_controller import ReleaseSchedule


class DemoEvaluationAuditTests(unittest.TestCase):
    def test_builds_bounded_zero_match_audit_without_private_state(self) -> None:
        audit = build_demo_evaluation_audit(
            {
                "ok": True,
                "matchedSignalCount": 0,
                "createdOrderCount": 0,
                "scans": {
                    "release-1": {
                        "signals": [],
                        "universe": {
                            "totalInstrumentCount": 405,
                            "liquidityEligibleCount": 375,
                            "screeningPoolCount": 100,
                        },
                        "progress": {"completed": 100, "required": 100, "percent": 100},
                        "rejections": [
                            {
                                "instId": "BTC-USDT-SWAP",
                                "reason": "frozen_rules_not_matched",
                                "rules": [
                                    {"checkId": "trend_up", "matched": True},
                                    {"checkId": "breakout_20", "matched": False},
                                ],
                            },
                            {
                                "instId": "ETH-USDT-SWAP",
                                "reason": "frozen_rules_not_matched",
                                "rules": [
                                    {"checkId": "trend_up", "matched": False},
                                    {"checkId": "breakout_20", "matched": False},
                                ],
                            },
                        ],
                    }
                },
                "rejectedSignals": [],
                "latencyMetrics": {"stageDurationsMs": {"closeToEvaluationFinishedMs": 840}},
                "availableEquityUsdt": 999999,
                "apiKey": "must-not-survive",
            },
            releases=[ReleaseSchedule("release-1", "strategy-1", "1h")],
        )

        self.assertEqual(audit["state"], "evaluated_zero_matches")
        self.assertEqual(audit["evaluatedReleaseCount"], 1)
        self.assertEqual(audit["marketSummary"]["totalInstrumentCount"], 405)
        self.assertEqual(audit["marketSummary"]["deepScreenCount"], 100)
        self.assertEqual(audit["rejectionReasonCounts"], {"frozen_rules_not_matched": 2})
        self.assertEqual(audit["failedCheckCounts"], {"breakout_20": 2, "trend_up": 1})
        self.assertEqual(audit["nearMisses"][0]["instId"], "BTC-USDT-SWAP")
        self.assertEqual(audit["nearMisses"][0]["failedCheckCount"], 1)
        serialized = json.dumps(audit)
        self.assertNotIn("apiKey", serialized)
        self.assertNotIn("availableEquity", serialized)
        self.assertNotIn("must-not-survive", serialized)

    def test_distinguishes_matched_rejected_and_submitted_orders(self) -> None:
        release = ReleaseSchedule("release-1", "strategy-1", "15m")
        rejected = build_demo_evaluation_audit(
            {
                "matchedSignalCount": 2,
                "createdOrderCount": 0,
                "scans": {},
                "rejectedSignals": [
                    {"reason": "portfolio_position_limit"},
                    {"reason": "signal_expired"},
                ],
                "orderOutcomes": [],
            },
            releases=[release],
        )
        submitted = build_demo_evaluation_audit(
            {
                "matchedSignalCount": 1,
                "createdOrderCount": 1,
                "scans": {},
                "rejectedSignals": [],
                "orderOutcomes": [{"status": "submitted", "exchangeCode": "0"}],
            },
            releases=[release],
        )

        self.assertEqual(rejected["state"], "matched_rejected")
        self.assertEqual(rejected["executionRejectionReasonCounts"]["signal_expired"], 1)
        self.assertEqual(submitted["state"], "order_submitted")
        self.assertEqual(submitted["orderAttemptCount"], 1)
        self.assertEqual(submitted["exchangeCodeCounts"], {"0": 1})


if __name__ == "__main__":
    unittest.main()
