from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from alphapilot_control_console.ai_orchestration.contracts import OrchestrationResult
from alphapilot_control_console.strategy_factory_v2 import (
    AIResearchGovernor,
    StrategyFactoryReviewRequired,
    StrategyFactoryV2,
)


@dataclass
class FakeAIService:
    outputs: list[dict]

    def __post_init__(self) -> None:
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        output = self.outputs.pop(0)
        return OrchestrationResult(
            request_id=request.request_id,
            status=output.pop("_status", "accepted"),
            output=output,
            response_hashes=("ai:deepseek", "ai:gemini"),
            disagreements=tuple(output.pop("_disagreements", ())),
            execution_authorized=False,
            route_mode="dual",
        )


def _hypothesis_output() -> dict:
    return {
        "hypothesisId": "hypothesis_001",
        "familyId": "funding_basis_reversion",
        "familyFingerprint": "family_fp_funding_basis_v1",
        "mechanism": "Extreme funding and basis can mean revert after liquidity normalizes.",
        "falsifiableHypothesis": "Net expectancy is positive after fees, slippage and funding.",
        "invalidationConditions": ["averageNetR <= 0", "unstable across regimes"],
        "timeframe": "1h",
        "direction": "both",
        "requiredData": ["ohlcv", "funding", "basis", "fees", "slippage"],
        "exitPolicy": {"policyId": "exit_basis_normalization_v1", "version": 1},
        "sourceArtifactHashes": ["source:registry", "source:failure-memory"],
    }


def _failure_output() -> dict:
    return {
        "failureLayer": "Stability / Regime",
        "facts": ["The candidate failed two preregistered volatility regimes."],
        "inferences": ["The signal may need a single volatility-state condition."],
        "repairability": "bounded_single_variable_experiment",
        "prohibitedRepair": ["read_locked_oos", "relax_gate_after_result"],
        "nextExperiment": "Add one preregistered volatility state condition.",
        "changedVariable": "volatilityState",
        "parentStrategy": "candidate_001",
        "familyFingerprint": "family_fp_funding_basis_v1",
        "signalCorrelation": 0.71,
        "sourceArtifactHashes": ["source:trial-result"],
    }


def test_governor_uses_dual_research_tasks_and_never_authorizes_execution(
    tmp_path: Path,
) -> None:
    service = FakeAIService([_hypothesis_output(), _failure_output()])
    factory = StrategyFactoryV2(tmp_path / "factory.sqlite")
    governor = AIResearchGovernor(ai_service=service, factory=factory)
    try:
        draft = governor.draft_hypothesis(
            campaign_id="campaign_001",
            source_material={"registry": "source:registry"},
            artifact_hashes=("source:registry", "source:failure-memory"),
        )
        assert draft["executionAuthorized"] is False
        assert service.requests[0].task_type == "strategy_hypothesis"
        assert service.requests[0].dual_review is True
        assert service.requests[0].tool_names == ()

        failure = governor.attribute_failure(
            run_id="run_missing_is_allowed_for_draft",
            trial_result={"averageNetR": -0.2},
            artifact_hashes=("source:trial-result",),
            persist=False,
        )
        assert failure["executionAuthorized"] is False
        assert service.requests[1].task_type == "failure_attribution"
        assert service.requests[1].dual_review is True
    finally:
        factory.close()


def test_governor_stops_when_independent_models_disagree(tmp_path: Path) -> None:
    output = _hypothesis_output()
    output.update(
        {
            "_status": "human_review_required",
            "_disagreements": ("falsifiableHypothesis",),
        }
    )
    service = FakeAIService([output])
    factory = StrategyFactoryV2(tmp_path / "factory.sqlite")
    governor = AIResearchGovernor(ai_service=service, factory=factory)
    try:
        with pytest.raises(StrategyFactoryReviewRequired, match="independent_review"):
            governor.draft_hypothesis(
                campaign_id="campaign_002",
                source_material={},
                artifact_hashes=("source:registry",),
            )
    finally:
        factory.close()


def test_governor_includes_negative_memory_before_new_hypothesis(tmp_path: Path) -> None:
    service = FakeAIService([_hypothesis_output()])
    factory = StrategyFactoryV2(tmp_path / "factory.sqlite")
    try:
        factory.create_run(
            run_id="prior_run",
            campaign_id="prior_campaign",
            hypothesis_draft=_hypothesis_output(),
        )
        factory.record_failure(
            "prior_run",
            {
                **_failure_output(),
                "prohibitedRepair": ["read_locked_oos"],
            },
        )
        governor = AIResearchGovernor(ai_service=service, factory=factory)
        governor.draft_hypothesis(
            campaign_id="campaign_003",
            source_material={},
            artifact_hashes=("source:registry", "source:failure-memory"),
        )
        payload = service.requests[0].payload
        assert payload["negativeResearchMemory"][0]["familyFingerprint"] == (
            "family_fp_funding_basis_v1"
        )
    finally:
        factory.close()
