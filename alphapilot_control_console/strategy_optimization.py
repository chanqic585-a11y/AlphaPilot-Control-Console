"""Explainable parameter optimization contexts for immutable strategy versions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


TARGET_R_KEYS = {"targetR", "targetRMultiple", "targetRewardRiskRatio"}
PARAMETER_LABELS = {
    "volume_min": "最小成交量倍数",
    "minVolumeRatio": "最小成交量倍数",
    "rsi_high": "RSI 高位阈值",
    "rsiMin": "RSI 最低阈值",
    "upper_buffer": "上影拒绝缓冲",
    "breakoutMultiplier": "突破确认倍数",
    "max_hold": "最长持有 K 线",
    "maxHoldBars": "最长持有 K 线",
    "horizonBars": "观察持有 K 线",
    "targetR": "目标盈亏比",
    "targetRMultiple": "目标盈亏比",
    "targetRewardRiskRatio": "目标盈亏比",
}


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed else None


def _first_number(rows: list[dict[str, Any]], *keys: str) -> float | None:
    for row in rows:
        for key in keys:
            value = _number(row.get(key))
            if value is not None:
                return value
    return None


def validate_optimization_parameters(
    definition: dict[str, Any],
    base_parameters: dict[str, Any],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(definition, dict):
        raise ValueError("strategy_definition_required")
    if not isinstance(base_parameters, dict) or not isinstance(parameters, dict):
        raise ValueError("strategy_parameters_required")
    if base_parameters == parameters:
        raise ValueError("optimized_parameters_unchanged")
    target_values: list[float] = []
    for container in (definition, parameters):
        for key in TARGET_R_KEYS:
            if key not in container:
                continue
            value = _number(container[key])
            if value is None:
                raise ValueError("target_r_must_be_numeric")
            target_values.append(value)
    if not target_values:
        raise ValueError("target_r_required")
    if min(target_values) <= 0:
        raise ValueError("target_r_must_be_positive")
    return deepcopy(parameters)


def _record_change(
    changes: dict[str, dict[str, Any]],
    proposed: dict[str, Any],
    key: str,
    value: Any,
    reason: str,
) -> None:
    current = proposed.get(key)
    if current == value:
        return
    proposed[key] = value
    changes[key] = {
        "key": key,
        "label": PARAMETER_LABELS.get(key, key),
        "currentValue": current,
        "proposedValue": value,
        "reason": reason,
    }


def build_optimization_context(item: dict[str, Any]) -> dict[str, Any]:
    raw = item.get("optimizationContext") if isinstance(item.get("optimizationContext"), dict) else {}
    definition = deepcopy(raw.get("definition") if isinstance(raw.get("definition"), dict) else {})
    base = deepcopy(raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {})
    proposed = deepcopy(base)
    failure = item.get("failure") if isinstance(item.get("failure"), dict) else {}
    category = str(failure.get("category") or "").strip()
    current_stage = str(item.get("currentStage") or item.get("stage") or "backtest")
    metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    validation_metrics = raw.get("validationMetrics") if isinstance(raw.get("validationMetrics"), dict) else {}
    test_metrics = raw.get("testMetrics") if isinstance(raw.get("testMetrics"), dict) else {}
    result = item.get("result") if isinstance(item.get("result"), dict) else {}
    result_metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    metric_priority = [validation_metrics, test_metrics, metrics, result_metrics]
    changes: dict[str, dict[str, Any]] = {}
    recommendations: list[str] = []

    if category == "data_integrity":
        recommendations.append("先补齐正式数据快照和防泄漏验证证据，再重新回测；当前不应猜测或改动策略参数。")
        recommendations.extend(str(row) for row in failure.get("suggestions") or [] if str(row).strip())
        recommendation_mode = "data_repair"
    else:
        profit_factor = _first_number(metric_priority, "profitFactor")
        if profit_factor is not None and profit_factor < 1.2:
            for key in ("volume_min", "minVolumeRatio", "rsi_high", "rsiMin", "upper_buffer", "breakoutMultiplier"):
                current = _number(proposed.get(key))
                if current is None:
                    continue
                if key in {"volume_min", "minVolumeRatio"}:
                    next_value = round(current + 0.1, 4)
                elif key in {"rsi_high", "rsiMin"}:
                    next_value = round(min(current + 2.0, 90.0), 4)
                elif key == "upper_buffer":
                    next_value = round(current + 0.001, 6)
                else:
                    next_value = round(current + 0.002, 6)
                _record_change(
                    changes,
                    proposed,
                    key,
                    next_value,
                    f"验证证据 PF {profit_factor:.2f} 低于 1.20，收紧已有入场质量阈值。",
                )
                break
        drawdown = _first_number(
            metric_priority,
            "maximumDrawdownR",
            "maxDrawdownR",
            "maxDrawdownPct",
            "maxDrawdownPctAt1PctRisk",
        )
        if drawdown is not None and drawdown > 10.0:
            for key in ("max_hold", "maxHoldBars", "horizonBars"):
                current = _number(proposed.get(key))
                if current is None:
                    continue
                next_value = max(1, int(round(current * 0.8)))
                _record_change(
                    changes,
                    proposed,
                    key,
                    next_value,
                    f"回撤 {drawdown:.2f} 超过 10，缩短已有持有期限以减少尾部暴露。",
                )
                break
        recommendations.extend(str(row) for row in failure.get("suggestions") or [] if str(row).strip())
        if changes:
            recommendations.insert(0, "建议只调整下列已有参数，并创建新版本重新完成回测、前向和 Demo 验证。")
            recommendation_mode = "parameter_quality"
        else:
            recommendations.insert(0, "现有证据没有形成可靠的自动参数建议；可以人工修改已登记参数，但必须创建新版本重新回测。")
            recommendation_mode = "manual_parameter_review"

    fields = []
    for key, value in base.items():
        if not isinstance(value, (str, int, float, bool)) or value is None:
            continue
        fields.append(
            {
                "key": key,
                "label": PARAMETER_LABELS.get(key, key),
                "currentValue": value,
                "proposedValue": proposed.get(key),
                "locked": key in TARGET_R_KEYS,
            }
        )
    return {
        "sourceKind": raw.get("sourceKind") or "unknown",
        "legacyStrategyId": raw.get("legacyStrategyId"),
        "parentStrategyVersionId": raw.get("parentStrategyVersionId"),
        "displayName": item.get("displayName") or "未命名策略",
        "currentStage": current_stage,
        "definition": definition,
        "parameters": base,
        "baseParameters": base,
        "proposedParameters": proposed,
        "parameterFields": fields,
        "changedFields": list(changes.values()),
        "recommendations": recommendations,
        "recommendationMode": recommendation_mode,
        "canAutoPropose": bool(changes),
        "targetRFloor": 2.0,
        "metrics": metrics,
        "validationMetrics": validation_metrics,
        "testMetrics": test_metrics,
    }
