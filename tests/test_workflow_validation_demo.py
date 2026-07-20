from __future__ import annotations

import unittest

from alphapilot_control_console.workflow_validation_demo import (
    run_workflow_validation_demo_fixture,
)


class WorkflowValidationDemoTests(unittest.TestCase):
    def test_fixture_covers_lifecycle_and_is_statistically_isolated(self) -> None:
        result = run_workflow_validation_demo_fixture()

        self.assertTrue(result["ok"])
        self.assertEqual(result["releaseClassification"], "diagnostic_only")
        self.assertFalse(result["strategyQualification"])
        self.assertFalse(result["formalPass"])
        self.assertFalse(result["livePromotionEligible"])
        self.assertEqual(
            [row["stage"] for row in result["timeline"]],
            [
                "import",
                "approval",
                "arm",
                "signal",
                "order",
                "position",
                "exit",
                "reconciliation",
                "ui",
            ],
        )
        self.assertTrue(all(row["status"] == "passed" for row in result["timeline"]))
        self.assertTrue(result["evidence"]["engineeringOnly"])
        self.assertFalse(result["evidence"]["formalEvidenceEligible"])
        self.assertFalse(result["evidence"]["strategyPerformanceEligible"])
        self.assertFalse(result["safetyBoundary"]["exchangeNetworkUsed"])
        self.assertFalse(result["safetyBoundary"]["liveOrderCreated"])
        self.assertFalse(result["safetyBoundary"]["withdrawAllowed"])


if __name__ == "__main__":
    unittest.main()
