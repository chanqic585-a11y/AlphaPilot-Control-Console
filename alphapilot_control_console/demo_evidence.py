"""Build persistent operator-facing evidence for the OKX Demo workflow."""

from __future__ import annotations

from typing import Any

from .advisory_r_exit_policy import (
    is_advisory_definition,
    validate_definition_exit_policy,
)

REVIEW_START_SAMPLES = 30


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _evidence(
    evidence_id: str,
    label: str,
    *,
    status: str,
    current: Any,
    target: Any,
    source_type: str,
    blocking: bool,
    detail: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "evidenceId": evidence_id,
        "label": label,
        "status": status,
        "current": current,
        "target": target,
        "sourceType": source_type,
        "blocking": blocking,
        "detail": detail,
        "nextAction": next_action,
    }


def _strategy_definition(lifecycle_item: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    optimization = _mapping(lifecycle_item.get("optimizationContext"))
    return _mapping(optimization.get("definition")), _mapping(optimization.get("parameters"))


def _target_r(definition: dict[str, Any], parameters: dict[str, Any]) -> float:
    return _number(
        definition.get("targetR")
        or parameters.get("targetRewardRiskRatio")
        or parameters.get("targetR")
    )


def _definition_complete(definition: dict[str, Any], parameters: dict[str, Any]) -> bool:
    required = (
        str(definition.get("family") or "").strip(),
        str(definition.get("direction") or "").strip(),
        str(definition.get("timeframe") or "").strip(),
    )
    if not all(required) or not parameters:
        return False
    if not is_advisory_definition(definition):
        return True
    try:
        validate_definition_exit_policy(definition)
    except ValueError:
        return False
    return True


def _advisory_policy(definition: dict[str, Any]) -> dict[str, Any] | None:
    if not is_advisory_definition(definition):
        return None
    try:
        return validate_definition_exit_policy(definition)
    except ValueError:
        return None


def build_demo_evidence_checklist(
    lifecycle_item: dict[str, Any],
    *,
    contract: dict[str, Any] | None,
    runtime: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return the same evidence categories even when values are still missing."""

    metrics = _mapping(lifecycle_item.get("metrics"))
    definition, parameters = _strategy_definition(lifecycle_item)
    runtime = _mapping(runtime)
    contract = _mapping(contract)
    trade_count = int(_number(metrics.get("tradeCount")))
    closed_samples = int(_number(metrics.get("closedSamples")))
    closed_demo_trades = (
        0
        if str(runtime.get("evidenceClass") or "") == "demo_engineering_smoke"
        else int(_number(runtime.get("closedTradeCount")))
    )
    target_r = _target_r(definition, parameters)
    advisory_definition = is_advisory_definition(definition)
    exit_policy = _advisory_policy(definition)
    exit_policy_complete = exit_policy is not None
    override = str(contract.get("releaseMode") or "") == "experimental_override"
    release_exists = bool(contract.get("demoReleaseId"))
    candidate_exists = bool(contract.get("strategyCandidateId"))
    runtime_ready = bool(runtime.get("automationReady"))

    items = [
        _evidence(
            "formal_backtest",
            "正式回测",
            status="passed" if trade_count > 0 else "missing",
            current=trade_count,
            target="> 0 笔正式回测交易",
            source_type="automatic",
            blocking=trade_count <= 0,
            detail="系统自动读取已登记的正式回测结果。",
            next_action="已有正式回测证据。" if trade_count > 0 else "返回策略页完成正式回测。",
        ),
        _evidence(
            "target_reward_risk",
            "退出策略完整性" if advisory_definition else "目标盈亏比",
            status=(
                "passed"
                if (exit_policy_complete if advisory_definition else target_r > 0)
                else "missing"
            ),
            current=(exit_policy.get("mode") if exit_policy else "缺失") if advisory_definition else target_r,
            target="完整且不可变的 Exit Policy" if advisory_definition else ">= 2R",
            source_type="automatic",
            blocking=not exit_policy_complete if advisory_definition else target_r <= 0,
            detail=(
                "系统自动校验 Exit Policy 内容、不可放宽初始止损规则和内容哈希。"
                if advisory_definition
                else "系统自动读取不可变策略定义中的目标 R。"
            ),
            next_action=(
                "Exit Policy 已完整冻结。"
                if exit_policy_complete
                else "补齐并重新冻结 Exit Policy 及其哈希。"
            ) if advisory_definition else (
                "目标 R 已达标。" if target_r >= 2.0 else "创建目标不低于 2R 的新策略版本。"
            ),
        ),
        _evidence(
            "strategy_definition",
            "完整策略定义",
            status="passed" if _definition_complete(definition, parameters) else "missing",
            current="完整" if _definition_complete(definition, parameters) else "缺字段",
            target="家族、方向、周期和参数完整",
            source_type="automatic",
            blocking=not _definition_complete(definition, parameters),
            detail="系统自动校验策略家族、方向、周期和参数。",
            next_action="策略定义完整。" if _definition_complete(definition, parameters) else "先补齐策略定义再重新回测。",
        ),
        _evidence(
            "local_forward_samples",
            "本地前向闭合样本",
            status=(
                "legacy_inactive"
                if override
                else ("passed" if closed_samples >= REVIEW_START_SAMPLES else "missing")
            ),
            current=closed_samples,
            target=REVIEW_START_SAMPLES,
            source_type="legacy_read_only" if override else "automatic",
            blocking=override or closed_samples < REVIEW_START_SAMPLES,
            detail=(
                "旧 experimental_override 仅保留为历史记录，不能再绕过证据或执行。"
                if override
                else "系统自动累计去重后的本地前向闭合样本。"
            ),
            next_action=(
                "为冻结组合生成新的精确 Hash Provisional Research Demo Release。"
                if override
                else (
                    "本地前向样本已达到复核起点。"
                    if closed_samples >= REVIEW_START_SAMPLES
                    else "返回本地模拟继续收集闭合样本，或使用受控 Demo-only 放行。"
                )
            ),
        ),
        _evidence(
            "formal_strategy_candidate",
            "正式策略候选登记",
            status="passed" if candidate_exists else "missing",
            current=contract.get("strategyCandidateId") or "未登记",
            target="不可变候选 ID",
            source_type="automatic",
            blocking=not candidate_exists,
            detail="系统自动读取 Demo Release 绑定的策略候选身份。",
            next_action="候选身份已登记。" if candidate_exists else "完成正式证据或受控放行后自动登记。",
        ),
        _evidence(
            "immutable_demo_release",
            "不可变 Demo Release",
            status=(
                "legacy_inactive"
                if override
                else ("passed" if release_exists else "missing")
            ),
            current=contract.get("demoReleaseId") or "未生成",
            target="校验通过的不可变 Release",
            source_type="legacy_read_only" if override else "automatic",
            blocking=override or not release_exists,
            detail=(
                "旧 Override Release 只读保留，不再具备执行资格。"
                if override
                else "系统自动校验 Release 内容哈希、风险包和 Demo-only 边界。"
            ),
            next_action=(
                "生成 Provisional Research Demo Release 并等待精确 Hash 批准。"
                if override
                else ("Demo Release 已存在。" if release_exists else "补齐证据后生成 Demo Release。")
            ),
        ),
        _evidence(
            "demo_runtime",
            "OKX Demo Runtime",
            status="passed" if runtime_ready else "pending",
            current="已就绪" if runtime_ready else "未就绪",
            target="凭据、只读、订单、自动化和风险闸门通过",
            source_type="manual_runtime",
            blocking=release_exists and not runtime_ready,
            detail="Runtime 凭据只存在于当前进程，不写入本地状态。",
            next_action="Runtime 已就绪。" if runtime_ready else "用 OKX Demo 启动器启动并完成运行前检查。",
        ),
        _evidence(
            "demo_closed_trades",
            "Demo 闭合交易",
            status="passed" if closed_demo_trades > 0 else "pending",
            current=closed_demo_trades,
            target="> 0 笔后开始复盘",
            source_type="automatic",
            blocking=False,
            detail="系统自动从 Demo 执行账本累计真实闭合模拟交易。",
            next_action="继续 Demo 复盘。" if closed_demo_trades > 0 else "运行 Demo 周期并等待真实条件匹配。",
        ),
    ]
    if not advisory_definition:
        target_evidence = next(item for item in items if item["evidenceId"] == "target_reward_risk")
        target_evidence["target"] = "Versioned positive exit target"
        target_evidence["nextAction"] = (
            "Versioned exit target is valid."
            if target_r > 0
            else "Create a new strategy version with an explicit positive exit target."
        )
    return {
        "items": items,
        "summary": {
            "passedCount": sum(item["status"] in {"passed", "bypassed"} for item in items),
            "blockingCount": sum(bool(item["blocking"]) for item in items),
            "automaticCount": sum(item["sourceType"] == "automatic" for item in items),
            "manualCount": sum(item["sourceType"] == "manual_runtime" for item in items),
            "overrideActive": False,
            "legacyOverrideDetected": override,
        },
    }
