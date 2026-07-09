from __future__ import annotations

import re
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable

from .config import SAFETY_BOUNDARY
from .exchange_connectors.public_exchange_registry import fetch_okx_public_market_snapshot
from .state_store import (
    list_auto_execution_lifecycle_events,
    list_auto_execution_records,
    now_iso,
    save_auto_execution_lifecycle_events,
)


CONTROL_CONSOLE_VERSION = "V13.10.5"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_10_5"

ACTIVE_EXECUTION_STATUSES = {"local_tp_sl_watch", "local_simulated_open"}
CLOSED_EXECUTION_STATUSES = {"take_profit_2r", "target_2r_hit", "stop_loss_1r", "stop_loss_hit", "expired_exit", "timeout_exit"}
TIMEFRAME_SECONDS = {"15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
MAX_HOLDING_BARS = {"15m": 96, "1h": 72, "4h": 42, "1d": 30}

SnapshotProvider = Callable[[str, str, int], dict[str, Any]]
_ADVANCE_LOCK = Lock()


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        if value is None or value == "":
            return fallback
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _atr_multiplier(record: dict[str, Any]) -> tuple[float, bool]:
    explicit = _optional_float(record.get("atrMultiplier"))
    if explicit is not None and explicit > 0:
        return explicit, False
    name = str(record.get("strategyName") or "")
    match = re.search(r"ATR\s*([0-9]+(?:\.[0-9]+)?)", name, re.IGNORECASE)
    if match:
        parsed = _optional_float(match.group(1))
        if parsed is not None and parsed > 0:
            return parsed, False
    return 1.0, True


def _is_short(record: dict[str, Any]) -> bool:
    return str(record.get("direction") or "").lower() == "short" or str(record.get("side") or "").lower() == "sell"


def _snapshot_key(record: dict[str, Any]) -> tuple[str, str]:
    symbol = str(record.get("symbol") or record.get("instId") or "BTC/USDT:USDT")
    timeframe = str(record.get("timeframe") or "1h").lower()
    return symbol, timeframe


def list_projected_auto_execution_records(limit: int = 500) -> list[dict[str, Any]]:
    base_records = list_auto_execution_records(limit=limit)
    events = list_auto_execution_lifecycle_events(limit=2000)
    latest_by_record: dict[str, dict[str, Any]] = {}
    for event in events:
        record_id = str(event.get("recordId") or "")
        if record_id and record_id not in latest_by_record:
            latest_by_record[record_id] = event

    projected: list[dict[str, Any]] = []
    for record in base_records:
        record_id = str(record.get("recordId") or "")
        event = latest_by_record.get(record_id)
        if not event:
            projected.append(dict(record))
            continue
        projection = event.get("projection") if isinstance(event.get("projection"), dict) else {}
        projected.append({
            **record,
            **projection,
            "latestLifecycleEventId": event.get("eventId"),
            "latestLifecycleEventType": event.get("eventType"),
            "latestLifecycleEventLabel": event.get("eventLabel"),
            "latestLifecycleEventAt": event.get("createdAt"),
        })
    return projected


def _is_active(record: dict[str, Any]) -> bool:
    execution_status = str(record.get("executionStatus") or "")
    exit_status = str(record.get("localExitStatus") or record.get("exitStatus") or "")
    return execution_status in ACTIVE_EXECUTION_STATUSES and exit_status not in CLOSED_EXECUTION_STATUSES


def _price_levels(entry_price: float, risk_unit: float, target_r: float, stop_r: float, short: bool) -> tuple[float, float]:
    if short:
        return entry_price - target_r * risk_unit, entry_price + stop_r * risk_unit
    return entry_price + target_r * risk_unit, entry_price - stop_r * risk_unit


def _current_r(entry_price: float, current_price: float, risk_unit: float, short: bool) -> float:
    movement = entry_price - current_price if short else current_price - entry_price
    return movement / risk_unit


def _iso_from_millis(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _confirmed_bar_outcome(
    snapshot: dict[str, Any],
    entry_at: str,
    entry_price: float,
    risk_unit: float,
    target_price: float,
    stop_price: float,
    target_r: float,
    stop_r: float,
    short: bool,
    previous_mfe: float,
    previous_mae: float,
) -> tuple[dict[str, Any] | None, float, float]:
    entry_dt = _parse_datetime(entry_at)
    entry_ms = int(entry_dt.timestamp() * 1000) if entry_dt else 0
    rows = snapshot.get("_confirmedCandles") if isinstance(snapshot.get("_confirmedCandles"), list) else []
    max_favorable = previous_mfe
    max_adverse = previous_mae
    for row in sorted((item for item in rows if isinstance(item, dict)), key=lambda item: int(item.get("timestamp") or 0)):
        timestamp = int(row.get("timestamp") or 0)
        if timestamp <= entry_ms:
            continue
        high = _optional_float(row.get("high"))
        low = _optional_float(row.get("low"))
        if high is None or low is None:
            continue
        favorable_r = (entry_price - low) / risk_unit if short else (high - entry_price) / risk_unit
        adverse_r = (entry_price - high) / risk_unit if short else (low - entry_price) / risk_unit
        max_favorable = max(max_favorable, favorable_r)
        max_adverse = min(max_adverse, adverse_r)
        target_hit = low <= target_price if short else high >= target_price
        stop_hit = high >= stop_price if short else low <= stop_price
        signal_at = _iso_from_millis(timestamp)
        if target_hit and stop_hit:
            return ({
                "eventType": "stop_loss_closed",
                "eventLabel": "同根确认K线双触发，保守按止损",
                "executionStatus": "stop_loss_1r",
                "localExitStatus": "stop_loss_1r",
                "resultR": -stop_r,
                "exitPrice": stop_price,
                "exitSignalAt": signal_at,
                "exitDetection": "confirmed_candle_ambiguous_stop_first",
            }, max_favorable, max_adverse)
        if stop_hit:
            return ({
                "eventType": "stop_loss_closed",
                "eventLabel": "确认K线触发 -1R",
                "executionStatus": "stop_loss_1r",
                "localExitStatus": "stop_loss_1r",
                "resultR": -stop_r,
                "exitPrice": stop_price,
                "exitSignalAt": signal_at,
                "exitDetection": "confirmed_candle_stop",
            }, max_favorable, max_adverse)
        if target_hit:
            return ({
                "eventType": "take_profit_closed",
                "eventLabel": "确认K线达到 2R",
                "executionStatus": "take_profit_2r",
                "localExitStatus": "take_profit_2r",
                "resultR": target_r,
                "exitPrice": target_price,
                "exitSignalAt": signal_at,
                "exitDetection": "confirmed_candle_target",
            }, max_favorable, max_adverse)
    return None, max_favorable, max_adverse


def _market_snapshot_for_event(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "exchange": "okx",
        "publicOnly": True,
        "symbol": snapshot.get("symbol"),
        "instId": snapshot.get("instId"),
        "timeframe": snapshot.get("timeframe"),
        "price": snapshot.get("price"),
        "atr14": snapshot.get("atr14"),
        "candleCount": snapshot.get("candleCount"),
        "confirmedCandleCount": snapshot.get("confirmedCandleCount"),
        "latestCandleAt": snapshot.get("latestCandleAt"),
        "generatedAt": snapshot.get("generatedAt"),
        "apiKeyUsed": False,
        "privateEndpointsUsed": False,
    }


def _event(
    record: dict[str, Any],
    event_type: str,
    event_label: str,
    projection: dict[str, Any],
    snapshot: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    return {
        "recordId": record.get("recordId"),
        "strategyId": record.get("strategyId"),
        "strategyName": record.get("strategyName"),
        "symbol": record.get("symbol") or record.get("instId"),
        "direction": record.get("direction"),
        "eventType": event_type,
        "eventLabel": event_label,
        "projection": projection,
        "marketSnapshot": _market_snapshot_for_event(snapshot),
        "createdAt": created_at,
        "source": CONTROL_CONSOLE_SOURCE,
        "apiKeyUsed": False,
        "ordersCreated": False,
        "demoOrderCreated": False,
        "liveTrading": False,
    }


def _initialize_reference(
    record: dict[str, Any],
    snapshot: dict[str, Any],
    created_at: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    price = _optional_float(snapshot.get("price"))
    atr14 = _optional_float(snapshot.get("atr14"))
    if price is None or price <= 0:
        return None, _failure(record, "缺少可用的 OKX 公共 ticker 价格")
    if atr14 is None or atr14 <= 0:
        return None, _failure(record, "确认 K 线不足，无法计算 ATR14")
    multiplier, fallback_used = _atr_multiplier(record)
    risk_unit = atr14 * multiplier
    if risk_unit <= 0:
        return None, _failure(record, "ATR 风险单位无效")
    target_r = max(_safe_float(record.get("targetR"), 2.0), 2.0)
    policy = record.get("tpSlPolicy") if isinstance(record.get("tpSlPolicy"), dict) else {}
    stop_r = max(_safe_float(policy.get("stopLossR"), 1.0), 0.1)
    short = _is_short(record)
    target_price, stop_price = _price_levels(price, risk_unit, target_r, stop_r, short)
    projection = {
        "entryReferencePrice": price,
        "entryPrice": price,
        "entryReferenceAt": created_at,
        "entryAt": created_at,
        "entryReferenceLabel": "首次公共行情推进建立的本地观察基准，不是历史成交价",
        "currentPrice": price,
        "currentR": 0.0,
        "atr14": atr14,
        "atrMultiplier": multiplier,
        "atrMultiplierFallbackUsed": fallback_used,
        "riskUnitPrice": risk_unit,
        "riskModel": "ATR14 × 策略 ATR 倍数",
        "targetR": target_r,
        "stopR": stop_r,
        "targetPrice": target_price,
        "stopPrice": stop_price,
        "maxFavorableR": 0.0,
        "maxAdverseR": 0.0,
        "executionStatus": "local_tp_sl_watch",
        "localExitStatus": None,
        "updatedAt": created_at,
    }
    event = _event(record, "reference_initialized", "本地观察基准已建立", projection, snapshot, created_at)
    result = {
        "recordId": record.get("recordId"),
        "strategyName": record.get("strategyName"),
        "symbol": record.get("symbol") or record.get("instId"),
        "status": "基准已建立",
        "eventLabel": "本地观察基准已建立",
        "currentR": 0.0,
        "message": "首次推进只建立公共行情基准，不判定盈利或亏损。",
    }
    return event, result


def _advance_existing(
    record: dict[str, Any],
    snapshot: dict[str, Any],
    created_at: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    entry_price = _optional_float(record.get("entryReferencePrice") or record.get("entryPrice"))
    current_price = _optional_float(snapshot.get("price"))
    if entry_price is None or entry_price <= 0:
        return _initialize_reference(record, snapshot, created_at)
    if current_price is None or current_price <= 0:
        return None, _failure(record, "缺少可用的 OKX 公共 ticker 价格")

    multiplier, fallback_used = _atr_multiplier(record)
    risk_unit = _optional_float(record.get("riskUnitPrice"))
    atr14 = _optional_float(record.get("atr14")) or _optional_float(snapshot.get("atr14"))
    if risk_unit is None or risk_unit <= 0:
        if atr14 is None or atr14 <= 0:
            return None, _failure(record, "确认 K 线不足，无法计算 ATR14")
        risk_unit = atr14 * multiplier
    if risk_unit <= 0:
        return None, _failure(record, "ATR 风险单位无效")

    target_r = max(_safe_float(record.get("targetR"), 2.0), 2.0)
    policy = record.get("tpSlPolicy") if isinstance(record.get("tpSlPolicy"), dict) else {}
    stop_r = max(_safe_float(record.get("stopR") or policy.get("stopLossR"), 1.0), 0.1)
    short = _is_short(record)
    current_r = round(_current_r(entry_price, current_price, risk_unit, short), 6)
    previous_mfe = _safe_float(record.get("maxFavorableR"), 0.0)
    previous_mae = _safe_float(record.get("maxAdverseR"), 0.0)
    target_price, stop_price = _price_levels(entry_price, risk_unit, target_r, stop_r, short)

    entry_at = str(record.get("entryReferenceAt") or record.get("entryAt") or created_at)
    bar_outcome, bar_mfe, bar_mae = _confirmed_bar_outcome(
        snapshot,
        entry_at,
        entry_price,
        risk_unit,
        target_price,
        stop_price,
        target_r,
        stop_r,
        short,
        previous_mfe,
        previous_mae,
    )
    max_favorable = max(bar_mfe, current_r)
    max_adverse = min(bar_mae, current_r)
    entry_dt = _parse_datetime(entry_at) or datetime.now(timezone.utc)
    current_dt = _parse_datetime(created_at) or datetime.now(timezone.utc)
    timeframe = str(record.get("timeframe") or "1h").lower()
    max_bars = MAX_HOLDING_BARS.get(timeframe, 72)
    max_seconds = TIMEFRAME_SECONDS.get(timeframe, 3600) * max_bars
    expired = (current_dt - entry_dt).total_seconds() >= max_seconds

    event_type = "price_marked"
    event_label = "公共价格已更新"
    execution_status = "local_tp_sl_watch"
    local_exit_status: str | None = None
    result_r: float | None = None
    exit_at: str | None = None
    exit_price: float | None = None
    exit_signal_at: str | None = None
    exit_detection: str | None = None
    if bar_outcome:
        event_type = str(bar_outcome["eventType"])
        event_label = str(bar_outcome["eventLabel"])
        execution_status = str(bar_outcome["executionStatus"])
        local_exit_status = str(bar_outcome["localExitStatus"])
        result_r = _optional_float(bar_outcome.get("resultR"))
        exit_at = created_at
        exit_price = _optional_float(bar_outcome.get("exitPrice"))
        exit_signal_at = str(bar_outcome.get("exitSignalAt") or "") or None
        exit_detection = str(bar_outcome.get("exitDetection") or "") or None
    elif current_r >= target_r:
        event_type = "take_profit_closed"
        event_label = "达到 2R"
        execution_status = "take_profit_2r"
        local_exit_status = "take_profit_2r"
        result_r = current_r
        exit_at = created_at
        exit_price = current_price
        exit_signal_at = created_at
        exit_detection = "public_ticker_target"
    elif current_r <= -stop_r:
        event_type = "stop_loss_closed"
        event_label = "触发 -1R"
        execution_status = "stop_loss_1r"
        local_exit_status = "stop_loss_1r"
        result_r = current_r
        exit_at = created_at
        exit_price = current_price
        exit_signal_at = created_at
        exit_detection = "public_ticker_stop"
    elif expired:
        event_type = "expired_closed"
        event_label = "过期退出"
        execution_status = "expired_exit"
        local_exit_status = "expired_exit"
        result_r = current_r
        exit_at = created_at
        exit_price = current_price
        exit_signal_at = created_at
        exit_detection = "timeframe_expiry"

    projection = {
        "entryReferencePrice": entry_price,
        "entryPrice": entry_price,
        "entryReferenceAt": entry_at,
        "entryAt": entry_at,
        "entryReferenceLabel": record.get("entryReferenceLabel") or "本地公共行情观察基准，不是交易所成交价",
        "currentPrice": current_price,
        "currentR": current_r,
        "atr14": atr14,
        "atrMultiplier": multiplier,
        "atrMultiplierFallbackUsed": bool(record.get("atrMultiplierFallbackUsed")) or fallback_used,
        "riskUnitPrice": risk_unit,
        "riskModel": "ATR14 × 策略 ATR 倍数",
        "targetR": target_r,
        "stopR": stop_r,
        "targetPrice": target_price,
        "stopPrice": stop_price,
        "distanceToTargetR": round(target_r - current_r, 6),
        "distanceToStopR": round(current_r + stop_r, 6),
        "maxFavorableR": max_favorable,
        "maxAdverseR": max_adverse,
        "maxHoldingBars": max_bars,
        "executionStatus": execution_status,
        "localExitStatus": local_exit_status,
        "resultR": result_r,
        "exitAt": exit_at,
        "exitPrice": exit_price,
        "exitSignalAt": exit_signal_at,
        "exitDetection": exit_detection,
        "updatedAt": created_at,
    }
    event = _event(record, event_type, event_label, projection, snapshot, created_at)
    result = {
        "recordId": record.get("recordId"),
        "strategyName": record.get("strategyName"),
        "symbol": record.get("symbol") or record.get("instId"),
        "status": event_label if local_exit_status else "本地模拟持有",
        "eventLabel": event_label,
        "currentR": current_r,
        "message": "本地生命周期已闭合。" if local_exit_status else "公共价格已更新，继续本地观察。",
    }
    return event, result


def _failure(record: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "recordId": record.get("recordId"),
        "strategyName": record.get("strategyName"),
        "symbol": record.get("symbol") or record.get("instId"),
        "status": "推进失败",
        "eventLabel": "未写入事件",
        "currentR": record.get("currentR"),
        "message": message,
    }


def advance_auto_execution_lifecycle(
    payload: dict[str, Any] | None = None,
    *,
    snapshot_provider: SnapshotProvider = fetch_okx_public_market_snapshot,
) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    max_records = max(1, min(_safe_int(payload.get("maxRecords"), 20), 50))
    with _ADVANCE_LOCK:
        return _advance_locked(max_records=max_records, snapshot_provider=snapshot_provider)


def _advance_locked(max_records: int, snapshot_provider: SnapshotProvider) -> dict[str, Any]:
    projected_before = list_projected_auto_execution_records(limit=500)
    active_records = [row for row in projected_before if _is_active(row)][:max_records]
    run_at = now_iso()
    snapshots: dict[tuple[str, str], dict[str, Any]] = {}
    events: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    for record in active_records:
        key = _snapshot_key(record)
        if key not in snapshots:
            try:
                snapshots[key] = snapshot_provider(key[0], key[1], 100)
            except Exception as exc:  # Defensive boundary around public providers.
                snapshots[key] = {"ok": False, "errors": [f"公共行情读取失败：{exc}"], "symbol": key[0], "timeframe": key[1]}
        snapshot = snapshots[key]
        if not snapshot.get("ok"):
            errors = snapshot.get("errors") if isinstance(snapshot.get("errors"), list) else []
            missing = snapshot.get("missingFields") if isinstance(snapshot.get("missingFields"), list) else []
            detail = "；".join([*(str(item) for item in errors if item), *(f"缺少{item}" for item in missing if item)])
            results.append(_failure(record, detail or "公共行情快照不可用"))
            continue
        if _optional_float(record.get("entryReferencePrice") or record.get("entryPrice")) is None:
            event, result = _initialize_reference(record, snapshot, run_at)
        else:
            event, result = _advance_existing(record, snapshot, run_at)
        results.append(result)
        if event:
            events.append(event)

    created_events = save_auto_execution_lifecycle_events(events)
    projected_after = list_projected_auto_execution_records(limit=500)
    active_after = sum(1 for row in projected_after if _is_active(row))
    event_counts: dict[str, int] = {}
    for event in created_events:
        event_type = str(event.get("eventType") or "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    closed_count = sum(event_counts.get(key, 0) for key in {"take_profit_closed", "stop_loss_closed", "expired_closed"})
    return {
        "ok": True,
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": run_at,
        "summary": {
            "activeBefore": len(active_records),
            "processedRecords": len(results),
            "eventsCreated": len(created_events),
            "referencesInitialized": event_counts.get("reference_initialized", 0),
            "pricesMarked": event_counts.get("price_marked", 0),
            "closedThisRun": closed_count,
            "takeProfitClosed": event_counts.get("take_profit_closed", 0),
            "stopLossClosed": event_counts.get("stop_loss_closed", 0),
            "expiredClosed": event_counts.get("expired_closed", 0),
            "failedRecords": sum(1 for row in results if row.get("status") == "推进失败"),
            "activeAfter": active_after,
        },
        "results": results,
        "events": created_events,
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "publicMarketOnly": True,
            "apiKeyRequired": False,
            "rawApiKeyStorageAllowed": False,
            "createsExchangeOrder": False,
            "createsDemoOrder": False,
            "exchangeDryRunExecuted": False,
            "automaticTrading": False,
        },
        "safetyNote": "推进器只读取 OKX 公共行情并追加本地模拟事件，不创建任何交易所订单。",
    }
