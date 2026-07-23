from __future__ import annotations

from pathlib import Path

import pytest

from alphapilot_control_console.strategy_factory_v2 import (
    FAILURE_LAYERS,
    StrategyFactoryV2,
    StrategyFactoryV2Error,
)


def _hypothesis() -> dict:
    return {
        "hypothesisId": "hypothesis_trend_recovery_001",
        "familyId": "trend_recovery",
        "familyFingerprint": "family_fp_trend_recovery_v1",
        "mechanism": "A liquid contract can resume its prevailing trend after a bounded pullback.",
        "falsifiableHypothesis": "Net expectancy is positive after costs on preregistered development folds.",
        "invalidationConditions": ["averageNetR <= 0", "profitFactor < 1.05"],
        "timeframe": "1h",
        "direction": "both",
        "requiredData": ["ohlcv", "fees", "funding", "point_in_time_universe"],
        "exitPolicy": {"policyId": "exit_atr_trailing_v1", "version": 1},
        "sourceArtifactHashes": ["source:abc"],
    }


def _experiment() -> dict:
    return {
        "experimentId": "experiment_001",
        "candidateId": "candidate_001",
        "parentStrategyId": "parent_001",
        "changedVariable": "pullbackAtrMaximum",
        "beforeValue": 1.2,
        "afterValue": 1.0,
        "lockedOosRead": False,
        "gateRelaxation": False,
    }


def test_v2_state_machine_requires_real_trials_and_formal_evidence(tmp_path: Path) -> None:
    factory = StrategyFactoryV2(tmp_path / "factory.sqlite")
    try:
        run = factory.create_run(
            run_id="run_001",
            campaign_id="campaign_001",
            hypothesis_draft=_hypothesis(),
        )
        assert run["state"] == "hypothesis_draft"
        assert run["completedTrialCount"] == 0

        factory.validate_hypothesis("run_001")
        factory.record_data_readiness(
            "run_001",
            snapshot_id="snapshot_001",
            status="ready",
            blockers=[],
        )
        factory.build_candidate(
            "run_001",
            candidate_id="candidate_001",
            candidate_definition_hash="candidate:def:001",
        )
        factory.queue_trial("run_001", _experiment())
        factory.start_trial("run_001", "experiment_001")

        with pytest.raises(StrategyFactoryV2Error, match="completed_trial_required"):
            factory.complete_development("run_001")

        factory.complete_trial(
            "run_001",
            "experiment_001",
            result={"status": "failed", "averageNetR": -0.08, "profitFactor": 0.91},
        )
        development = factory.complete_development("run_001")
        assert development["state"] == "development_complete"
        assert development["completedTrialCount"] == 1

        factory.queue_formal("run_001", job_hash="formal_job:001")
        factory.claim_formal("run_001", claim_hash="formal_claim:001")
        factory.start_formal("run_001", attempt_hash="formal_attempt:001")
        factory.complete_formal("run_001", result_hash="formal_result:001", survivor_count=0)
        formal = factory.read_formal_result("run_001", read_hash="formal_read:001")
        assert formal["state"] == "formal_complete"
        assert formal["formalEvidence"] == {
            "job": 1,
            "claim": 1,
            "attempt": 1,
            "result": 1,
            "read": 1,
        }
        assert formal["survivorCount"] == 0
    finally:
        factory.close()


def test_v2_rejects_fake_completion_states_and_multi_variable_tuning(tmp_path: Path) -> None:
    factory = StrategyFactoryV2(tmp_path / "factory.sqlite")
    try:
        factory.create_run(
            run_id="run_002",
            campaign_id="campaign_002",
            hypothesis_draft=_hypothesis(),
        )
        with pytest.raises(StrategyFactoryV2Error, match="unsupported_state"):
            factory.transition("run_002", "awaiting_formal_validation")

        factory.validate_hypothesis("run_002")
        factory.record_data_readiness(
            "run_002", snapshot_id="snapshot_002", status="ready", blockers=[]
        )
        factory.build_candidate(
            "run_002",
            candidate_id="candidate_002",
            candidate_definition_hash="candidate:def:002",
        )
        invalid = {
            **_experiment(),
            "experimentId": "experiment_002",
            "candidateId": "candidate_002",
            "changedVariables": ["pullbackAtrMaximum", "rsiMaximum"],
        }
        with pytest.raises(StrategyFactoryV2Error, match="one_variable_at_a_time"):
            factory.queue_trial("run_002", invalid)
    finally:
        factory.close()


def test_failure_tree_and_negative_memory_are_durable(tmp_path: Path) -> None:
    path = tmp_path / "factory.sqlite"
    factory = StrategyFactoryV2(path)
    try:
        factory.create_run(
            run_id="run_003",
            campaign_id="campaign_003",
            hypothesis_draft=_hypothesis(),
        )
        failure = factory.record_failure(
            "run_003",
            {
                "failureLayer": "Cost / Capacity",
                "facts": ["Cost-stressed average net R was -0.11."],
                "inferences": ["Turnover is likely too high for the observed edge."],
                "repairability": "bounded_single_variable_experiment",
                "prohibitedRepair": ["lower_cost_gate_after_result", "locked_oos_tuning"],
                "nextExperiment": "Increase minimum holding period only.",
                "changedVariable": "minimumHoldingBars",
                "parentStrategy": "candidate_003",
                "familyFingerprint": "family_fp_trend_recovery_v1",
                "signalCorrelation": 0.82,
            },
        )
        assert failure["failureLayer"] in FAILURE_LAYERS
        memory = factory.negative_memory(family_fingerprint="family_fp_trend_recovery_v1")
        assert len(memory) == 1
        assert memory[0]["prohibitedRepeats"] == [
            "locked_oos_tuning",
            "lower_cost_gate_after_result",
        ]
    finally:
        factory.close()

    reopened = StrategyFactoryV2(path)
    try:
        assert reopened.get_run("run_003")["failureCount"] == 1
        assert len(reopened.negative_memory()) == 1
    finally:
        reopened.close()
