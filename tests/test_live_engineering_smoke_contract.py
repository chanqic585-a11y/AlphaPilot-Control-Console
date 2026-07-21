from __future__ import annotations

import unittest

from alphapilot_control_console.live_engineering_smoke_contract import (
    build_live_engineering_smoke_approval_request,
    build_live_engineering_smoke_contract,
    validate_live_engineering_smoke_approval,
    validate_live_engineering_smoke_contract,
)


class LiveEngineeringSmokeContractTests(unittest.TestCase):
    def test_contract_is_single_attempt_minimum_order_and_strategy_ineligible(self) -> None:
        contract = build_live_engineering_smoke_contract(
            created_at="2026-07-21T06:00:00Z",
            maximum_notional_usdt=10.0,
        )

        validate_live_engineering_smoke_contract(contract)
        self.assertEqual(contract["environment"], "okx_live")
        self.assertEqual(contract["maximumAttempts"], 1)
        self.assertEqual(contract["maximumConcurrentPositions"], 1)
        self.assertEqual(contract["sizePolicy"], "exchange_minimum_size")
        self.assertEqual(contract["orderType"], "limit")
        self.assertEqual(contract["limitOffsetBps"], 1000)
        self.assertEqual(contract["marginMode"], "isolated")
        self.assertEqual(contract["maximumLeverage"], 1)
        self.assertFalse(contract["strategyQualification"])
        self.assertFalse(contract["promotionEligible"])
        self.assertFalse(contract["liveCanaryEvidenceEligible"])
        self.assertFalse(contract["withdrawAllowed"])

    def test_exact_approval_is_required_for_exact_contract_hash(self) -> None:
        contract = build_live_engineering_smoke_contract(
            created_at="2026-07-21T06:00:00Z",
            maximum_notional_usdt=10.0,
        )
        request = build_live_engineering_smoke_approval_request(contract)

        self.assertEqual(request["status"], "blocked_waiting_exact_live_smoke_approval")
        self.assertEqual(request["contractHash"], contract["contractHash"])
        with self.assertRaises(PermissionError):
            validate_live_engineering_smoke_approval(contract, {})
        approval = {
            "actor": "user_explicit",
            "contractHash": contract["contractHash"],
            "confirmation": request["requiredConfirmation"],
        }
        validated = validate_live_engineering_smoke_approval(contract, approval)
        self.assertEqual(validated["status"], "approved")
        self.assertEqual(validated["contractHash"], contract["contractHash"])


if __name__ == "__main__":
    unittest.main()
