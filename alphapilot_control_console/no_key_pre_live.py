from __future__ import annotations

from collections import Counter
from typing import Any

from .config import SAFETY_BOUNDARY
from .exchange_connectors.public_exchange_registry import probe_public_exchanges
from .state_store import (
    list_local_sandbox_daily_reports,
    list_local_sandbox_health_snapshots,
    list_local_sandbox_learning_snapshots,
    list_local_sandbox_runs,
    list_no_key_pre_live_scans,
    list_no_key_pre_live_tickets,
    list_paper_observation_logs,
    now_iso,
    save_no_key_pre_live_scan,
    save_no_key_pre_live_ticket,
)
from .usable_strategy_catalog import build_usable_strategy_catalog


CONTROL_CONSOLE_VERSION = "V13.10.1"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_10_1"
MAX_LOCAL_OBSERVATION_NOTIONAL_USDT = 1000


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        if value is None:
            return fallback
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _okx_inst_id_from_pair(pair: str) -> str:
    value = (pair or "BTC/USDT:USDT").upper().replace(":USDT", "").strip()
    if "/" in value:
        base, quote = value.split("/", 1)
    elif value.endswith("USDT"):
        base, quote = value[:-4], "USDT"
    else:
        base, quote = value, "USDT"
    return f"{base}-{quote}-SWAP"


def _side_from_direction(direction: str) -> str:
    return "sell" if str(direction or "").lower() == "short" else "buy"


def _metric_pack(strategy: dict[str, Any]) -> dict[str, Any]:
    metrics = strategy.get("testMetrics")
    if not isinstance(metrics, dict):
        metrics = strategy.get("validationMetrics")
    if not isinstance(metrics, dict):
        metrics = strategy.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    return {
        "tradeCount": _safe_int(metrics.get("tradeCount")),
        "winRatePct": _safe_float(metrics.get("winRatePct")),
        "profitFactor": _safe_float(metrics.get("profitFactor")),
        "expectancyR": _safe_float(metrics.get("expectancyR")),
        "totalR": _safe_float(metrics.get("totalR")),
        "maxDrawdownR": _safe_float(metrics.get("maxDrawdownR") or metrics.get("maxDrawdownPctAt1PctRisk")),
    }


def _direction_label(direction: Any) -> str:
    value = str(direction or "").lower()
    if value == "short":
        return "空头候选"
    if value in {"long", "long_research"}:
        return "多头研究"
    if value in {"neutral", "market_neutral"}:
        return "中性研究"
    return "未知方向"


def _direction_balance(cards: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    strategy_counts = Counter(str(card.get("direction") or "unknown") for card in cards)
    candidate_counts = Counter(str(row.get("direction") or "unknown") for row in candidates)
    rows: list[dict[str, Any]] = []
    for direction in sorted(set(strategy_counts) | set(candidate_counts)):
        rows.append({
            "direction": direction,
            "label": _direction_label(direction),
            "strategyCount": int(strategy_counts.get(direction, 0)),
            "candidateCount": int(candidate_counts.get(direction, 0)),
        })
    short_candidates = candidate_counts.get("short", 0)
    long_candidates = candidate_counts.get("long", 0) + candidate_counts.get("long_research", 0)
    if short_candidates and not long_candidates:
        note = "当前公共行情候选偏空；这来自最新扫描结果，不代表策略库没有多头候选。"
    elif long_candidates and not short_candidates:
        note = "当前公共行情候选偏多；仍需按同一套 2R 和风险门槛复核。"
    else:
        note = "策略库同时保留多头和空头研究方向；公共行情扫描会随市场状态变化。"
    return {
        "rows": rows,
        "strategyDirectionCounts": dict(strategy_counts),
        "candidateDirectionCounts": dict(candidate_counts),
        "shortCandidateCount": int(short_candidates),
        "longCandidateCount": int(long_candidates),
        "note": note,
    }


def _sample_layer_summary() -> dict[str, Any]:
    logs_by_artifact = list_paper_observation_logs()
    log_rows = 0
    if isinstance(logs_by_artifact, dict):
        log_rows = sum(len(rows) for rows in logs_by_artifact.values() if isinstance(rows, list))
    runs = list_local_sandbox_runs(limit=50)
    reports = list_local_sandbox_daily_reports(limit=60)
    health_snapshots = list_local_sandbox_health_snapshots(limit=500)
    learning_snapshots = list_local_sandbox_learning_snapshots(limit=500)
    latest_report = reports[0] if reports else {}
    latest_report_summary = latest_report.get("summary") if isinstance(latest_report.get("summary"), dict) else {}
    return {
        "paperObservationLogBuckets": len(logs_by_artifact) if isinstance(logs_by_artifact, dict) else 0,
        "paperObservationLogRows": log_rows,
        "localSandboxRunCount": len(runs),
        "localSandboxDailyReportCount": len(reports),
        "localSandboxHealthSnapshotCount": len(health_snapshots),
        "localSandboxLearningSnapshotCount": len(learning_snapshots),
        "latestSandboxReportId": latest_report.get("reportId"),
        "latestSandboxDateKey": latest_report.get("dateKey"),
        "latestSandboxClosedSamples": latest_report_summary.get("totalClosedSampleCount"),
        "latestSandboxDailyR": latest_report_summary.get("dailyR"),
        "note": "旧沙盒样本仍保存在本地 state；无私钥预实盘候选是新的候选/票据层，不会覆盖旧样本。",
    }


def _universe_scope(cards: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    selected_pairs: set[str] = set()
    for card in cards:
        pairs = card.get("selectedPairs") if isinstance(card.get("selectedPairs"), list) else []
        selected_pairs.update(str(pair) for pair in pairs if pair)
    candidate_pairs = {str(row.get("symbol")) for row in candidates if row.get("symbol")}
    return {
        "currentMode": "selected_pairs_public_probe",
        "currentModeLabel": "当前是 selectedPairs 公共行情探测",
        "selectedPairCount": len(selected_pairs),
        "candidatePairCount": len(candidate_pairs),
        "marketWideScanEnabled": False,
        "nextMode": "liquidity_filtered_market_wide_scan",
        "nextModeLabel": "下一步扩展为流动性过滤后的全市场扫描",
        "note": "当前策略不是固定单一币种，但也还不是 OKX 全市场实时扫描；它先使用历史回测筛出的 selectedPairs。",
    }


def _long_candidate_lane(cards: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    long_cards = [
        card for card in cards
        if str(card.get("direction") or "").lower() in {"long", "long_research"}
    ]
    long_candidates = [
        row for row in candidates
        if str(row.get("direction") or "").lower() in {"long", "long_research"}
    ]
    return {
        "strategyCount": len(long_cards),
        "publicCandidateCount": len(long_candidates),
        "nextAction": (
            "多头策略已经在策略库中，但当前公共行情扫描未优先展开多头；下一步应增加多头优先扫描和全市场相对强势筛选。"
            if long_cards and not long_candidates
            else "继续用同一套 2R、样本数、回撤和风险规则复核多头候选。"
        ),
        "candidateFamilies": list(dict.fromkeys(str(card.get("family") or "--") for card in long_cards)),
        "watchItems": [
            "熊市震荡里的相对强势币",
            "日线超跌修复后仍保持结构的币",
            "低波压缩后放量突破的币",
            "BTC 下跌时抗跌、BTC 企稳时先反弹的币",
        ],
        "note": "多头候选不能为了平衡方向硬凑，必须通过和空头同样的回测、沙盒和 Demo 门槛。",
    }


def _plain_strategy_explanation(strategy: dict[str, Any]) -> str:
    family = str(strategy.get("family") or "").lower()
    direction = str(strategy.get("direction") or "").lower()
    timeframe = strategy.get("timeframe") or "--"
    if "short_rejection" in family:
        return f"{timeframe} 短周期反弹失败/上影拒绝观察，偏向寻找做空方向的回撤型候选。"
    if "low_frequency" in family or timeframe in {"4h", "1d"}:
        return f"{timeframe} 低频方向观察，重点看大周期趋势、回撤和风险过滤。"
    if direction == "short":
        return f"{timeframe} 空头方向候选，先观察是否出现规则匹配和风险可控样本。"
    return f"{timeframe} 多头方向候选，先观察公共行情是否支持本地策略继续跟踪。"


def _entry_context(strategy: dict[str, Any]) -> list[str]:
    family = str(strategy.get("family") or "").lower()
    timeframe = strategy.get("timeframe") or "--"
    items = [
        f"观察周期：{timeframe}",
        "只使用公共行情和本地策略报告做候选筛选",
    ]
    if "short_rejection" in family:
        items.extend([
            "关注冲高回落、上影拒绝、波动过滤后的短周期候选",
            "需要后续样本确认是否能保持 2R 目标路径",
        ])
    else:
        items.extend([
            "关注趋势方向、回撤质量和市场状态",
            "需要后续样本确认是否超过基准和本地沙盒阈值",
        ])
    return items


def _risk_notes(strategy: dict[str, Any]) -> list[str]:
    return [
        "这是无私钥预实盘观察，不是交易指令。",
        "公共行情可用不等于策略可以下单。",
        "历史回测和沙盒样本不保证未来收益。",
        "进入 OKX Demo 前仍需要凭据隔离、只读检查和人工确认。",
        f"策略来源：{strategy.get('sourceReport') or 'local usable strategy catalog'}",
    ]


def _strategy_cards(limit: int = 10) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    catalog = build_usable_strategy_catalog()
    strategies = catalog.get("strategies") if isinstance(catalog.get("strategies"), list) else []
    rows: list[dict[str, Any]] = []
    for strategy in sorted(strategies, key=lambda item: _safe_float(item.get("score")), reverse=True)[:limit]:
        metrics = _metric_pack(strategy)
        selected_pairs = strategy.get("selectedPairs") if isinstance(strategy.get("selectedPairs"), list) else []
        rows.append({
            "strategyId": strategy.get("strategyId") or strategy.get("taskId") or strategy.get("catalogId"),
            "taskId": strategy.get("taskId"),
            "name": strategy.get("name") or strategy.get("shortName") or "本地候选策略",
            "plainName": strategy.get("shortName") or strategy.get("name") or "本地候选策略",
            "family": strategy.get("family") or "--",
            "direction": strategy.get("direction") or "--",
            "side": _side_from_direction(str(strategy.get("direction") or "")),
            "timeframe": strategy.get("timeframe") or "--",
            "frequencyLabel": strategy.get("frequencyLabel") or "--",
            "targetR": _safe_float(strategy.get("targetR"), 2.0),
            "score": _safe_float(strategy.get("score")),
            "selectedPairs": selected_pairs[:12],
            "selectedPairCount": len(selected_pairs),
            "metrics": metrics,
            "explanation": _plain_strategy_explanation(strategy),
            "entryContext": _entry_context(strategy),
            "riskNotes": _risk_notes(strategy),
            "marketFit": "适合先做公共行情筛选和本地观察；不直接进入实盘。",
            "sourceReport": strategy.get("sourceReport"),
        })
    summary = catalog.get("summary") if isinstance(catalog.get("summary"), dict) else {}
    return rows, {
        "strategyCount": _safe_int(summary.get("totalUsableStrategies"), len(strategies)),
        "sandboxReadyCount": _safe_int(summary.get("sandboxReadyCount")),
        "sourceReports": summary.get("sourceReports") or [],
        "targetR": _safe_float(summary.get("targetR"), 2.0),
        "virtualCapitalPerStrategy": _safe_float(summary.get("virtualCapitalPerStrategy"), 1000),
    }


def _candidate_rows(cards: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    max_pairs_per_strategy = 3
    for pair_index in range(max_pairs_per_strategy):
        for card in cards:
            pairs = card.get("selectedPairs") if isinstance(card.get("selectedPairs"), list) else []
            if not pairs:
                pairs = ["BTC/USDT:USDT"]
            if pair_index >= len(pairs[:max_pairs_per_strategy]):
                continue
            pair = pairs[pair_index]
            inst_id = _okx_inst_id_from_pair(str(pair))
            key = (str(card.get("strategyId") or ""), inst_id)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "candidateId": f"no_key::{card.get('strategyId')}::{inst_id}",
                "strategyId": card.get("strategyId"),
                "strategyName": card.get("plainName") or card.get("name"),
                "symbol": str(pair),
                "instId": inst_id,
                "side": card.get("side"),
                "direction": card.get("direction"),
                "timeframe": card.get("timeframe"),
                "frequencyLabel": card.get("frequencyLabel"),
                "score": card.get("score"),
                "targetR": card.get("targetR"),
                "winRatePct": card.get("metrics", {}).get("winRatePct") if isinstance(card.get("metrics"), dict) else None,
                "profitFactor": card.get("metrics", {}).get("profitFactor") if isinstance(card.get("metrics"), dict) else None,
                "tradeCount": card.get("metrics", {}).get("tradeCount") if isinstance(card.get("metrics"), dict) else None,
                "marketDataStatus": "not_scanned",
                "screeningStatus": "strategy_loaded",
                "ticketStatus": "not_created",
                "reason": "策略已加载；等待公共行情扫描后再生成本地观察票据。",
                "apiKeyRequired": False,
                "ordersCreated": False,
                "selectionLayer": "balanced_strategy_first",
            })
            if len(rows) >= limit:
                return rows
    return rows


def _apply_latest_scan(candidates: list[dict[str, Any]], latest_scan: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not latest_scan:
        return candidates
    scanned = latest_scan.get("candidates") if isinstance(latest_scan.get("candidates"), list) else []
    scanned_by_id = {
        str(item.get("candidateId")): item
        for item in scanned
        if isinstance(item, dict) and item.get("candidateId")
    }
    enriched: list[dict[str, Any]] = []
    for candidate in candidates:
        match = scanned_by_id.get(str(candidate.get("candidateId")))
        enriched.append({**candidate, **match} if match else candidate)
    return enriched


def build_no_key_pre_live_workbench() -> dict[str, Any]:
    cards, catalog_summary = _strategy_cards()
    scans = list_no_key_pre_live_scans(limit=5)
    tickets = list_no_key_pre_live_tickets(limit=20)
    latest_scan = scans[0] if scans else None
    candidates = _apply_latest_scan(_candidate_rows(cards), latest_scan)
    ready = [row for row in candidates if row.get("screeningStatus") == "market_ready"]
    preferred = ready[0] if ready else (candidates[0] if candidates else None)
    direction_balance = _direction_balance(cards, candidates)
    sample_layer_summary = _sample_layer_summary()
    universe_scope = _universe_scope(cards, candidates)
    long_candidate_lane = _long_candidate_lane(cards, candidates)
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            **catalog_summary,
            "stage": "no_key_pre_live",
            "stageLabel": "无私钥预实盘准备",
            "strategyCardCount": len(cards),
            "candidateCount": len(candidates),
            "marketReadyCount": len(ready),
            "ticketCount": len(tickets),
            "latestScanAt": latest_scan.get("createdAt") if latest_scan else None,
            "preferredCandidateId": preferred.get("candidateId") if preferred else None,
            "sampleLayer": sample_layer_summary,
            "directionBalance": direction_balance,
            "universeScope": universe_scope,
            "longCandidateLane": long_candidate_lane,
            "nextAction": (
                "公共行情已有可观察候选，可以先生成本地观察票据；等 OKX Demo 凭据准备好后再做只读检查。"
                if ready else "先点击公共行情扫描；不需要 API Key，不会下单。"
            ),
        },
        "strategyCards": cards,
        "publicCandidates": candidates,
        "preferredCandidate": preferred,
        "sampleLayerSummary": sample_layer_summary,
        "directionBalance": direction_balance,
        "universeScope": universe_scope,
        "longCandidateLane": long_candidate_lane,
        "recentScans": scans,
        "recentTickets": tickets,
        "workflow": [
            {"stepId": "explain_strategy", "label": "看懂策略", "status": "ready"},
            {"stepId": "public_scan", "label": "公共行情筛选", "status": "ready" if latest_scan else "waiting"},
            {"stepId": "local_ticket", "label": "本地观察票据", "status": "ready" if ready else "waiting"},
            {"stepId": "demo_readonly", "label": "OKX Demo 只读检查", "status": "waiting_credentials"},
            {"stepId": "demo_order", "label": "Demo 小额演练", "status": "locked"},
        ],
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "publicMarketOnly": True,
            "apiKeyRequired": False,
            "rawApiKeyStorageAllowed": False,
            "createsExchangeOrder": False,
            "maxLocalObservationNotionalUsdt": MAX_LOCAL_OBSERVATION_NOTIONAL_USDT,
        },
        "safetyNote": "No-key pre-live uses local strategy reports and public market data only. It creates local observation tickets, not exchange orders.",
    }


def scan_no_key_pre_live_candidates(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    limit = max(1, min(_safe_int(payload.get("limit"), 12), 12))
    cards, catalog_summary = _strategy_cards()
    candidates = _candidate_rows(cards, limit=limit)
    scanned: list[dict[str, Any]] = []
    public_ok_count = 0
    for candidate in candidates:
        probe = probe_public_exchanges(
            exchanges=["okx"],
            symbol=str(candidate.get("symbol") or "BTC/USDT:USDT"),
            timeframe=str(candidate.get("timeframe") or "1h"),
            limit=2,
        )
        results = probe.get("results") if isinstance(probe.get("results"), list) else []
        okx = next((row for row in results if isinstance(row, dict) and row.get("exchange") == "okx"), {})
        ok = bool(okx.get("ok"))
        if ok:
            public_ok_count += 1
        scanned.append({
            **candidate,
            "marketDataStatus": "public_ok" if ok else "public_gap",
            "screeningStatus": "market_ready" if ok else "market_gap",
            "marketLatencyMs": okx.get("latencyMs"),
            "missingPublicFields": okx.get("missingPublicFields") or [],
            "publicProbeGeneratedAt": okx.get("generatedAt") or probe.get("generatedAt"),
            "reason": (
                "OKX 公共行情可用，可生成本地观察票据；仍不代表可下单。"
                if ok else "OKX 公共行情探测不完整，暂不建议生成观察票据。"
            ),
        })
    record = save_no_key_pre_live_scan({
        "candidateCount": len(scanned),
        "publicProbeCount": len(scanned),
        "publicOkCount": public_ok_count,
        "strategyCount": catalog_summary.get("strategyCount"),
        "candidates": scanned,
        "usesApiKey": False,
        "publicOnly": True,
    })
    workbench = build_no_key_pre_live_workbench()
    return {
        "ok": True,
        "scan": record,
        "noKeyPreLive": workbench,
        "safetyBoundary": workbench["safetyBoundary"],
    }


def create_no_key_observation_ticket(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    workbench = build_no_key_pre_live_workbench()
    candidates = workbench.get("publicCandidates") if isinstance(workbench.get("publicCandidates"), list) else []
    requested_id = str(payload.get("candidateId") or "").strip()
    candidate = next((item for item in candidates if str(item.get("candidateId")) == requested_id), None)
    if candidate is None:
        candidate = workbench.get("preferredCandidate") if isinstance(workbench.get("preferredCandidate"), dict) else None
    if not candidate:
        return {
            "ok": False,
            "error": "candidate_not_found",
            "noKeyPreLive": workbench,
            "safetyBoundary": workbench["safetyBoundary"],
        }
    notional = min(max(_safe_float(payload.get("notionalUsdt"), MAX_LOCAL_OBSERVATION_NOTIONAL_USDT), 1), MAX_LOCAL_OBSERVATION_NOTIONAL_USDT)
    blocked = candidate.get("screeningStatus") != "market_ready"
    ticket = save_no_key_pre_live_ticket({
        "strategyId": candidate.get("strategyId"),
        "strategyName": candidate.get("strategyName"),
        "candidateId": candidate.get("candidateId"),
        "symbol": candidate.get("symbol"),
        "instId": candidate.get("instId"),
        "side": candidate.get("side"),
        "timeframe": candidate.get("timeframe"),
        "notionalUsdt": notional,
        "ticketStatus": "blocked_market_gap" if blocked else "local_observation",
        "blockers": ["public_market_not_ready"] if blocked else [],
        "reason": candidate.get("reason"),
        "manualReviewRequired": True,
        "apiKeyUsed": False,
        "ordersCreated": False,
        "note": "Local observation ticket only. It does not submit a Demo or live exchange order.",
    })
    refreshed = build_no_key_pre_live_workbench()
    return {
        "ok": not blocked,
        "ticket": ticket,
        "noKeyPreLive": refreshed,
        "safetyBoundary": refreshed["safetyBoundary"],
    }
