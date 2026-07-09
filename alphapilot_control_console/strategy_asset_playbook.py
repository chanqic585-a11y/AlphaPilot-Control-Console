from __future__ import annotations

import json
from typing import Any

from .config import SAFETY_BOUNDARY
from .local_sandbox_quality_center import build_local_sandbox_quality_center
from .state_store import now_iso


CONTROL_CONSOLE_VERSION = "V13.8.8"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_8"
DEFAULT_TESTNET_BLOCKERS = [
    "Testnet credential isolation is not implemented.",
    "Order lifecycle simulator is not implemented.",
    "Kill switch is not implemented.",
    "Maximum order and loss limits are not implemented.",
    "Manual confirmation gate is not implemented.",
]


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


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _plain_family(name: str, timeframe: str | None) -> dict[str, Any]:
    text = f"{name} {timeframe or ''}".lower()
    if "空头上影拒绝" in name or "short_rejection" in text:
        return {
            "familyId": "short_rejection_1h",
            "familyName": "1h 上影拒绝短周期策略",
            "directionLabel": "偏空研究样本",
            "oneLine": "观察 1h 冲高回落后的拒绝形态，固定按 2R 口径记录结果。",
            "whenItWorks": [
                "适合在短周期冲高失败、上影明显、动能转弱时做研究观察。",
                "更适合用在样本足够、成交活跃、滑点可控的主流合约币种。",
                "需要继续复核 BTC 急跌、极端拉升和低流动性窗口。",
            ],
            "whenToAvoid": [
                "样本集中在少数币种或少数窗口时，不能升级。",
                "连续亏损扩大、数据缺口增加、信号来自低流动性币种时先暂停。",
                "不能把形态识别直接当成开仓指令。",
            ],
            "coreRules": [
                "先确认 1h 上影拒绝形态是否完整。",
                "只记录规则是否匹配、纸面 2R 结果、失败原因和风险备注。",
                "保持固定 2R 目标，不为了提高胜率随意降低目标。",
            ],
        }
    if "横盘超卖修复" in name or "oversold" in text:
        return {
            "familyId": "daily_oversold_repair",
            "familyName": "1D 横盘超卖修复策略",
            "directionLabel": "修复研究样本",
            "oneLine": "观察日线横盘后过度下跌的修复质量，重点看 2R 能否稳定闭合。",
            "whenItWorks": [
                "适合震荡或修复阶段，不适合强趋势追涨。",
                "需要 RSI、波动率和市场状态共同支持修复假设。",
                "更适合先做低频观察，补足多市场状态样本。",
            ],
            "whenToAvoid": [
                "BTC 处于急跌或系统性风险阶段时先降级观察。",
                "只有少数币种贡献表现时，先做集中度复核。",
                "不能把超卖状态解释成交易建议。",
            ],
            "coreRules": [
                "记录横盘结构、超卖状态和修复路径。",
                "优先补失败样本，避免只记录好看的修复。",
                "用本地沙盒继续检查回撤和连亏。",
            ],
        }
    if "低波突破" in name or "breakout" in text:
        return {
            "familyId": "daily_low_vol_breakout",
            "familyName": "1D 低波突破策略",
            "directionLabel": "突破研究样本",
            "oneLine": "观察日线低波动压缩后的突破延续，先验证跨币种和跨窗口稳定性。",
            "whenItWorks": [
                "适合趋势已经形成、波动短暂收缩后再扩张的阶段。",
                "需要成交和趋势过滤同时支持，避免假突破。",
                "适合作为资产筛选候选，而不是单币种指令。",
            ],
            "whenToAvoid": [
                "突破后回撤迅速扩大时先暂停。",
                "低成交量或 K 线缺口明显时不能升级。",
                "不能跳过前向样本直接进入实盘。",
            ],
            "coreRules": [
                "记录低波动压缩、突破确认和后续 2R 路径。",
                "同步记录失败突破和连续亏损。",
                "保持只读研究边界。",
            ],
        }
    if "趋势突破确认" in name or "trend" in text:
        return {
            "familyId": "daily_trend_confirmation",
            "familyName": "1D 趋势突破确认策略",
            "directionLabel": "趋势研究样本",
            "oneLine": "观察日线趋势突破后的确认样本，先看延续质量和回撤是否可控。",
            "whenItWorks": [
                "适合 BTC 处于 recovery 或 bull 状态，主流币趋势较清晰时。",
                "需要趋势、波动、成交和回撤共同验证。",
                "适合低频策略池继续沙盒观察。",
            ],
            "whenToAvoid": [
                "震荡阶段或假突破频繁时先降级。",
                "最大回撤 R 超过门槛时不能升级。",
                "不能把趋势判断当成买卖建议。",
            ],
            "coreRules": [
                "记录趋势结构、突破确认和失效位置。",
                "用固定 2R 结果闭合样本。",
                "先完成本地复核，再讨论 testnet 设计。",
            ],
        }
    return {
        "familyId": "general_research_candidate",
        "familyName": "通用研究候选策略",
        "directionLabel": "研究样本",
        "oneLine": "本策略已进入本地研究记录，但需要继续补足可解释规则和闭合样本。",
        "whenItWorks": [
            "适合继续收集本地沙盒样本。",
            "需要补充清晰规则、失败场景和风险说明。",
        ],
        "whenToAvoid": [
            "规则解释不清时不能升级。",
            "样本不足或风险未复核时不能进入 testnet。",
        ],
        "coreRules": [
            "补充策略条件说明。",
            "记录每次规则是否匹配和纸面结果。",
            "保留研究边界。",
        ],
    }


def _gate_by_task(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in (row.get("taskId"), row.get("strategyId")):
            text = str(key or "").strip()
            if text and text not in result:
                result[text] = row
    return result


def _testnet_blockers(readiness: dict[str, Any]) -> list[str]:
    blockers = readiness.get("blockers")
    if not isinstance(blockers, list):
        return []
    return [str(item) for item in blockers if item]


def _build_strategy_asset(
    quality_row: dict[str, Any],
    gate_row: dict[str, Any] | None,
    readiness_blockers: list[str],
) -> dict[str, Any]:
    strategy_name = str(quality_row.get("strategyName") or quality_row.get("taskId") or "未命名策略")
    timeframe = str(quality_row.get("timeframe") or "")
    family = _plain_family(strategy_name, timeframe)
    closed_samples = _safe_int(quality_row.get("closedSamples"))
    win_rate = _first_non_empty(quality_row.get("winRate"), quality_row.get("winRatePct"))
    profit_factor = quality_row.get("profitFactor")
    total_r = quality_row.get("totalR")
    quality_score = quality_row.get("qualityScore")
    gate = gate_row or {}
    promotion_status = str(
        _first_non_empty(
            gate.get("promotionTier"),
            quality_row.get("promotionStatus"),
            "continue_observing",
        )
    )
    can_enter_testnet = bool(gate.get("canEnterTestnetReadiness"))
    gate_status = "testnet_prep_candidate" if can_enter_testnet else promotion_status
    next_action = str(
        _first_non_empty(
            gate.get("nextAction"),
            quality_row.get("nextAction"),
            "继续本地沙盒观察，补足闭合样本、失败样本和风险备注。",
        )
    )
    missing_checks = gate.get("missingChecks") if isinstance(gate.get("missingChecks"), list) else []
    passed_checks = gate.get("passedChecks") if isinstance(gate.get("passedChecks"), list) else []
    latest = quality_row.get("latestTrigger") if isinstance(quality_row.get("latestTrigger"), dict) else {}

    return {
        "strategyId": _first_non_empty(quality_row.get("strategyId"), gate.get("strategyId"), quality_row.get("taskId")),
        "taskId": _first_non_empty(quality_row.get("taskId"), gate.get("taskId")),
        "readableName": strategy_name,
        "plainName": family["familyName"],
        "familyId": family["familyId"],
        "familyName": family["familyName"],
        "timeframe": timeframe or None,
        "directionLabel": family["directionLabel"],
        "oneLine": family["oneLine"],
        "whenItWorks": family["whenItWorks"],
        "whenToAvoid": family["whenToAvoid"],
        "coreRules": family["coreRules"],
        "evidence": {
            "closedSamples": closed_samples,
            "reviewMinimum": _safe_int(quality_row.get("reviewMinimum"), 30),
            "dryRunMinimum": _safe_int(quality_row.get("dryRunMinimum"), 100),
            "winRate": win_rate,
            "profitFactor": profit_factor,
            "totalR": total_r,
            "qualityScore": quality_score,
            "maxConsecutiveLosses": quality_row.get("maxConsecutiveLosses"),
            "maxDrawdownR": quality_row.get("maxDrawdownR"),
            "dataGapCount": quality_row.get("dataGapCount"),
            "riskWarningCount": quality_row.get("riskWarningCount"),
            "invalidatedCount": quality_row.get("invalidatedCount"),
            "latestPair": latest.get("latestPair"),
            "latestOutcomeR": latest.get("latestOutcomeR"),
            "latestLogAt": latest.get("latestLogAt"),
        },
        "gate": {
            "status": gate_status,
            "label": _first_non_empty(gate.get("promotionLabel"), quality_row.get("promotionLabel"), gate_status),
            "canEnterSandboxReview": bool(gate.get("canEnterSandboxReview")) or gate_status in {"sandbox_review_candidate", "testnet_readiness_candidate"},
            "canEnterTestnetReadiness": can_enter_testnet,
            "passedChecks": passed_checks,
            "missingChecks": missing_checks,
            "testnetBlockers": readiness_blockers,
            "dryRunApproved": False,
            "liveTradingApproved": False,
        },
        "nextAction": next_action,
        "operatorChecklist": [
            "继续记录无信号日、规则匹配日、失败样本和闭合样本。",
            "先做集中度、滑点、数据缺口和连续亏损复核。",
            "Testnet 安全设计完成前，不输入 API Key，不创建订单。",
        ],
        "safetyNote": "Research asset only. No API key, no Trade API, no order, no automatic trading.",
    }


def build_strategy_asset_playbook() -> dict[str, Any]:
    quality = build_local_sandbox_quality_center()
    quality_rows = quality.get("strategies") if isinstance(quality.get("strategies"), list) else []
    readonly = quality.get("readonlyPreparation") if isinstance(quality.get("readonlyPreparation"), dict) else {}
    blockers = readonly.get("testnetBlockers") if isinstance(readonly.get("testnetBlockers"), list) else []
    blockers = [str(item) for item in blockers if item] or DEFAULT_TESTNET_BLOCKERS
    strategies = [
        _build_strategy_asset(
            row,
            None,
            blockers,
        )
        for row in quality_rows
        if isinstance(row, dict)
    ]
    strategies.sort(
        key=lambda row: (
            row["gate"]["status"] != "testnet_prep_candidate",
            row["gate"]["status"] != "sandbox_review_candidate",
            -_safe_int(row["evidence"].get("closedSamples")),
            -_safe_float(row["evidence"].get("profitFactor"), -1),
        )
    )
    summary_quality = quality.get("summary") if isinstance(quality.get("summary"), dict) else {}
    top = strategies[0] if strategies else {}
    sandbox_review_count = sum(
        1
        for row in strategies
        if _safe_int(row.get("evidence", {}).get("closedSamples")) >= _safe_int(row.get("evidence", {}).get("reviewMinimum"), 30)
    )
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "strategyCount": len(strategies),
            "totalClosedSamples": summary_quality.get("totalClosedSamples", 0),
            "sandboxReviewCandidateCount": sandbox_review_count,
            "testnetPrepCandidateCount": summary_quality.get("testnetPrepCandidateCount", 0),
            "testnetReadinessCandidateCount": summary_quality.get("testnetPrepCandidateCount", 0),
            "blockedFromExecution": True,
            "sandboxRunning": bool(summary_quality.get("sandboxRunning")),
            "runnerStatus": summary_quality.get("runnerStatus"),
            "topStrategyName": top.get("readableName"),
            "topStrategyPlainName": top.get("plainName"),
            "testnetReadinessStage": readonly.get("testnetReadinessStage", "blocked"),
            "testnetBlockerCount": len(blockers),
            "nextAction": "把策略先资产化、读懂规则和风险，再补集中度/压力复核；Testnet 安全设计完成前不接密钥、不创建订单。",
        },
        "strategies": strategies,
        "executionReadiness": {
            "testnetEnabled": False,
            "apiKeyInputEnabled": False,
            "tradeApiAllowed": False,
            "withdrawApiAllowed": False,
            "orderCreationAllowed": False,
            "autoTradingAllowed": False,
            "dryRunApproved": False,
            "liveTradingApproved": False,
            "blockers": blockers,
            "nextAction": "下一步只能补 Testnet 设计清单和本地订单生命周期模拟，不允许连接交易所私有接口。",
        },
        "sourceSnapshots": {
            "qualityCenterVersion": quality.get("version"),
            "promotionGateVersion": None,
            "testnetReadinessVersion": None,
            "performanceMode": "fast_quality_center_only",
        },
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Strategy Asset Playbook is local research only. It cannot store API keys, connect private exchange endpoints, create orders, or run automatic trading.",
    }


if __name__ == "__main__":
    print(json.dumps(build_strategy_asset_playbook(), ensure_ascii=False, indent=2))
