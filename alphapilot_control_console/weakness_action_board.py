from __future__ import annotations

from typing import Any

from .config import SAFETY_BOUNDARY
from .simulation_replay import build_closed_sample_replay


CONTROL_CONSOLE_VERSION = "V13.7.48"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_48"

ACTION_RECIPES: dict[str, dict[str, Any]] = {
    "deep_adverse_excursion": {
        "label": "回撤过深",
        "recommendedAction": "降低回撤暴露，优先检查入场过滤和止损距离。",
        "researchTasks": [
            "复查触发前 20 根 K 线的趋势和波动状态。",
            "对比 MAE 超过 -2R 的样本是否集中在同一资产或市场状态。",
            "测试更严格的入场确认或更早失效条件，但不得放宽 2R 目标。",
        ],
    },
    "holding_too_long": {
        "label": "持有过久",
        "recommendedAction": "研究时间退出规则，避免样本在低效率区间里耗损。",
        "researchTasks": [
            "统计持有时间超过 24 小时的样本与最终 R 的关系。",
            "测试固定时间退出或动能衰减退出规则。",
            "检查长持有样本是否带来更高回撤或更低 MFE 兑现率。",
        ],
    },
    "stop_loss_like": {
        "label": "止损型亏损",
        "recommendedAction": "定位止损型亏损集中条件，先做过滤而不是加仓或放大风险。",
        "researchTasks": [
            "按资产、周期、方向和 BTC regime 拆分止损型亏损。",
            "检查亏损样本触发前是否存在趋势反向或成交量衰减。",
            "把止损型亏损样本加入负样本库，训练后续过滤器。",
        ],
    },
    "profit_not_captured": {
        "label": "利润未兑现",
        "recommendedAction": "研究 MFE 兑现和移动止盈，避免有利波动回吐。",
        "researchTasks": [
            "筛选 MFE >= 2R 但最终 < 1R 的样本。",
            "测试分段兑现、移动止盈或时间衰减退出。",
            "对比固定 2R 目标与路径内最高 MFE 的差距。",
        ],
    },
    "weak_favorable_path": {
        "label": "有利波动不足",
        "recommendedAction": "提高触发阈值或增加动量确认，减少低质量触发。",
        "researchTasks": [
            "检查 MFE < 0.8R 的样本是否来自弱趋势或低成交量环境。",
            "增加突破强度、RSI/MACD 或成交量确认作为研究过滤器。",
            "把弱有利波动样本作为候选策略降权依据。",
        ],
    },
    "cost_drag_high": {
        "label": "成本拖累",
        "recommendedAction": "降低交易频率或提高目标空间，确保费用和滑点不会吞噬 2R 结构。",
        "researchTasks": [
            "统计 fee/slippage 超过 0.2R 的资产和周期。",
            "排查低流动性资产是否贡献主要成本拖累。",
            "测试最小 ATR、最小成交量和最小目标空间过滤。",
        ],
    },
    "path_missing": {
        "label": "路径字段不足",
        "recommendedAction": "补齐路径字段，先提升复盘质量，不做策略晋级。",
        "researchTasks": [
            "补齐 entry/exit price、MFE、MAE、fee/slippage 和 holding time。",
            "确认样本是否有唯一 sampleKey，避免重复样本污染。",
            "字段补齐前不允许进入 testnet 或实盘准备。",
        ],
    },
    "flat_or_small_loss": {
        "label": "小亏或持平",
        "recommendedAction": "检查无效触发和低效率样本，优先减少无意义观察。",
        "researchTasks": [
            "拆分小亏样本的市场状态和触发原因。",
            "检查是否需要更强趋势过滤或更少交易频率。",
            "把小亏样本纳入策略健康趋势，而不是单独放大解释。",
        ],
    },
    "stop_area_touched": {
        "label": "接近止损区",
        "recommendedAction": "研究入场时机和止损位置，避免刚触发就贴近风险区。",
        "researchTasks": [
            "统计 MAE 在 -1R 到 -2R 的样本是否最终仍能到达 2R。",
            "对比更晚确认入场与当前触发入场的路径差异。",
            "检查止损距离是否与波动率不匹配。",
        ],
    },
}

DEFAULT_RECIPE = {
    "label": "未归类弱点",
    "recommendedAction": "先保留为人工复盘任务，等样本更多后再归类。",
    "researchTasks": [
        "复查相关样本的路径、成本和市场状态。",
        "确认该弱点是否重复出现，避免根据单个样本改策略。",
    ],
}


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed else fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _severity_weight(severity: str) -> int:
    if severity == "danger":
        return 38
    if severity == "warning":
        return 22
    return 10


def _priority_label(score: float) -> str:
    if score >= 75:
        return "高优先级"
    if score >= 50:
        return "中优先级"
    return "观察"


def _priority_tone(score: float) -> str:
    if score >= 75:
        return "danger"
    if score >= 50:
        return "warn"
    return "ok"


def _blocked_reason(severity: str, average_score: float, code: str) -> str | None:
    if code == "path_missing":
        return "路径字段不足，禁止升级到 testnet 或实盘。"
    if severity == "danger":
        return "存在 danger 级弱点，必须先完成复盘行动。"
    if average_score < 55:
        return "平均复盘分不足 55，策略仍处于研究修复阶段。"
    return None


def _collect_action_rows(strategy: dict[str, Any]) -> list[dict[str, Any]]:
    score_summary = strategy.get("scoreSummary") if isinstance(strategy.get("scoreSummary"), dict) else {}
    labels = score_summary.get("topWeaknessLabels") if isinstance(score_summary.get("topWeaknessLabels"), list) else []
    average_score = _safe_float(score_summary.get("averageReviewScore"), 0.0)
    sample_count = _safe_int(strategy.get("representativeSampleCount"))
    rows: list[dict[str, Any]] = []
    for label in labels:
        if not isinstance(label, dict):
            continue
        code = str(label.get("code") or "").strip()
        if not code:
            continue
        recipe = ACTION_RECIPES.get(code, DEFAULT_RECIPE)
        severity = str(label.get("severity") or "warning")
        count = _safe_int(label.get("count"), 0)
        blocked_reason = _blocked_reason(severity, average_score, code)
        priority_score = min(
            100.0,
            _severity_weight(severity)
            + count * 12
            + max(0.0, 65.0 - average_score) * 0.45
            + (12 if blocked_reason else 0)
            + (8 if sample_count >= 5 else 0),
        )
        rows.append({
            "actionId": f"{strategy.get('taskId') or strategy.get('strategyId') or 'unknown'}::{code}",
            "strategyId": strategy.get("strategyId"),
            "taskId": strategy.get("taskId"),
            "strategyName": strategy.get("strategyName") or strategy.get("taskId") or "--",
            "timeframe": strategy.get("timeframe"),
            "weaknessCode": code,
            "weaknessLabel": label.get("label") or recipe["label"],
            "severity": severity,
            "weaknessCount": count,
            "sampleCount": sample_count,
            "averageReviewScore": round(average_score, 2),
            "priorityScore": round(priority_score, 2),
            "priorityLabel": _priority_label(priority_score),
            "priorityTone": _priority_tone(priority_score),
            "recommendedAction": recipe["recommendedAction"],
            "researchTasks": recipe["researchTasks"],
            "blockedUpgrade": blocked_reason is not None,
            "blockedUpgradeReason": blocked_reason or "可以继续观察，但仍不能自动升级或创建订单。",
            "safetyNote": "行动项只用于本地研究修复，不是交易信号，不会创建订单。",
        })
    return rows


def build_weakness_action_board(limit: int = 200) -> dict[str, Any]:
    replay = build_closed_sample_replay(limit=limit)
    strategies = replay.get("strategies") if isinstance(replay.get("strategies"), list) else []
    actions = [
        action
        for strategy in strategies
        if isinstance(strategy, dict)
        for action in _collect_action_rows(strategy)
    ]
    actions.sort(key=lambda row: (-_safe_float(row.get("priorityScore")), str(row.get("strategyName") or "")))
    top_action = actions[0] if actions else None
    critical_count = sum(1 for row in actions if row.get("priorityTone") == "danger")
    warning_count = sum(1 for row in actions if row.get("priorityTone") == "warn")
    blocked_count = sum(1 for row in actions if row.get("blockedUpgrade"))
    summary = {
        "totalActions": len(actions),
        "criticalActionCount": critical_count,
        "warningActionCount": warning_count,
        "blockedUpgradeCount": blocked_count,
        "strategyCount": len(strategies),
        "topPriorityAction": top_action,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "nextAction": (
            "优先处理高优先级弱点行动；所有行动项只用于研究修复，"
            "不会自动进入 Dry-run、testnet 或实盘。"
        ),
    }
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "summary": summary,
        "actions": actions,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Weakness action board is local research only. It does not connect exchange APIs, read accounts, or create orders.",
    }
