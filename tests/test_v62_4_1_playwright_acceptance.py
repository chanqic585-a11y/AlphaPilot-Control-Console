from __future__ import annotations

import unittest

from alphapilot_control_console.v62_4_1_playwright_acceptance import (
    evaluate_browser_snapshot,
)


class V6241PlaywrightAcceptanceTests(unittest.TestCase):
    def test_matching_production_snapshot_passes(self) -> None:
        result = evaluate_browser_snapshot(
            viewport="desktop",
            strategy_dom={
                "canEnterDemo": "1",
                "needsForwardValidation": "0",
                "failed": "0",
                "dataInsufficient": "0",
                "systemIssue": "0",
                "campaignId": "campaign-1",
                "candidateTrials": "4 / 12",
                "stable": "2",
                "formalReady": "1",
                "formalBlocked": "1",
            },
            strategy_api={
                "resultCounts": {
                    "canEnterDemo": 1,
                    "needsForwardValidation": 0,
                    "failed": 0,
                    "dataInsufficient": 0,
                    "systemIssue": 0,
                },
                "currentPilot": {
                    "campaignId": "campaign-1",
                    "candidateCount": 4,
                    "trialCount": 12,
                    "stableSelectionCount": 2,
                    "formalReadyCandidateCount": 1,
                    "formalBlockedCandidateCount": 1,
                },
            },
            demo_dom={"runningStrategyCount": "0", "openPositionCount": "0"},
            demo_api={"runningStrategyCount": 0, "openPositionCount": 0},
            ai_dom={
                "credentialState": "当前凭据未注入",
                "historicalSmokeState": "历史 Smoke 已通过",
            },
            ai_api={
                "currentCredentialState": {
                    "status": "provider_credentials_required",
                },
                "historicalProviderSmoke": {
                    "status": "provider_smoke_passed",
                },
            },
            console_errors=[],
            page_errors=[],
            request_failures=[],
            horizontal_overflow=False,
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["issues"], [])

    def test_console_error_placeholder_and_overflow_fail(self) -> None:
        result = evaluate_browser_snapshot(
            viewport="mobile-390",
            strategy_dom={
                "canEnterDemo": "--",
                "needsForwardValidation": "0",
                "failed": "0",
                "dataInsufficient": "0",
                "systemIssue": "0",
                "campaignId": "--",
                "candidateTrials": "--",
                "stable": "0",
                "formalReady": "0",
                "formalBlocked": "0",
            },
            strategy_api={"resultCounts": {}, "currentPilot": {}},
            demo_dom={"runningStrategyCount": "0", "openPositionCount": "0"},
            demo_api={"runningStrategyCount": 0, "openPositionCount": 0},
            ai_dom={
                "credentialState": "--",
                "historicalSmokeState": "--",
            },
            ai_api={},
            console_errors=["boom"],
            page_errors=[],
            request_failures=[],
            horizontal_overflow=True,
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("console_error", result["issues"])
        self.assertIn("horizontal_overflow", result["issues"])
        self.assertIn("strategy_placeholder_value", result["issues"])


if __name__ == "__main__":
    unittest.main()
