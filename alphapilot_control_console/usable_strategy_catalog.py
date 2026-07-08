from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DEFAULT_QUANT_ENGINE_PATH, SAFETY_BOUNDARY, get_quant_engine_path
from .state_store import now_iso


CONTROL_CONSOLE_VERSION = "V13.7.41"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_41"

LOW_FREQUENCY_TASK_PACK_REPORT = "v13_7_21_paper_observation_task_pack_report.json"
SHORT_CYCLE_SELECTED_REPORT = "v13_7_40_short_cycle_selected_candidate_cards.json"
USABLE_STRATEGY_CATALOG_REPORT = "v13_7_41_usable_strategy_catalog.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_float(value: Any, fallback: float | None = None) -> float | None:
    if value is None:
        return fallback
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


def _metric(metrics: dict[str, Any], key: str) -> float | None:
    return _safe_float(metrics.get(key))


def _safe_pairs(pairs: Any) -> list[str]:
    if not isinstance(pairs, list):
        return []
    rows: list[str] = []
    for item in pairs:
        if isinstance(item, str):
            pair = item.strip()
        elif isinstance(item, dict):
            pair = str(item.get("pair") or "").strip()
        else:
            pair = ""
        if pair:
            rows.append(pair)
    return list(dict.fromkeys(rows))


def _score_metrics(metrics: dict[str, Any], test_metrics: dict[str, Any] | None = None) -> float:
    test_metrics = test_metrics or {}
    trades = _metric(metrics, "tradeCount") or 0.0
    win_rate = _metric(metrics, "winRatePct") or 0.0
    profit_factor = _metric(metrics, "profitFactor") or 0.0
    max_drawdown = (
        _metric(metrics, "maxDrawdownPct")
        if metrics.get("maxDrawdownPct") is not None
        else _metric(metrics, "maxDrawdownPctAt1PctRisk")
    )
    test_pf = _metric(test_metrics, "profitFactor") or 0.0
    score = 40.0
    score += min(trades, 300.0) / 10.0
    score += max(0.0, win_rate - 40.0) * 1.2
    score += profit_factor * 12.0
    score += test_pf * 10.0
    if max_drawdown is not None:
        score -= min(max_drawdown, 35.0) * 0.9
    return round(max(0.0, min(score, 100.0)), 2)


def _normalize_low_frequency_task(task: dict[str, Any], index: int) -> dict[str, Any]:
    metrics = task.get("historicalMetrics") if isinstance(task.get("historicalMetrics"), dict) else {}
    pairs = _safe_pairs(task.get("recommendedPairs"))
    return {
        "catalogId": f"usable_low_frequency::{task.get('taskId') or index}",
        "taskId": task.get("taskId"),
        "strategyId": task.get("strategyId"),
        "candidateId": task.get("candidateId"),
        "name": task.get("title") or task.get("candidateId") or task.get("taskId"),
        "shortName": task.get("title") or task.get("candidateId") or task.get("taskId"),
        "family": task.get("family") or "unknown",
        "direction": task.get("direction") or "long_research",
        "timeframe": task.get("timeframe") or "1d",
        "frequencyBucket": "low_frequency",
        "frequencyLabel": "低频日线观察",
        "targetR": _safe_float(task.get("targetRewardRiskRatio"), 2.0),
        "approvalTier": task.get("status") or "planned_paper_observation",
        "sandboxReady": True,
        "sourceReport": task.get("sourceReport") or f"reports\\{LOW_FREQUENCY_TASK_PACK_REPORT}",
        "selectedPairs": pairs,
        "metrics": metrics,
        "validationMetrics": {},
        "testMetrics": {},
        "params": task.get("params") if isinstance(task.get("params"), dict) else {},
        "score": _score_metrics(metrics),
        "riskNotes": [
            "低频候选仍需要本地沙盒持续观察，不能直接升级实盘。",
            "日线策略不会因为 5 分钟心跳频繁产生新闭合样本。",
        ],
        "nextAction": "继续收集真实前向日志和本地沙盒闭合样本。",
    }


def _normalize_short_cycle_candidate(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    metrics = candidate.get("metrics") if isinstance(candidate.get("metrics"), dict) else {}
    validation_metrics = (
        candidate.get("validationMetrics") if isinstance(candidate.get("validationMetrics"), dict) else {}
    )
    test_metrics = candidate.get("testMetrics") if isinstance(candidate.get("testMetrics"), dict) else {}
    asset_filter = candidate.get("assetFilter") if isinstance(candidate.get("assetFilter"), dict) else {}
    pairs = _safe_pairs(asset_filter.get("selectedPairs"))
    return {
        "catalogId": f"usable_short_cycle::{candidate.get('candidateId') or index}",
        "taskId": f"v13_7_41_observe_{candidate.get('candidateId') or index}",
        "strategyId": candidate.get("candidateId"),
        "candidateId": candidate.get("candidateId"),
        "name": candidate.get("name") or candidate.get("candidateId"),
        "shortName": candidate.get("name") or candidate.get("candidateId"),
        "family": candidate.get("family") or "unknown",
        "direction": candidate.get("direction") or "research",
        "timeframe": candidate.get("timeframe") or "1h",
        "frequencyBucket": "short_cycle",
        "frequencyLabel": "短周期 1h 沙盒观察",
        "targetR": _safe_float(candidate.get("targetR"), 2.0),
        "approvalTier": candidate.get("approvalTier") or "strict_approved_asset_filtered",
        "sandboxReady": True,
        "sourceReport": f"reports\\{SHORT_CYCLE_SELECTED_REPORT}",
        "selectedPairs": pairs,
        "assetFilter": asset_filter,
        "metrics": metrics,
        "validationMetrics": validation_metrics,
        "testMetrics": test_metrics,
        "params": candidate.get("params") if isinstance(candidate.get("params"), dict) else {},
        "score": _score_metrics(metrics, test_metrics),
        "riskNotes": [
            "短周期候选来自 train-only asset filter，仍有多重搜索和过拟合风险。",
            "只能进入本地沙盒/纸面观察，不能作为交易信号或实盘指令。",
            "固定 2R 目标保持不变，后续优化只允许改过滤质量和适用市场状态。",
        ],
        "nextAction": "放入本地沙盒持续观察，重点看验证段、测试段、连续亏损和数据缺口。",
    }


def _short_cycle_to_sandbox_task(row: dict[str, Any], rank: int) -> dict[str, Any]:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    validation_metrics = row.get("validationMetrics") if isinstance(row.get("validationMetrics"), dict) else {}
    test_metrics = row.get("testMetrics") if isinstance(row.get("testMetrics"), dict) else {}
    pairs = row.get("selectedPairs") if isinstance(row.get("selectedPairs"), list) else []
    recommended_pairs = [{"pair": pair} for pair in pairs]
    return {
        "taskId": row.get("taskId"),
        "strategyId": row.get("strategyId"),
        "candidateId": row.get("candidateId"),
        "title": row.get("name"),
        "displaySubtitle": f"{row.get('timeframe')} · {row.get('direction')} · 2R · 资产筛选 {len(pairs)} 个",
        "status": "planned_paper_observation",
        "rank": rank,
        "sourceReport": row.get("sourceReport"),
        "timeframe": row.get("timeframe"),
        "family": row.get("family"),
        "direction": row.get("direction"),
        "targetRewardRiskRatio": row.get("targetR") or 2.0,
        "historicalMetrics": {
            "tradeCount": metrics.get("tradeCount"),
            "winRatePct": metrics.get("winRatePct"),
            "profitFactor": metrics.get("profitFactor"),
            "expectancyR": metrics.get("expectancyR"),
            "totalReturnPct": metrics.get("totalR"),
            "maxDrawdownPct": metrics.get("maxDrawdownPctAt1PctRisk") or metrics.get("maxDrawdownPct"),
            "validationProfitFactor": validation_metrics.get("profitFactor"),
            "testProfitFactor": test_metrics.get("profitFactor"),
            "testTradeCount": test_metrics.get("tradeCount"),
        },
        "observationPlan": {
            "virtualCapitalPerStrategy": 1000,
            "riskUnitPercent": 1,
            "targetClosedSamples": 80,
            "minObservationDays": 30,
            "mode": "local_sandbox_virtual_only",
        },
        "recommendedPairs": recommended_pairs,
        "avoidUntilReviewedPairs": [],
        "weakPoints": row.get("riskNotes") if isinstance(row.get("riskNotes"), list) else [],
        "dailyLogFields": [
            "signalObserved",
            "ruleMatched",
            "pair",
            "timeframe",
            "outcomeR",
            "dataStatus",
            "dataMode",
            "notes",
        ],
        "promotionCriteria": [
            "累计闭合样本 >= 80",
            "测试段和沙盒观察 PF 继续大于 1.2",
            "连续亏损、滑点和数据缺口可解释",
            "仍保持 2R 目标，不降低盈亏比要求",
        ],
        "rejectionCriteria": [
            "沙盒观察连续亏损不可解释",
            "测试段表现无法复现",
            "资产筛选依赖验证/测试数据",
            "数据缺口无法修复",
        ],
        "sandboxSource": CONTROL_CONSOLE_SOURCE,
        "safetyNote": "Local sandbox observation only. No exchange order is created.",
    }


def build_usable_strategy_catalog(quant_path: Path | None = None) -> dict[str, Any]:
    root = (quant_path or get_quant_engine_path() or DEFAULT_QUANT_ENGINE_PATH).expanduser().resolve()
    reports_dir = root / "reports"
    low_payload = _read_json(reports_dir / LOW_FREQUENCY_TASK_PACK_REPORT)
    short_payload = _read_json(reports_dir / SHORT_CYCLE_SELECTED_REPORT)
    low_tasks = low_payload.get("paperObservationTasks") if isinstance(low_payload.get("paperObservationTasks"), list) else []
    short_candidates = (
        short_payload.get("selectedCandidates") if isinstance(short_payload.get("selectedCandidates"), list) else []
    )
    low_rows = [
        _normalize_low_frequency_task(task, index)
        for index, task in enumerate(low_tasks, start=1)
        if isinstance(task, dict)
    ]
    short_rows = [
        _normalize_short_cycle_candidate(candidate, index)
        for index, candidate in enumerate(short_candidates, start=1)
        if isinstance(candidate, dict)
    ]
    rows = sorted(low_rows + short_rows, key=lambda item: (item.get("frequencyBucket") != "short_cycle", -float(item.get("score") or 0)))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    summary = {
        "totalUsableStrategies": len(rows),
        "lowFrequencyCount": len(low_rows),
        "shortCycleCount": len(short_rows),
        "sandboxReadyCount": sum(1 for row in rows if row.get("sandboxReady")),
        "targetR": 2.0,
        "virtualCapitalPerStrategy": 1000,
        "sourceReports": [LOW_FREQUENCY_TASK_PACK_REPORT, SHORT_CYCLE_SELECTED_REPORT],
        "catalogMethod": "Merge the V13.7.21 low-frequency paper observation pack with V13.7.40 strict short-cycle candidates into a local-sandbox-only usable strategy catalog.",
        "safetyNote": "Usable means sandbox-observable, not tradable. This catalog does not enable API keys, orders, dry-run, or live trading.",
    }
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": summary,
        "strategies": rows,
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "localSandboxOnly": True,
            "usableMeansTradable": False,
            "virtualCapitalPerStrategy": 1000,
        },
    }


def build_usable_sandbox_task_pack(quant_path: Path | None = None) -> dict[str, Any]:
    root = (quant_path or get_quant_engine_path() or DEFAULT_QUANT_ENGINE_PATH).expanduser().resolve()
    reports_dir = root / "reports"
    low_payload = _read_json(reports_dir / LOW_FREQUENCY_TASK_PACK_REPORT)
    low_tasks = low_payload.get("paperObservationTasks") if isinstance(low_payload.get("paperObservationTasks"), list) else []
    safe_low_tasks = [task for task in low_tasks if isinstance(task, dict)]
    catalog = build_usable_strategy_catalog(root)
    short_rows = [
        row
        for row in catalog.get("strategies", [])
        if isinstance(row, dict) and row.get("frequencyBucket") == "short_cycle"
    ]
    short_tasks = [
        _short_cycle_to_sandbox_task(row, rank=len(safe_low_tasks) + index)
        for index, row in enumerate(short_rows, start=1)
    ]
    tasks = safe_low_tasks + short_tasks
    return {
        "reportId": "v13_7_41_usable_sandbox_task_pack",
        "version": CONTROL_CONSOLE_VERSION,
        "status": "completed",
        "generatedAt": catalog.get("generatedAt") or now_iso(),
        "source": CONTROL_CONSOLE_SOURCE,
        "summary": {
            **catalog.get("summary", {}),
            "taskCount": len(tasks),
            "lowFrequencyTaskCount": len(safe_low_tasks),
            "shortCycleTaskCount": len(short_tasks),
            "dryRunApproved": False,
            "liveTradingApproved": False,
        },
        "paperObservationTasks": tasks,
        "catalog": catalog,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyBoundary": catalog.get("safetyBoundary") or SAFETY_BOUNDARY,
    }
