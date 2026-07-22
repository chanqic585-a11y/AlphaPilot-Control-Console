from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.ai_orchestration.budget import AIBudgetLedger, AIBudgetPolicy
from alphapilot_control_console.ai_orchestration.circuit_breaker import ProviderCircuitBreaker
from alphapilot_control_console.ai_orchestration.errors import (
    BudgetExceededError,
    ProviderUnavailableError,
)


class AIBudgetPolicyTests(unittest.TestCase):
    def test_provider_task_and_campaign_budgets_are_enforced_without_storing_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = AIBudgetLedger(Path(directory) / "budget.sqlite")
            policy = AIBudgetPolicy(
                ledger=ledger,
                daily_provider_limits={"openai": 2.0},
                daily_task_limits={"strategy_hypothesis": 1.5},
                campaign_limits={"campaign-1": 1.0},
            )
            try:
                policy.record_usage(
                    provider="openai",
                    task_type="strategy_hypothesis",
                    campaign_id="campaign-1",
                    request_id="request-1",
                    cost_usd=0.75,
                    total_tokens=100,
                )
                policy.assert_available(
                    provider="openai",
                    task_type="strategy_hypothesis",
                    campaign_id="campaign-1",
                    requested_cost_ceiling_usd=0.20,
                )
                with self.assertRaises(BudgetExceededError):
                    policy.assert_available(
                        provider="openai",
                        task_type="strategy_hypothesis",
                        campaign_id="campaign-1",
                        requested_cost_ceiling_usd=0.50,
                    )
                projection = ledger.projection()
            finally:
                ledger.close()

        self.assertEqual(projection["usageCount"], 1)
        self.assertNotIn("prompt", repr(projection).lower())


class ProviderCircuitBreakerTests(unittest.TestCase):
    def test_repeated_failures_open_circuit_until_cooldown(self) -> None:
        clock = [100.0]
        circuit = ProviderCircuitBreaker(
            failure_threshold=2,
            cooldown_seconds=30,
            clock=lambda: clock[0],
        )

        circuit.record_failure("openai")
        self.assertEqual(circuit.status("openai"), "degraded")
        circuit.record_failure("openai")
        self.assertEqual(circuit.status("openai"), "unavailable")
        with self.assertRaises(ProviderUnavailableError):
            circuit.assert_available("openai")

        clock[0] += 31
        self.assertEqual(circuit.status("openai"), "degraded")
        circuit.record_success("openai")
        self.assertEqual(circuit.status("openai"), "healthy")


if __name__ == "__main__":
    unittest.main()
