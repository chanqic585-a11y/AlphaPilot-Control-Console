"""Deterministic task routing with an explicit execution-authority denylist."""

from __future__ import annotations

from .contracts import AIRequest, TaskRoute
from .errors import ForbiddenAITaskError, ToolPolicyError


FORBIDDEN_TASK_TYPES = frozenset(
    {
        "signal_decision",
        "risk_decision",
        "order_creation",
        "order_submission",
        "order_cancel",
        "position_management",
        "exit_decision",
        "reconciliation",
        "kill_switch",
        "approval",
        "arm",
        "withdraw",
    }
)

FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "place_order",
        "create_order",
        "cancel_order",
        "close_position",
        "modify_position",
        "set_leverage",
        "approve_release",
        "arm_runtime",
        "kill_switch",
        "withdraw",
        "transfer_funds",
    }
)

RESEARCH_TOOL_ALLOWLIST = frozenset(
    {
        "read_research_artifact",
        "read_factor_registry",
        "read_failure_memory",
        "read_market_summary",
        "read_backtest_summary",
        "search_public_research",
    }
)


class AITaskRouter:
    def route(self, request: AIRequest) -> TaskRoute:
        task_type = request.task_type.strip().lower()
        if task_type in FORBIDDEN_TASK_TYPES:
            raise ForbiddenAITaskError(f"LLM use is forbidden for task type: {task_type}")
        for tool_name in request.tool_names:
            normalized = tool_name.strip().lower()
            if normalized in FORBIDDEN_TOOL_NAMES or normalized not in RESEARCH_TOOL_ALLOWLIST:
                raise ToolPolicyError(f"AI tool is not research-allowlisted: {tool_name}")

        if task_type == "strategy_hypothesis":
            return TaskRoute(
                mode="dual",
                model_aliases=("deepseek_reasoning_primary", "gemini_reasoning_primary"),
                critical_fields=("mechanism", "marketScope", "timeframe", "direction"),
                requires_human_on_disagreement=True,
            )
        if task_type == "failure_attribution":
            return TaskRoute(
                mode="dual",
                model_aliases=("deepseek_reasoning_primary", "gemini_reasoning_primary"),
                critical_fields=("failureLayer", "repairability"),
                requires_human_on_disagreement=True,
            )
        if task_type in {"architecture_review", "security_review"}:
            return TaskRoute(
                mode="dual",
                model_aliases=("deepseek_reasoning_critical", "gemini_reasoning_primary"),
                critical_fields=("severity", "disposition"),
                requires_human_on_disagreement=True,
            )
        if task_type == "document_analysis" or request.multimodal:
            return TaskRoute(
                mode="dual",
                model_aliases=("gemini_multimodal_primary", "deepseek_reasoning_primary"),
                critical_fields=("evidenceStatus",),
                requires_human_on_disagreement=True,
            )
        if task_type == "code_review" or request.coding:
            return TaskRoute(
                mode="dual",
                model_aliases=("deepseek_coding_primary", "gemini_reasoning_primary"),
                critical_fields=("severity", "disposition"),
                requires_human_on_disagreement=True,
            )
        if task_type == "historical_batch":
            return TaskRoute(mode="batch", model_aliases=("gemini_batch",))
        if task_type == "provider_smoke_deepseek":
            return TaskRoute(mode="single", model_aliases=("deepseek_fast",))
        if task_type == "provider_smoke_gemini":
            return TaskRoute(mode="single", model_aliases=("gemini_fast",))
        if task_type == "provider_smoke_dual":
            return TaskRoute(
                mode="dual",
                model_aliases=("deepseek_fast_reasoning", "gemini_fast"),
                critical_fields=("evidenceStatus", "executionIntent"),
                requires_human_on_disagreement=True,
            )
        if task_type in {
            "research_summary",
            "factor_summary",
            "forward_evidence_summary",
            "ui_explanation",
        }:
            return TaskRoute(
                mode="single",
                model_aliases=("deepseek_fast",),
                fallback_model_aliases=("gemini_fast",),
            )
        raise ForbiddenAITaskError(f"AI task type is not registered: {task_type}")
