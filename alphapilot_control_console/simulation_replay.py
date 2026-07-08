from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .config import SAFETY_BOUNDARY
from .sample_path_instrumentation import enrich_log_with_estimated_path
from .simulation_review import build_simulation_review
from .state_store import list_paper_observation_logs


CONTROL_CONSOLE_VERSION = "V13.7.46"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_46"

PATH_FIELDS = {
    "sampleKey": "样本去重键",
    "entryTime": "入场时间",
    "exitTime": "出场时间",
    "entryPrice": "入场价格",
    "exitPrice": "出场价格",
    "direction": "方向",
    "marketRegime": "市场状态",
    "mfeR": "最大有利浮动",
    "maeR": "最大不利浮动",
    "feeEstimate": "费用估算",
    "slippageEstimate": "滑点估算",
    "holdingTimeMinutes": "持有时长",
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


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_outcome_r(value: Any) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return None
    return _safe_float(match.group(0), 0.0)


def _extract_outcome_r(row: dict[str, Any]) -> float | None:
    if row.get("outcomeR") is not None:
        return _parse_outcome_r(row.get("outcomeR"))
    return _parse_outcome_r(row.get("outcome"))


def _closed_sample_identity(log: dict[str, Any]) -> str:
    sample_key = str(log.get("sampleKey") or "").strip()
    if sample_key:
        return sample_key
    legacy_parts = [
        str(log.get("artifactId") or ""),
        str(log.get("pair") or ""),
        str(log.get("timeframe") or ""),
        str(log.get("dataMode") or ""),
        str(log.get("dataSourcePathHint") or ""),
    ]
    legacy_key = "|".join(legacy_parts).strip("|")
    return legacy_key or str(log.get("logId") or log.get("createdAt") or id(log))


def _unique_closed_logs(logs: list[dict[str, Any]]) -> list[tuple[dict[str, Any], float]]:
    seen: set[str] = set()
    values: list[tuple[dict[str, Any], float]] = []
    for log in sorted(logs, key=lambda item: str(item.get("createdAt") or "")):
        outcome_r = _extract_outcome_r(log)
        if outcome_r is None:
            continue
        identity = _closed_sample_identity(log)
        if identity in seen:
            continue
        seen.add(identity)
        values.append((log, outcome_r))
    return values


def _missing_fields(log: dict[str, Any]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for key, label in PATH_FIELDS.items():
        if log.get(key) in (None, ""):
            missing.append({"field": key, "label": label})
    return missing


def _sample_quality(log: dict[str, Any], missing: list[dict[str, str]]) -> str:
    if log.get("instrumentationStatus") == "actual":
        return "full_path_ready"
    if log.get("instrumentationStatus") == "estimated":
        return "estimated_path_ready"
    fields = {row["field"] for row in missing}
    if not fields:
        return "partial_path_ready"
    if {"entryPrice", "exitPrice", "mfeR", "maeR"} & fields:
        return "representative_sample_without_full_trade_path"
    return "partial_path_ready"


def _build_replay_narrative(log: dict[str, Any], outcome_r: float, missing: list[dict[str, str]]) -> str:
    pair = log.get("pair") or "未知币种"
    timeframe = log.get("timeframe") or "未知周期"
    reason = log.get("outcomeReason") or log.get("outcome") or "未记录原因"
    sign = "+" if outcome_r > 0 else ""
    if log.get("instrumentationStatus") == "estimated":
        path_note = "；已用本地 public OHLCV 缓存估算入场、出场和 MFE/MAE"
    elif missing:
        path_note = "；缺少完整路径字段，只能做代表样本复盘"
    else:
        path_note = "；路径字段可用于复盘"
    return f"{pair} · {timeframe} · {reason} · {sign}{outcome_r:.2f}R{path_note}。"


def _build_sample(log: dict[str, Any], outcome_r: float, strategy: dict[str, Any]) -> dict[str, Any]:
    enriched_log = enrich_log_with_estimated_path(log, task=strategy)
    missing = _missing_fields(enriched_log)
    quality = _sample_quality(enriched_log, missing)
    return {
        "sampleId": enriched_log.get("sampleKey") or enriched_log.get("logId"),
        "logId": enriched_log.get("logId"),
        "sampleKey": enriched_log.get("sampleKey"),
        "taskId": strategy.get("taskId") or enriched_log.get("artifactId"),
        "strategyId": strategy.get("strategyId") or enriched_log.get("strategyId"),
        "strategyName": strategy.get("strategyName") or enriched_log.get("title"),
        "pair": enriched_log.get("pair"),
        "timeframe": enriched_log.get("timeframe"),
        "createdAt": enriched_log.get("createdAt"),
        "runId": enriched_log.get("runId"),
        "outcome": enriched_log.get("outcome"),
        "outcomeR": round(outcome_r, 4),
        "outcomeReason": enriched_log.get("outcomeReason"),
        "signalObserved": bool(enriched_log.get("signalObserved")),
        "ruleMatched": bool(enriched_log.get("ruleMatched")),
        "virtualCapital": enriched_log.get("virtualCapital"),
        "virtualEquity": enriched_log.get("virtualEquity"),
        "riskUnitPercent": enriched_log.get("riskUnitPercent"),
        "dataMode": enriched_log.get("dataMode"),
        "dataStatus": enriched_log.get("dataStatus"),
        "dataSourcePathHint": enriched_log.get("dataSourcePathHint"),
        "sandboxMode": enriched_log.get("sandboxMode"),
        "entryTime": enriched_log.get("entryTime"),
        "exitTime": enriched_log.get("exitTime"),
        "entryPrice": enriched_log.get("entryPrice"),
        "exitPrice": enriched_log.get("exitPrice"),
        "exitPriceSource": enriched_log.get("exitPriceSource"),
        "direction": enriched_log.get("direction"),
        "directionSource": enriched_log.get("directionSource"),
        "marketRegime": enriched_log.get("marketRegime"),
        "mfeR": enriched_log.get("mfeR"),
        "maeR": enriched_log.get("maeR"),
        "pathOutcomeR": enriched_log.get("pathOutcomeR"),
        "feeEstimate": enriched_log.get("feeEstimate"),
        "slippageEstimate": enriched_log.get("slippageEstimate"),
        "feeEstimateR": enriched_log.get("feeEstimateR"),
        "slippageEstimateR": enriched_log.get("slippageEstimateR"),
        "feeRateEstimate": enriched_log.get("feeRateEstimate"),
        "slippageRateEstimate": enriched_log.get("slippageRateEstimate"),
        "costEstimateMode": enriched_log.get("costEstimateMode"),
        "holdingTimeMinutes": enriched_log.get("holdingTimeMinutes"),
        "replayWindowCandleCount": enriched_log.get("replayWindowCandleCount"),
        "replayWindowStart": enriched_log.get("replayWindowStart"),
        "replayWindowEnd": enriched_log.get("replayWindowEnd"),
        "instrumentationVersion": enriched_log.get("instrumentationVersion"),
        "instrumentationMode": enriched_log.get("instrumentationMode"),
        "instrumentationStatus": enriched_log.get("instrumentationStatus"),
        "instrumentationMissingReason": enriched_log.get("instrumentationMissingReason"),
        "actualExchangeFill": bool(enriched_log.get("actualExchangeFill")),
        "isEstimatedReplay": bool(enriched_log.get("isEstimatedReplay")),
        "missingFields": missing,
        "sampleQuality": quality,
        "replayNarrative": _build_replay_narrative(enriched_log, outcome_r, missing),
        "safetyNote": "本条记录仅用于本地模拟盘复盘，不是 testnet、实盘信号或订单。",
    }


def _quality_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {
            "fullPathSampleCount": 0,
            "estimatedPathSampleCount": 0,
            "actualFillSampleCount": 0,
            "representativeSampleCount": 0,
            "missingPathFieldCount": 0,
            "hasUniqueSampleId": False,
            "hasEntryExitPrices": False,
            "hasPathMetrics": False,
            "hasCostMetrics": False,
            "hasEstimatedPath": False,
            "hasActualFillPath": False,
        }
    full_path_count = sum(1 for sample in samples if sample.get("sampleQuality") == "full_path_ready")
    estimated_count = sum(1 for sample in samples if sample.get("sampleQuality") == "estimated_path_ready")
    actual_count = sum(1 for sample in samples if sample.get("actualExchangeFill"))
    missing_count = sum(len(sample.get("missingFields") or []) for sample in samples)
    return {
        "fullPathSampleCount": full_path_count,
        "estimatedPathSampleCount": estimated_count,
        "actualFillSampleCount": actual_count,
        "representativeSampleCount": len(samples),
        "missingPathFieldCount": missing_count,
        "hasUniqueSampleId": any(bool(sample.get("sampleKey")) for sample in samples),
        "hasEntryExitPrices": all(sample.get("entryPrice") is not None and sample.get("exitPrice") is not None for sample in samples),
        "hasPathMetrics": all(sample.get("mfeR") is not None and sample.get("maeR") is not None for sample in samples),
        "hasCostMetrics": all(sample.get("feeEstimate") is not None and sample.get("slippageEstimate") is not None for sample in samples),
        "hasEstimatedPath": estimated_count > 0,
        "hasActualFillPath": actual_count > 0,
    }


def _build_strategy_replay(row: dict[str, Any]) -> dict[str, Any]:
    task_id = str(row.get("taskId") or "").strip()
    raw_logs_payload = list_paper_observation_logs(task_id)
    raw_logs = raw_logs_payload if isinstance(raw_logs_payload, list) else []
    unique_logs = _unique_closed_logs([log for log in raw_logs if isinstance(log, dict)])
    deduped_count = _safe_int(row.get("metrics", {}).get("closedSamples")) if isinstance(row.get("metrics"), dict) else len(unique_logs)
    representative_pairs = unique_logs[:deduped_count] if deduped_count > 0 else []
    samples = [_build_sample(log, outcome_r, row) for log, outcome_r in representative_pairs]
    quality = _quality_summary(samples)
    latest_sample_time = max((_parse_time(sample.get("createdAt")) for sample in samples), default=None)
    raw_outcome_count = sum(1 for log in raw_logs if isinstance(log, dict) and _extract_outcome_r(log) is not None)
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    return {
        "taskId": task_id,
        "strategyId": row.get("strategyId"),
        "strategyName": row.get("strategyName"),
        "timeframe": row.get("timeframe"),
        "status": row.get("status"),
        "statusLabel": row.get("statusLabel"),
        "recommendedAction": row.get("recommendedAction"),
        "dedupedClosedSampleCount": deduped_count,
        "rawOutcomeLogCount": raw_outcome_count,
        "representativeSampleCount": len(samples),
        "sampleSelectionNote": "复盘样本按本地日报去重后的闭合样本数截取；原始自动日志可能包含重复观察。",
        "metrics": {
            "totalR": metrics.get("totalR"),
            "winRate": metrics.get("winRate"),
            "profitFactor": metrics.get("profitFactor"),
            "virtualCapital": metrics.get("virtualCapital"),
            "virtualEquity": metrics.get("virtualEquity"),
            "virtualPnl": metrics.get("virtualPnl"),
            "maxDrawdownR": metrics.get("maxDrawdownR"),
            "maxConsecutiveLosses": metrics.get("maxConsecutiveLosses"),
        },
        "quality": quality,
        "latestSampleAt": latest_sample_time.isoformat() if latest_sample_time else None,
        "samples": samples,
        "whatCanBeReviewed": [
            "pair/timeframe 分布",
            "本地模拟 R 结果",
            "估算 entry/exit price",
            "估算 MFE/MAE 路径指标",
            "估算 fee/slippage 成本",
            "数据来源文件和缓存状态",
            "虚拟资金和虚拟权益变化",
        ],
        "whatNeedsInstrumentation": [
            "real exchange-independent paper fill log",
            "actual manual observation timestamp",
            "actual entry/exit confirmation source",
            "user review label after replay",
        ],
        "safetyNote": "闭合样本复盘只用于本地研究，不会创建订单、不会进入 Dry-run、不会连接实盘权限。",
    }


def build_closed_sample_replay(strategy_id: str | None = None, limit: int = 80) -> dict[str, Any]:
    review = build_simulation_review()
    rows = review.get("queue") if isinstance(review.get("queue"), list) else []
    strategy_rows = [_build_strategy_replay(row) for row in rows if isinstance(row, dict)]
    if strategy_id:
        wanted = str(strategy_id).strip()
        strategy_rows = [
            row for row in strategy_rows
            if wanted in {str(row.get("taskId")), str(row.get("strategyId"))}
        ]
    safe_limit = max(1, min(_safe_int(limit, 80), 200))
    all_samples = [
        {**sample, "strategyName": row.get("strategyName"), "taskId": row.get("taskId")}
        for row in strategy_rows
        for sample in row.get("samples", [])
        if isinstance(sample, dict)
    ]
    all_samples.sort(key=lambda sample: str(sample.get("createdAt") or ""), reverse=True)
    non_actual_path_count = sum(
        1 for sample in all_samples
        if not sample.get("actualExchangeFill")
    )
    estimated_path_count = sum(
        1 for sample in all_samples
        if sample.get("sampleQuality") == "estimated_path_ready"
    )
    summary = {
        "totalStrategies": len(strategy_rows),
        "totalDedupedClosedSamples": sum(_safe_int(row.get("dedupedClosedSampleCount")) for row in strategy_rows),
        "totalRawOutcomeLogs": sum(_safe_int(row.get("rawOutcomeLogCount")) for row in strategy_rows),
        "totalRepresentativeSamples": sum(_safe_int(row.get("representativeSampleCount")) for row in strategy_rows),
        "estimatedPathSampleCount": estimated_path_count,
        "nonActualPathSampleCount": non_actual_path_count,
        "missingFullPathSampleCount": non_actual_path_count,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "nextAction": "继续用估算路径复盘策略弱点；后续若进入 testnet，也必须保持人工确认和安全闸门。",
    }
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "summary": summary,
        "strategies": strategy_rows,
        "samples": all_samples[:safe_limit],
        "sampleSchema": {
            "currentMode": "estimated_sample_path_replay",
            "fieldLabels": PATH_FIELDS,
            "note": "当前页面使用本地 public OHLCV cache 估算样本路径，不是真实成交回放。",
            "actualExchangeFill": False,
        },
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Closed sample replay is local research only. It does not connect exchange APIs, read accounts, or create orders.",
    }


def build_closed_sample_strategy_detail(strategy_id: str) -> dict[str, Any] | None:
    payload = build_closed_sample_replay(strategy_id=strategy_id, limit=200)
    rows = payload.get("strategies") if isinstance(payload.get("strategies"), list) else []
    if not rows:
        return None
    return {
        "version": payload["version"],
        "source": payload["source"],
        "strategy": rows[0],
        "sampleSchema": payload["sampleSchema"],
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyBoundary": SAFETY_BOUNDARY,
    }
