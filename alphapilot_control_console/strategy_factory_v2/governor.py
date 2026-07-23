from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol
from uuid import uuid4

from ..ai_orchestration.contracts import AIRequest, OrchestrationResult
from .errors import StrategyFactoryReviewRequired
from .ledger import StrategyFactoryV2
from .schemas import FAILURE_RESPONSE_SCHEMA, HYPOTHESIS_RESPONSE_SCHEMA


class _AIService(Protocol):
    def execute(self, request: AIRequest) -> OrchestrationResult: ...


class AIResearchGovernor:
    """Research-only bridge. AI drafts never authorize experiments or execution."""

    def __init__(self, *, ai_service: _AIService, factory: StrategyFactoryV2) -> None:
        self.ai_service = ai_service
        self.factory = factory

    def draft_hypothesis(
        self,
        *,
        campaign_id: str,
        source_material: Mapping[str, Any],
        artifact_hashes: Sequence[str],
    ) -> dict[str, Any]:
        result = self.ai_service.execute(
            AIRequest(
                request_id=f"strategy-hypothesis-{uuid4().hex}",
                task_type="strategy_hypothesis",
                payload={
                    "sourceMaterial": dict(source_material),
                    "negativeResearchMemory": self.factory.negative_memory(),
                    "constraints": {
                        "oneVariableAtATime": True,
                        "lockedOosTuningAllowed": False,
                        "gateRelaxationAfterResultsAllowed": False,
                        "automaticPromotionAllowed": False,
                    },
                },
                response_schema=HYPOTHESIS_RESPONSE_SCHEMA,
                sensitivity="internal",
                prompt_version="strategy-hypothesis-v1",
                artifact_hashes=tuple(artifact_hashes),
                tool_names=(),
                quant_research=True,
                dual_review=True,
                human_review_required=True,
                cost_ceiling_usd=2.0,
                token_ceiling=8_192,
                metadata={"researchCampaignId": campaign_id},
            )
        )
        self._require_independent_acceptance(result)
        return {
            "schemaVersion": "strategy_factory_hypothesis_draft_v2",
            "draft": dict(result.output),
            "responseHashes": list(result.response_hashes),
            "executionAuthorized": False,
        }

    def attribute_failure(
        self,
        *,
        run_id: str,
        trial_result: Mapping[str, Any],
        artifact_hashes: Sequence[str],
        persist: bool = True,
    ) -> dict[str, Any]:
        result = self.ai_service.execute(
            AIRequest(
                request_id=f"failure-attribution-{uuid4().hex}",
                task_type="failure_attribution",
                payload={
                    "runId": run_id,
                    "trialResult": dict(trial_result),
                    "failureTree": [
                        "Implementation",
                        "Data / PIT",
                        "Signal Edge",
                        "Cost / Capacity",
                        "Stability / Regime",
                        "Risk / Portfolio",
                        "Promotion / Execution",
                    ],
                    "constraints": {
                        "factInferenceSeparation": True,
                        "oneVariableAtATime": True,
                        "lockedOosTuningAllowed": False,
                    },
                },
                response_schema=FAILURE_RESPONSE_SCHEMA,
                sensitivity="internal",
                prompt_version="failure-attribution-v1",
                artifact_hashes=tuple(artifact_hashes),
                tool_names=(),
                quant_research=True,
                dual_review=True,
                human_review_required=True,
                cost_ceiling_usd=2.0,
                token_ceiling=8_192,
                metadata={"researchCampaignId": run_id},
            )
        )
        self._require_independent_acceptance(result)
        payload = dict(result.output)
        persisted = self.factory.record_failure(run_id, payload) if persist else payload
        return {
            "schemaVersion": "strategy_factory_failure_attribution_v2",
            "attribution": persisted,
            "responseHashes": list(result.response_hashes),
            "executionAuthorized": False,
        }

    @staticmethod
    def _require_independent_acceptance(result: OrchestrationResult) -> None:
        if result.status != "accepted" or result.disagreements:
            raise StrategyFactoryReviewRequired("blocked_waiting_independent_review")
        if result.route_mode != "dual" or len(result.response_hashes) != 2:
            raise StrategyFactoryReviewRequired("independent_review_incomplete")
        if result.execution_authorized:
            raise StrategyFactoryReviewRequired("AI_execution_authority_forbidden")
