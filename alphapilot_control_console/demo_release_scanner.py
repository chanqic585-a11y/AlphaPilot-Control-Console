"""Generate Demo signals only from an immutable release and OKX public data."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from typing import Any, Callable

from .exchange_connectors.public_exchange_registry import (
    fetch_okx_public_instrument_metadata,
    fetch_okx_public_market_snapshot,
)


SnapshotLoader = Callable[[str, str, int], dict[str, Any]]
MetadataLoader = Callable[[str], dict[str, Any]]
_OPERATORS = {
    "lt": lambda value, threshold: value < threshold,
    "lte": lambda value, threshold: value <= threshold,
    "gt": lambda value, threshold: value > threshold,
    "gte": lambda value, threshold: value >= threshold,
}
_TIMEFRAME_MS = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


def _ema(values: list[float], span: int) -> float | None:
    if len(values) < span:
        return None
    alpha = 2.0 / (span + 1.0)
    result = values[0]
    for value in values[1:]:
        result = alpha * value + (1.0 - alpha) * result
    return result


def _ema_series(values: list[float], span: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (span + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result


def _rsi(values: list[float], window: int = 14) -> float | None:
    if len(values) <= window:
        return None
    changes = [current - previous for previous, current in zip(values, values[1:])]
    gains = [max(value, 0.0) for value in changes[-window:]]
    losses = [max(-value, 0.0) for value in changes[-window:]]
    average_gain = sum(gains) / window
    average_loss = sum(losses) / window
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    strength = average_gain / average_loss
    return 100.0 - 100.0 / (1.0 + strength)


def _std(values: list[float]) -> float | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _factors(snapshot: dict[str, Any]) -> dict[str, float | None]:
    candles = snapshot.get("_confirmedCandles")
    rows = candles if isinstance(candles, list) else []
    closes = [float(row["close"]) for row in rows if isinstance(row, dict) and row.get("close")]
    volumes = [float(row["volume"]) for row in rows if isinstance(row, dict) and row.get("volume") is not None]
    if not closes:
        return {}
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    ema12_series = _ema_series(closes, 12)
    ema26_series = _ema_series(closes, 26)
    macd_series = [fast - slow for fast, slow in zip(ema12_series, ema26_series)]
    signal_series = _ema_series(macd_series, 9)
    macd_histogram = (
        macd_series[-1] - signal_series[-1]
        if len(closes) >= 26 and signal_series
        else None
    )
    recent20 = closes[-20:]
    band_std = _std(recent20) if len(recent20) == 20 else None
    band_mean = sum(recent20) / 20 if len(recent20) == 20 else None
    returns = [current / previous - 1.0 for previous, current in zip(closes, closes[1:]) if previous]
    atr14 = snapshot.get("atr14")
    latest = closes[-1]
    return {
        "return_1": returns[-1] if returns else None,
        "return_6": latest / closes[-7] - 1.0 if len(closes) >= 7 and closes[-7] else None,
        "volatility_12": _std(returns[-12:]) if len(returns) >= 12 else None,
        "volume_ratio_20": volumes[-1] / (sum(volumes[-20:]) / 20) if len(volumes) >= 20 and sum(volumes[-20:]) > 0 else None,
        "ema_distance_20": latest / ema20 - 1.0 if ema20 else None,
        "ema_distance_50": latest / ema50 - 1.0 if ema50 else None,
        "rsi_14": _rsi(closes),
        "macd_histogram": macd_histogram,
        "bollinger_position": (latest - band_mean) / (band_std * 2) if band_mean is not None and band_std else None,
        "atr_pct_14": float(atr14) / latest if atr14 and latest else None,
    }


def _size_signal(
    *,
    contract: dict[str, Any],
    instrument: str,
    direction: str,
    snapshot: dict[str, Any],
    metadata: dict[str, Any],
    factor_context: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    price = float(snapshot.get("price") or 0)
    atr = float(snapshot.get("atr14") or 0)
    ct_val = float(metadata.get("ctVal") or 0)
    lot_size = float(metadata.get("lotSz") or 0)
    min_size = float(metadata.get("minSz") or 0)
    if min(price, atr, ct_val, lot_size, min_size) <= 0:
        return None, "sizing_metadata_incomplete"
    limits = contract.get("riskEnvelope") if isinstance(contract.get("riskEnvelope"), dict) else {}
    equity = float(limits.get("initialEquityUsdt") or 0)
    risk_percent = float(limits.get("riskPerTradePercent") or 0)
    notional_cap = float(limits.get("maxOrderNotionalUsdt") or 0)
    risk_usdt = equity * risk_percent / 100.0
    base_quantity = min(risk_usdt / atr, notional_cap / price)
    raw_contracts = base_quantity / ct_val
    size = math.floor(raw_contracts / lot_size + 1e-12) * lot_size
    if size < min_size:
        return None, "size_below_exchange_minimum"
    notional = size * ct_val * price
    sign = 1.0 if direction == "long" else -1.0
    signal_time_ms = int(snapshot.get("latestCandleAt") or 0)
    identity = {
        "demoReleaseId": contract["demoReleaseId"],
        "strategyCandidateId": contract["strategyCandidateId"],
        "instrument": instrument,
        "direction": direction,
        "signalTimeMs": signal_time_ms,
        "factorContext": factor_context,
    }
    candidate_id = "demo_signal_" + hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    signal_time = datetime.fromtimestamp(signal_time_ms / 1000, tz=UTC).isoformat()
    strategy = contract.get("strategy") if isinstance(contract.get("strategy"), dict) else {}
    return {
        "candidateId": candidate_id,
        "strategyCandidateId": contract["strategyCandidateId"],
        "demoReleaseId": contract["demoReleaseId"],
        "source": "immutable_release_scanner_v13_20",
        "signalTime": signal_time,
        "strategyFamilyId": str(strategy.get("familyKey") or contract["strategyCandidateId"]),
        "instId": str(metadata.get("instId") or instrument),
        "side": "buy" if direction == "long" else "sell",
        "posSide": direction,
        "tdMode": "isolated",
        "ordType": "market",
        "sz": f"{size:.12f}".rstrip("0").rstrip("."),
        "entryPrice": price,
        "stopLossPrice": price - sign * atr,
        "takeProfitPrice": price + sign * atr * 2.0,
        "notionalUsdt": notional,
        "leverage": min(2, int(limits.get("defaultMaxLeverage") or 2)),
        "riskPercent": risk_percent,
        "score": 1.0,
        "correlationGroup": instrument.split("-")[0],
        "dataFresh": True,
        "liquidityPassed": True,
        "factorContext": factor_context,
    }, None


def scan_immutable_demo_release(
    contract: dict[str, Any],
    *,
    snapshot_loader: SnapshotLoader = fetch_okx_public_market_snapshot,
    metadata_loader: MetadataLoader = fetch_okx_public_instrument_metadata,
) -> dict[str, Any]:
    strategy = contract.get("strategy") if isinstance(contract.get("strategy"), dict) else {}
    market = strategy.get("marketDefinition") if isinstance(strategy.get("marketDefinition"), dict) else {}
    policy = strategy.get("forwardSignalPolicy") if isinstance(strategy.get("forwardSignalPolicy"), dict) else {}
    instruments = market.get("eligibleInstruments")
    timeframe = str(market.get("timeframe") or "")
    direction = str(policy.get("direction") or "")
    rules = policy.get("rules")
    if not isinstance(instruments, list) or not instruments or not timeframe:
        return {"signals": [], "rejections": [], "blockers": ["release_market_definition_incomplete"]}
    if direction not in {"long", "short"} or not isinstance(rules, list) or not rules:
        return {"signals": [], "rejections": [], "blockers": ["release_signal_policy_incomplete"]}
    signals: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    for instrument in sorted({str(item).upper() for item in instruments})[:20]:
        snapshot = snapshot_loader(instrument, timeframe, 100)
        metadata = metadata_loader(instrument)
        latest_ms = int(snapshot.get("latestCandleAt") or 0)
        fresh = latest_ms > 0 and now_ms - latest_ms <= _TIMEFRAME_MS.get(timeframe, 0) * 2
        spread = snapshot.get("spreadPct")
        liquid = bool(
            metadata.get("ok")
            and spread is not None
            and 0 <= float(spread) <= 0.002
        )
        if not snapshot.get("ok") or not fresh or not liquid:
            rejections.append(
                {
                    "instId": instrument,
                    "reason": "public_market_or_liquidity_gate_failed",
                    "dataFresh": fresh,
                    "liquidityPassed": liquid,
                }
            )
            continue
        factors = _factors(snapshot)
        evaluations: list[dict[str, Any]] = []
        matched = True
        for rule in rules:
            factor_id = str(rule.get("factorId") or "") if isinstance(rule, dict) else ""
            operator = str(rule.get("operator") or "") if isinstance(rule, dict) else ""
            value = factors.get(factor_id)
            try:
                threshold = float(rule.get("threshold")) if isinstance(rule, dict) else float("nan")
            except (TypeError, ValueError):
                threshold = float("nan")
            rule_matched = bool(
                value is not None
                and math.isfinite(float(value))
                and math.isfinite(threshold)
                and operator in _OPERATORS
                and _OPERATORS[operator](float(value), threshold)
            )
            evaluations.append(
                {"factorId": factor_id, "operator": operator, "threshold": threshold, "value": value, "matched": rule_matched}
            )
            matched = matched and rule_matched
        if not matched:
            rejections.append({"instId": instrument, "reason": "frozen_rules_not_matched", "rules": evaluations})
            continue
        signal, error = _size_signal(
            contract=contract,
            instrument=instrument,
            direction=direction,
            snapshot=snapshot,
            metadata=metadata,
            factor_context={"rules": evaluations, "factors": factors},
        )
        if signal is None:
            rejections.append({"instId": instrument, "reason": error})
        else:
            signals.append(signal)
    return {
        "signals": signals,
        "rejections": rejections,
        "blockers": [],
        "publicMarketOnly": True,
        "externalSignalsAccepted": False,
        "createsOrder": False,
    }
