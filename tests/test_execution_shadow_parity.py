from __future__ import annotations

import unittest

from alphapilot_control_console.execution_shadow_parity import (
    ShadowDecisionEvaluator,
    run_execution_shadow_parity,
)


def _decision(case: dict[str, object]) -> dict[str, object]:
    score = float(case["score"])
    return {
        "eligible": score >= 0.5,
        "instrumentId": case["instrumentId"],
        "side": "buy" if score >= 0.5 else None,
        "reasonCodes": [] if score >= 0.5 else ["score_below_threshold"],
        "score": score,
        "generatedAt": "ignored-runtime-timestamp",
    }


class ExecutionShadowParityTests(unittest.TestCase):
    def test_requires_full_fixture_and_replay_parity_without_order_access(self) -> None:
        reference = ShadowDecisionEvaluator("production-reference", _decision)
        shadow = ShadowDecisionEvaluator("remediation-shadow", _decision)

        result = run_execution_shadow_parity(
            reference=reference,
            shadow=shadow,
            deterministic_fixtures=[
                {"caseId": "fixture-pass", "instrumentId": "BTC-USDT-SWAP", "score": 0.7},
                {"caseId": "fixture-block", "instrumentId": "ETH-USDT-SWAP", "score": 0.3},
            ],
            replay_events=[
                {"caseId": "replay-1", "instrumentId": "SOL-USDT-SWAP", "score": 0.8},
            ],
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["deterministicFixtureParity"]["parityRate"], 1.0)
        self.assertEqual(result["replayParity"]["parityRate"], 1.0)
        self.assertTrue(result["shadowOrderAccessDisabled"])
        self.assertFalse(result["cutoverPerformed"])
        self.assertTrue(result["cutoverEligible"])

    def test_any_decision_mismatch_blocks_cutover_and_records_case(self) -> None:
        def changed(case: dict[str, object]) -> dict[str, object]:
            decision = _decision(case)
            decision["eligible"] = not bool(decision["eligible"])
            return decision

        result = run_execution_shadow_parity(
            reference=ShadowDecisionEvaluator("production-reference", _decision),
            shadow=ShadowDecisionEvaluator("remediation-shadow", changed),
            deterministic_fixtures=[
                {"caseId": "fixture-mismatch", "instrumentId": "BTC-USDT-SWAP", "score": 0.7},
            ],
            replay_events=[],
        )

        self.assertFalse(result["passed"])
        self.assertFalse(result["cutoverEligible"])
        self.assertEqual(result["deterministicFixtureParity"]["mismatchCaseIds"], ["fixture-mismatch"])

    def test_shadow_evaluator_cannot_have_order_access(self) -> None:
        with self.assertRaises(PermissionError):
            run_execution_shadow_parity(
                reference=ShadowDecisionEvaluator("production-reference", _decision),
                shadow=ShadowDecisionEvaluator(
                    "unsafe-shadow",
                    _decision,
                    order_access=True,
                ),
                deterministic_fixtures=[],
                replay_events=[],
            )


if __name__ == "__main__":
    unittest.main()
