from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.ai_research_governor import (
    AIResearchGovernor,
    append_negative_research_records,
    build_negative_research_record,
    load_negative_research_memory,
)


class AIResearchGovernorTests(unittest.TestCase):
    def test_retrieves_matching_failed_family_before_generation(self) -> None:
        failed = build_negative_research_record(
            strategy_id="candidate-old",
            family_id="pullback",
            parent_version="v1",
            hypothesis="15m trend pullback",
            failure_layer="Cost/Capacity",
            metrics={"profitFactor": 0.91},
            cost={"roundTripBps": 12},
            capacity={"eligibleSymbols": 4},
            stability={"walkForwardPass": False},
            regime={"failed": ["sideways"]},
            signal_correlation=0.94,
            prohibited_repeats=["same_entry_with_looser_gate"],
        )
        governor = AIResearchGovernor([failed])

        context = governor.prepare_generation_context(
            family_id="pullback",
            hypothesis="15m trend pullback with volume confirmation",
            timeframe="15m",
            direction="long",
        )

        self.assertEqual(context["memoryHitCount"], 1)
        self.assertEqual(context["memoryHits"][0]["strategyId"], "candidate-old")
        self.assertIn("same_entry_with_looser_gate", context["prohibitedRepeats"])
        self.assertFalse(context["executionAuthorized"])

    def test_candidate_draft_rejects_gate_lowering_and_multi_variable_tuning(self) -> None:
        governor = AIResearchGovernor([])
        draft = {
            "schemaType": "CandidateDraft",
            "candidateId": "candidate-new",
            "familyId": "pullback",
            "parentVersion": "v1",
            "changedVariables": ["rsiThreshold", "volumeRatio"],
            "gateOverrides": {"minimumProfitFactor": 0.8},
            "lockedOosUsedForTuning": True,
            "automaticPromotionAllowed": True,
        }

        result = governor.validate_draft(draft)

        self.assertFalse(result["valid"])
        self.assertEqual(
            set(result["blockers"]),
            {
                "automatic_promotion_forbidden",
                "gate_override_forbidden",
                "locked_oos_tuning_forbidden",
                "single_variable_experiment_required",
            },
        )

    def test_valid_experiment_draft_builds_non_executable_run_card(self) -> None:
        governor = AIResearchGovernor([])
        result = governor.validate_draft(
            {
                "schemaType": "ExperimentDraft",
                "candidateId": "candidate-new",
                "familyId": "pullback",
                "parentVersion": "v1",
                "changedVariables": ["volumeRatio"],
                "gateOverrides": {},
                "lockedOosUsedForTuning": False,
                "automaticPromotionAllowed": False,
                "dataSnapshotId": "snapshot-1",
                "costPolicyHash": "cost-1",
                "capitalPolicyHash": "capital-1",
                "benchmarkPolicyHash": "benchmark-1",
                "randomSeed": 42,
            }
        )

        self.assertTrue(result["valid"])
        self.assertFalse(result["runCard"]["executionAuthorized"])
        self.assertFalse(result["runCard"]["automaticPromotionAllowed"])
        self.assertEqual(result["runCard"]["changedVariable"], "volumeRatio")

    def test_negative_memory_store_is_atomic_and_deduplicated_by_record_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "negative_research_memory.jsonl"
            record = build_negative_research_record(
                strategy_id="candidate-old",
                family_id="pullback",
                parent_version="v1",
                hypothesis="15m trend pullback",
                failure_layer="Signal Edge",
                metrics={"profitFactor": 0.91},
                cost={"roundTripBps": 12},
                capacity={"eligibleSymbols": 4},
                stability={"walkForwardPass": False},
                regime={"failed": ["sideways"]},
                signal_correlation=0.94,
                prohibited_repeats=["same_entry_with_looser_gate"],
            )

            first = append_negative_research_records(path, [record])
            second = append_negative_research_records(path, [record])

            self.assertEqual(first["appendedCount"], 1)
            self.assertEqual(second["appendedCount"], 0)
            self.assertEqual(load_negative_research_memory(path), [record])
            self.assertFalse(path.with_suffix(path.suffix + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()
