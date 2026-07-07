from __future__ import annotations

from typing import Any

from .config import SAFETY_BOUNDARY
from .state_store import now_iso


CONTROL_CONSOLE_VERSION = "V13.7.37"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_37"


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _metric(item: dict[str, Any], key: str) -> float | None:
    value = item.get(key)
    if value is None:
        return None
    return _safe_float(value)


def _candidate_text(item: dict[str, Any]) -> str:
    parts = [
        item.get("artifactId"),
        item.get("strategyId"),
        item.get("title"),
        item.get("originalTitle"),
        item.get("displaySubtitle"),
        item.get("sourceFile"),
        item.get("version"),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _find_candidate(candidates: list[dict[str, Any]], needles: list[str]) -> dict[str, Any] | None:
    lowered_needles = [needle.lower() for needle in needles]
    for item in candidates:
        text = _candidate_text(item)
        if any(needle in text for needle in lowered_needles):
            return item
    return None


def _score_candidate(row: dict[str, Any], source: dict[str, Any] | None) -> float:
    score = _safe_float(row.get("baseScore"), 0.0)
    if source:
        sample_count = _metric(source, "sampleCount") or 0.0
        win_rate = _metric(source, "winRatePct") or 0.0
        profit_factor = _metric(source, "profitFactor") or 0.0
        reward_risk = _metric(source, "rewardRiskRatio") or 0.0
        drawdown = _metric(source, "maxDrawdownPct")
        score += min(sample_count, 300.0) / 15.0
        score += max(0.0, win_rate - 40.0) * 1.6
        score += profit_factor * 12.0
        score += reward_risk * 8.0
        if drawdown is not None:
            score -= min(drawdown, 80.0) / 4.0
    return round(score, 2)


def _build_pool_row(template: dict[str, Any], source: dict[str, Any] | None, rank_seed: int) -> dict[str, Any]:
    source_metrics = source or {}
    evidence: list[str] = []
    missing: list[str] = []
    if source:
        evidence.append(f"关联资产：{source.get('title') or source.get('strategyId') or source.get('artifactId')}")
        if source.get("sampleCount") is not None:
            evidence.append(f"已有样本：{source.get('sampleCount')}")
        if source.get("profitFactor") is not None:
            evidence.append(f"PF：{source.get('profitFactor')}")
        if source.get("winRatePct") is not None:
            evidence.append(f"胜率：{source.get('winRatePct')}%")
    else:
        missing.append("没有匹配到现有策略资产，需要先补策略规格和回测报告。")

    for key, label in (
        ("sampleCount", "样本"),
        ("winRatePct", "胜率"),
        ("profitFactor", "PF"),
        ("rewardRiskRatio", "RR"),
    ):
        if source_metrics.get(key) is None:
            missing.append(f"缺少{label}指标。")

    validation_status = template["validationStatus"]
    if source and template.get("existingShortCycle"):
        validation_label = "已有短周期资产，仍需扩样本复测"
    elif source:
        validation_label = "由现有资产派生，待短周期回测"
    else:
        validation_label = "待创建研究资产"

    row = {
        "poolId": template["poolId"],
        "rank": rank_seed,
        "name": template["name"],
        "shortName": template["shortName"],
        "category": template["category"],
        "targetTimeframe": template["targetTimeframe"],
        "candidateFrequencyLabel": template["candidateFrequencyLabel"],
        "notHft": True,
        "direction": template["direction"],
        "sourceArtifactId": source.get("artifactId") if source else None,
        "sourceStrategyId": source.get("strategyId") if source else None,
        "sourceTitle": source.get("title") if source else None,
        "sourceQueueType": source.get("queueType") if source else None,
        "sourceQueueLabel": source.get("queueLabel") if source else None,
        "sourceFile": source.get("sourceFile") if source else None,
        "sampleCount": source_metrics.get("sampleCount"),
        "winRatePct": source_metrics.get("winRatePct"),
        "profitFactor": source_metrics.get("profitFactor"),
        "rewardRiskRatio": source_metrics.get("rewardRiskRatio"),
        "maxDrawdownPct": source_metrics.get("maxDrawdownPct"),
        "totalReturnPct": source_metrics.get("totalReturnPct"),
        "baseScore": template["baseScore"],
        "shortCycleScore": 0.0,
        "validationStatus": validation_status,
        "validationLabel": validation_label,
        "evidence": evidence,
        "missingData": missing[:6],
        "entryIdea": template["entryIdea"],
        "riskIdea": template["riskIdea"],
        "whySelected": template["whySelected"],
        "nextAction": template["nextAction"],
        "safetyNote": "短周期候选池只做研究排序，不是交易信号，不创建订单。",
    }
    row["shortCycleScore"] = _score_candidate(row, source)
    return row


SHORT_CYCLE_TEMPLATES: list[dict[str, Any]] = [
    {
        "poolId": "sc_volume_rebound_15m_v01",
        "name": "15m 放量反弹候选",
        "shortName": "放量反弹 15m",
        "category": "volume_rebound",
        "targetTimeframe": "15m",
        "candidateFrequencyLabel": "短周期高频候选（非 HFT）",
        "direction": "long_only",
        "needles": ["alpha_volume_rebound_v01", "volume_rebound", "v13_4_smoke_backtest"],
        "baseScore": 78,
        "existingShortCycle": True,
        "validationStatus": "existing_report_needs_expanded_retest",
        "entryIdea": "15m 放量后价格修复，叠加 BTC 急跌过滤和基础趋势过滤。",
        "riskIdea": "手续费、滑点和假反弹成本较高，必须做 15m 多币种扩样本。",
        "whySelected": "已有 V13.4 真实 smoke 回测资产，适合作为短周期池的第一条样本线。",
        "nextAction": "补 2020-2026 多币种 15m 回测，单独统计手续费后 2R 表现。",
    },
    {
        "poolId": "sc_trend_pullback_1h_v01",
        "name": "1h 趋势回撤候选",
        "shortName": "趋势回撤 1h",
        "category": "trend_pullback",
        "targetTimeframe": "1h",
        "candidateFrequencyLabel": "短周期高频候选（非 HFT）",
        "direction": "long_short_research",
        "needles": ["alpha_trend_pullback_1h_v01", "trend_pullback_1h"],
        "baseScore": 82,
        "existingShortCycle": True,
        "validationStatus": "existing_report_needs_quality_review",
        "entryIdea": "1h 趋势方向内等待回撤，优先看趋势质量、回撤深度和动能恢复。",
        "riskIdea": "当前样本偏少且 PF 偏弱，不能进入主线，只能进入扩样本观察。",
        "whySelected": "现有候选明确带 1h，是当前最接近短周期主线的资产之一。",
        "nextAction": "扩大到 Top 50/Top 100，按牛熊震荡分层复测。",
    },
    {
        "poolId": "sc_short_rejection_1h_v01",
        "name": "1h 短线反转拒绝候选",
        "shortName": "反转拒绝 1h",
        "category": "short_rejection",
        "targetTimeframe": "1h",
        "candidateFrequencyLabel": "短周期高频候选（非 HFT）",
        "direction": "short_research",
        "needles": ["alpha_short_rejection_1h_v01", "short_rejection_1h"],
        "baseScore": 76,
        "existingShortCycle": True,
        "validationStatus": "existing_report_needs_failure_filter",
        "entryIdea": "1h 假突破或反弹失败后观察拒绝形态，不解释为做空建议。",
        "riskIdea": "币圈挤空和急拉风险高，需要先加入流动性、资金费率和 BTC 状态过滤。",
        "whySelected": "已有 1h 反转/拒绝研究资产，可专门验证失败过滤是否有效。",
        "nextAction": "补失败样本复核，重点看连续亏损和极端反弹风险。",
    },
    {
        "poolId": "sc_volatility_compression_30m_v01",
        "name": "30m 波动压缩突破候选",
        "shortName": "压缩突破 30m",
        "category": "volatility_breakout",
        "targetTimeframe": "30m",
        "candidateFrequencyLabel": "短周期高频候选（非 HFT）",
        "direction": "long_short_research",
        "needles": ["volatility_compression_breakout", "alpha_batch_h"],
        "baseScore": 70,
        "existingShortCycle": False,
        "validationStatus": "derived_needs_30m_backtest",
        "entryIdea": "从 4h 波动压缩突破资产降到 30m，观察压缩后放量突破的路径质量。",
        "riskIdea": "30m 假突破密度更高，需要强制滑点、成交量和突破后回踩过滤。",
        "whySelected": "突破类逻辑适合短周期验证，但必须独立补 30m 回测。",
        "nextAction": "先做 30m BTC/ETH/SOL smoke，再扩展到 Top 50。",
    },
    {
        "poolId": "sc_bollinger_reversion_30m_v01",
        "name": "30m 布林均值回归候选",
        "shortName": "布林回归 30m",
        "category": "mean_reversion",
        "targetTimeframe": "30m",
        "candidateFrequencyLabel": "短周期高频候选（非 HFT）",
        "direction": "long_short_research",
        "needles": ["bollinger_reversion", "alpha_batch_e", "alpha_batch_f"],
        "baseScore": 68,
        "existingShortCycle": False,
        "validationStatus": "derived_needs_30m_backtest",
        "entryIdea": "30m 偏离布林带后观察均值回归，要求 BTC 状态和流动性不过度恶化。",
        "riskIdea": "趋势单边时均值回归容易连续亏损，必须加 regime gate 和止损纪律。",
        "whySelected": "均值回归能补充趋势/突破候选，适合放进短周期池做对照。",
        "nextAction": "补 30m 分市场状态回测，只保留具备 2R 路径质量的样本。",
    },
]


def build_short_cycle_candidate_pool(payload: dict[str, Any]) -> dict[str, Any]:
    queue = payload.get("strategyCandidateQueue") if isinstance(payload.get("strategyCandidateQueue"), dict) else {}
    candidates = queue.get("candidates") if isinstance(queue.get("candidates"), list) else []
    safe_candidates = [item for item in candidates if isinstance(item, dict)]
    rows = [
        _build_pool_row(template, _find_candidate(safe_candidates, template["needles"]), index)
        for index, template in enumerate(SHORT_CYCLE_TEMPLATES, start=1)
    ]
    rows = sorted(rows, key=lambda item: float(item.get("shortCycleScore") or 0), reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank

    existing_count = sum(1 for row in rows if str(row.get("validationStatus") or "").startswith("existing"))
    derived_count = sum(1 for row in rows if str(row.get("validationStatus") or "").startswith("derived"))
    missing_metric_count = sum(1 for row in rows if row.get("missingData"))
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "generatedAt": now_iso(),
        "source": CONTROL_CONSOLE_SOURCE,
        "summary": {
            "totalCandidates": len(rows),
            "selectedShortCycleCount": len(rows),
            "existingShortCycleReportCount": existing_count,
            "derivedCandidateCount": derived_count,
            "missingMetricCandidateCount": missing_metric_count,
            "targetTimeframes": ["15m", "30m", "1h"],
            "topCandidateName": rows[0].get("name") if rows else None,
            "poolMethod": "Select five short-cycle research candidates from existing assets and derived templates, then rank by source evidence, samples, PF, RR, win rate, and drawdown penalty.",
            "safetyNote": "This is a short-cycle research pool, not tick-level HFT, not a signal engine, and not execution.",
        },
        "candidates": rows,
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "shortCycleResearchOnly": True,
            "tickLevelHft": False,
            "orderBookDataRequired": False,
            "createsOrders": False,
            "autoTrading": False,
        },
        "safetyNotes": [
            "这里的高频指 15m/30m/1h 短周期研究候选，不是秒级盘口 HFT。",
            "候选池只用于安排回测和前向观察，不代表可交易策略。",
            "本版本不接 API Key、不接 Trade API、不接 Withdraw API、不读取真实账户、不创建订单。",
        ],
    }
