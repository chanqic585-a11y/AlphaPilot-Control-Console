"""Generate Demo signals only from an immutable release and OKX public data."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from statistics import median
from typing import Any, Callable

from .exchange_connectors.public_exchange_registry import (
    fetch_okx_public_instrument_metadata,
    fetch_okx_public_market_snapshot,
)
from .okx_market_universe import fetch_okx_usdt_swap_universe


SnapshotLoader = Callable[[str, str, int], dict[str, Any]]
MetadataLoader = Callable[[str], dict[str, Any]]
UniverseLoader = Callable[[int], dict[str, Any]]
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
    precomputed = snapshot.get("_precomputedFactors")
    if isinstance(precomputed, dict) and precomputed:
        return dict(precomputed)
    candles = snapshot.get("_confirmedCandles")
    rows = candles if isinstance(candles, list) else []
    closes = [float(row["close"]) for row in rows if isinstance(row, dict) and row.get("close")]
    opens = [float(row["open"]) for row in rows if isinstance(row, dict) and row.get("open")]
    highs = [float(row["high"]) for row in rows if isinstance(row, dict) and row.get("high")]
    lows = [float(row["low"]) for row in rows if isinstance(row, dict) and row.get("low")]
    volumes = [float(row["volume"]) for row in rows if isinstance(row, dict) and row.get("volume") is not None]
    if not closes:
        return {}
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    ema200 = _ema(closes, 200)
    ema12_series = _ema_series(closes, 12)
    ema26_series = _ema_series(closes, 26)
    macd_series = [fast - slow for fast, slow in zip(ema12_series, ema26_series)]
    signal_series = _ema_series(macd_series, 9)
    macd_histogram = (
        macd_series[-1] - signal_series[-1]
        if len(closes) >= 26 and signal_series
        else None
    )
    previous_macd_histogram = (
        macd_series[-2] - signal_series[-2]
        if len(closes) >= 27 and len(signal_series) >= 2
        else None
    )
    recent20 = closes[-20:]
    band_std = _std(recent20) if len(recent20) == 20 else None
    band_mean = sum(recent20) / 20 if len(recent20) == 20 else None
    bb_upper = band_mean + 2 * band_std if band_mean is not None and band_std is not None else None
    bb_lower = band_mean - 2 * band_std if band_mean is not None and band_std is not None else None
    bb_widths: list[float] = []
    for end in range(20, len(closes) + 1):
        window = closes[end - 20:end]
        window_std = _std(window)
        window_close = closes[end - 1]
        if window_std is not None and window_close:
            bb_widths.append((4 * window_std) / window_close * 100)
    bb_width_pct = bb_widths[-1] if bb_widths else None
    bb_width_median_120 = median(bb_widths[-120:]) if len(bb_widths) >= 60 else None
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
        "ema_20": ema20,
        "ema_50": ema50,
        "ema_200": ema200,
        "rsi_14": _rsi(closes),
        "macd_histogram": macd_histogram,
        "macd_histogram_prev": previous_macd_histogram,
        "bollinger_position": (latest - band_mean) / (band_std * 2) if band_mean is not None and band_std else None,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_width_pct": bb_width_pct,
        "bb_width_median_120": bb_width_median_120,
        "atr_pct_14": float(atr14) / latest if atr14 and latest else None,
        "atr_14": float(atr14) if atr14 else None,
        "open": opens[-1] if opens else None,
        "high": highs[-1] if highs else None,
        "low": lows[-1] if lows else None,
        "close": latest,
        "prior_high_20": max(highs[-21:-1]) if len(highs) >= 21 else None,
        "prior_low_20": min(lows[-21:-1]) if len(lows) >= 21 else None,
        "return_3": latest / closes[-4] - 1.0 if len(closes) >= 4 and closes[-4] else None,
        "return_18": latest / closes[-19] - 1.0 if len(closes) >= 19 and closes[-19] else None,
        "return_42": latest / closes[-43] - 1.0 if len(closes) >= 43 and closes[-43] else None,
    }


def _check(check_id: str, matched: bool, value: Any, target: Any) -> dict[str, Any]:
    return {"checkId": check_id, "matched": bool(matched), "value": value, "target": target}


def _btc_context(snapshot: dict[str, Any]) -> dict[str, Any]:
    factors = _factors(snapshot)
    close = factors.get("close")
    ema20 = factors.get("ema_20")
    ema50 = factors.get("ema_50")
    ema200 = factors.get("ema_200")
    labels: list[str] = []
    if all(value is not None for value in (close, ema20, ema50, ema200)):
        if float(close) > float(ema200) and float(ema20) > float(ema50):
            labels.append("bull")
        if float(close) < float(ema200) and float(ema20) < float(ema50):
            labels.append("bear")
        if float(ema50) and abs(float(ema20) / float(ema50) - 1.0) <= 0.01:
            labels.append("sideways")
    if factors.get("return_18") is not None and float(factors["return_18"]) <= -0.10:
        labels.append("crash")
    if (
        factors.get("return_42") is not None
        and float(factors["return_42"]) >= 0.10
        and ema20 is not None
        and close is not None
        and float(close) > float(ema20)
    ):
        labels.append("recovery")
    if not labels:
        labels.append("unknown")
    priority = ("crash", "bear", "recovery", "bull", "high_volatility", "sideways")
    primary = next((label for label in priority if label in labels), "unknown")
    return {
        "primaryRegime": primary,
        "labels": sorted(set(labels)),
        "return3": factors.get("return_3"),
        "return24hPct": float(factors["return_6"]) * 100 if factors.get("return_6") is not None else None,
        "return3dPct": float(factors["return_18"]) * 100 if factors.get("return_18") is not None else None,
        "factors": factors,
    }


def _between(value: Any, lower: Any, upper: Any) -> bool:
    if value is None:
        return False
    number = float(value)
    if lower is not None and number < float(lower):
        return False
    if upper is not None and number > float(upper):
        return False
    return True


def _evaluate_strategy_family_policy(
    factors: dict[str, Any],
    btc: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[bool, list[dict[str, Any]]]:
    family = str(policy.get("family") or "")
    params = policy.get("parameters") if isinstance(policy.get("parameters"), dict) else {}
    close = factors.get("close")
    ema20 = factors.get("ema_20")
    ema50 = factors.get("ema_50")
    ema200 = factors.get("ema_200")
    rsi = factors.get("rsi_14")
    volume_ratio = factors.get("volume_ratio_20")
    macd = factors.get("macd_histogram")
    macd_previous = factors.get("macd_histogram_prev")
    atr = factors.get("atr_14")
    required_ready = all(value is not None for value in (close, ema20, ema50, ema200, rsi, volume_ratio, macd, atr))
    checks = [_check("indicators_ready", required_ready, required_ready, True)]

    if family == "short_rejection":
        checks.extend(
            [
                _check("btc_not_rallying", btc.get("return3") is not None and float(btc["return3"]) < 0.012, btc.get("return3"), "< 0.012"),
                _check("below_ema200", close is not None and ema200 is not None and float(close) < float(ema200) * float(params.get("trend_tolerance") or 1.0), close, params.get("trend_tolerance")),
                _check("ema_bear_stack", ema20 is not None and ema50 is not None and float(ema20) <= float(ema50), [ema20, ema50], "ema20 <= ema50"),
                _check("upper_band_rejection", factors.get("high") is not None and factors.get("bb_upper") is not None and float(factors["high"]) >= float(factors["bb_upper"]) * (1 - float(params.get("upper_buffer") or 0)), factors.get("high"), params.get("upper_buffer")),
                _check("bear_candle", factors.get("open") is not None and close is not None and float(close) < float(factors["open"]), [factors.get("open"), close], "close < open"),
                _check("rsi_high", rsi is not None and float(rsi) >= float(params.get("rsi_high") or 0), rsi, params.get("rsi_high")),
                _check("volume_min", volume_ratio is not None and float(volume_ratio) >= float(params.get("volume_min") or 0), volume_ratio, params.get("volume_min")),
            ]
        )
        return all(row["matched"] for row in checks), checks

    allowed_regimes = [str(value) for value in params.get("btcRegimes", [])] if isinstance(params.get("btcRegimes"), list) else []
    checks.extend(
        [
            _check("btc_regime", not allowed_regimes or btc.get("primaryRegime") in allowed_regimes, btc.get("primaryRegime"), allowed_regimes),
            _check("btc_24h_floor", btc.get("return24hPct") is None or float(btc["return24hPct"]) > float(params.get("btcReturn24hMinPct") or -8), btc.get("return24hPct"), params.get("btcReturn24hMinPct", -8)),
            _check("btc_3d_floor", btc.get("return3dPct") is None or float(btc["return3dPct"]) > float(params.get("btcReturn3dMinPct") or -10), btc.get("return3dPct"), params.get("btcReturn3dMinPct", -10)),
            _check("volume_min", volume_ratio is not None and float(volume_ratio) >= float(params.get("minVolumeRatio") or 0), volume_ratio, params.get("minVolumeRatio")),
            _check("rsi_range", _between(rsi, params.get("rsiMin"), params.get("rsiMax")), rsi, [params.get("rsiMin"), params.get("rsiMax")]),
        ]
    )
    trend_up = close is not None and ema200 is not None and ema20 is not None and ema50 is not None and float(close) > float(ema200) and float(ema20) > float(ema50)
    macd_improving = macd is not None and macd_previous is not None and float(macd) > float(macd_previous)
    macd_positive_or_improving = (macd is not None and float(macd) > 0) or macd_improving
    if family in {"breakout", "squeeze_breakout"}:
        checks.extend(
            [
                _check("trend_up", trend_up, [close, ema20, ema50, ema200], "close > ema200 and ema20 > ema50"),
                _check("macd_positive_or_improving", macd_positive_or_improving, [macd, macd_previous], "> 0 or improving"),
                _check("breakout_20", close is not None and factors.get("prior_high_20") is not None and float(close) > float(factors["prior_high_20"]) * float(params.get("breakoutMultiplier") or 1.0), [close, factors.get("prior_high_20")], params.get("breakoutMultiplier")),
            ]
        )
        if family == "squeeze_breakout":
            checks.append(
                _check(
                    "bollinger_squeeze",
                    factors.get("bb_width_pct") is not None
                    and factors.get("bb_width_median_120") is not None
                    and float(factors["bb_width_pct"]) <= float(factors["bb_width_median_120"]) * float(params.get("bbWidthMultiplier") or 1.0),
                    [factors.get("bb_width_pct"), factors.get("bb_width_median_120")],
                    params.get("bbWidthMultiplier"),
                )
            )
    elif family == "mean_reversion":
        checks.extend(
            [
                _check("ema200_floor", close is not None and ema200 is not None and float(close) > float(ema200) * float(params.get("ema200FloorMultiplier") or 0.92), [close, ema200], params.get("ema200FloorMultiplier")),
                _check("near_20_low", close is not None and factors.get("prior_low_20") is not None and float(close) <= float(factors["prior_low_20"]) * float(params.get("meanReversionLowMultiplier") or 1.01), [close, factors.get("prior_low_20")], params.get("meanReversionLowMultiplier")),
            ]
        )
    else:
        checks.append(_check("supported_family", False, family, ["breakout", "squeeze_breakout", "mean_reversion", "short_rejection"]))
    return all(row["matched"] for row in checks), checks


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
    atr_multiplier = max(0.1, float(factor_context.get("atrMultiplier") or 1.0))
    target_r = max(2.0, float(factor_context.get("targetRewardRiskRatio") or 2.0))
    risk_distance = atr * atr_multiplier
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
    base_quantity = min(risk_usdt / risk_distance, notional_cap / price)
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
        "stopLossPrice": price - sign * risk_distance,
        "takeProfitPrice": price + sign * risk_distance * target_r,
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
    universe_loader: UniverseLoader = fetch_okx_usdt_swap_universe,
) -> dict[str, Any]:
    strategy = contract.get("strategy") if isinstance(contract.get("strategy"), dict) else {}
    market = strategy.get("marketDefinition") if isinstance(strategy.get("marketDefinition"), dict) else {}
    policy = strategy.get("forwardSignalPolicy") if isinstance(strategy.get("forwardSignalPolicy"), dict) else {}
    instruments = market.get("eligibleInstruments")
    universe_policy = market.get("universePolicy") if isinstance(market.get("universePolicy"), dict) else {}
    timeframe = str(market.get("timeframe") or "")
    direction = str(policy.get("direction") or "")
    rules = policy.get("rules")
    family_policy = str(policy.get("policyType") or "") == "strategy_family_params_v1"
    dynamic_universe = str(universe_policy.get("mode") or "") == "okx_usdt_linear_perpetual_full_market"
    universe: dict[str, Any]
    ranked_candidates: list[dict[str, Any]] = []
    if dynamic_universe:
        screening_limit = max(1, min(int(universe_policy.get("screeningLimit") or 20), 100))
        universe_payload = universe_loader(screening_limit)
        pool = universe_payload.get("screeningPool") if isinstance(universe_payload.get("screeningPool"), list) else []
        instruments = [
            str(row.get("instId") or "").upper()
            for row in pool
            if isinstance(row, dict) and str(row.get("instId") or "").strip()
        ]
        ranked_candidates = [
            {
                "rank": index,
                "instId": str(row.get("instId") or "").upper(),
                "quoteVolumeProxy": row.get("quoteVolumeProxy"),
                "spreadPct": row.get("spreadPct"),
                "scanStatus": "pending",
                "reason": None,
            }
            for index, row in enumerate(pool, start=1)
            if isinstance(row, dict) and str(row.get("instId") or "").strip()
        ]
        universe = {
            "marketScope": universe_payload.get("marketScope") or "okx_usdt_linear_perpetual_full_market",
            "totalInstrumentCount": int(universe_payload.get("totalInstrumentCount") or 0),
            "liveUsdtLinearSwapCount": int(universe_payload.get("liveUsdtLinearSwapCount") or 0),
            "liquidityEligibleCount": int(universe_payload.get("liquidityEligibleCount") or 0),
            "screeningLimit": screening_limit,
            "screeningPoolCount": len(instruments),
            "errors": list(universe_payload.get("errors") or []),
        }
    else:
        universe = {
            "marketScope": "frozen_instrument_list",
            "totalInstrumentCount": len(instruments) if isinstance(instruments, list) else 0,
            "liveUsdtLinearSwapCount": len(instruments) if isinstance(instruments, list) else 0,
            "liquidityEligibleCount": len(instruments) if isinstance(instruments, list) else 0,
            "screeningLimit": len(instruments) if isinstance(instruments, list) else 0,
            "screeningPoolCount": len(instruments) if isinstance(instruments, list) else 0,
            "errors": [],
        }
    if not isinstance(instruments, list) or not instruments or not timeframe:
        return {"signals": [], "rejections": [], "blockers": ["release_market_definition_incomplete"]}
    family = str(policy.get("family") or "")
    parameters = policy.get("parameters") if isinstance(policy.get("parameters"), dict) else {}
    if direction not in {"long", "short"}:
        return {"signals": [], "rejections": [], "blockers": ["release_signal_policy_incomplete"]}
    if family_policy and (not family or not parameters):
        return {"signals": [], "rejections": [], "blockers": ["release_signal_policy_incomplete"]}
    if not family_policy and (not isinstance(rules, list) or not rules):
        return {"signals": [], "rejections": [], "blockers": ["release_signal_policy_incomplete"]}
    signals: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    instrument_cap = 100 if dynamic_universe else 20
    ordered_instruments = list(dict.fromkeys(str(item).upper() for item in instruments))[:instrument_cap]
    candidate_by_id = {str(row.get("instId")): row for row in ranked_candidates}
    completed = 0
    snapshot_limit = 260 if family_policy else 100
    snapshot_cache: dict[str, dict[str, Any]] = {}
    btc_context: dict[str, Any] = {}
    if family_policy:
        btc_snapshot = snapshot_loader("BTC-USDT-SWAP", timeframe, snapshot_limit)
        if btc_snapshot.get("prewarmedMarketMissing") is True:
            return {
                "signals": [],
                "rejections": [],
                "blockers": ["prewarmed_market_snapshot_missing"],
                "createsOrder": False,
            }
        snapshot_cache["BTC-USDT-SWAP"] = btc_snapshot
        btc_context = _btc_context(btc_snapshot) if btc_snapshot.get("ok") else {}
    for instrument in ordered_instruments:
        snapshot = snapshot_cache.get(instrument) or snapshot_loader(instrument, timeframe, snapshot_limit)
        if snapshot.get("prewarmedMarketMissing") is True:
            return {
                "signals": [],
                "rejections": rejections,
                "blockers": ["prewarmed_market_snapshot_missing"],
                "createsOrder": False,
            }
        metadata = metadata_loader(instrument)
        if metadata.get("prewarmedMarketMissing") is True:
            return {
                "signals": [],
                "rejections": rejections,
                "blockers": ["prewarmed_market_metadata_missing"],
                "createsOrder": False,
            }
        latest_ms = int(snapshot.get("latestCandleAt") or 0)
        fresh = latest_ms > 0 and now_ms - latest_ms <= _TIMEFRAME_MS.get(timeframe, 0) * 2
        spread = snapshot.get("spreadPct")
        liquid = bool(
            metadata.get("ok")
            and spread is not None
            and 0 <= float(spread) <= 0.002
        )
        if not snapshot.get("ok") or not fresh or not liquid:
            if instrument in candidate_by_id:
                candidate_by_id[instrument]["scanStatus"] = "rejected"
                candidate_by_id[instrument]["reason"] = "public_market_or_liquidity_gate_failed"
            rejections.append(
                {
                    "instId": instrument,
                    "reason": "public_market_or_liquidity_gate_failed",
                    "dataFresh": fresh,
                    "liquidityPassed": liquid,
                }
            )
            completed += 1
            continue
        factors = _factors(snapshot)
        evaluations: list[dict[str, Any]] = []
        if family_policy:
            matched, evaluations = _evaluate_strategy_family_policy(factors, btc_context, policy)
            factor_context = {
                "policyType": "strategy_family_params_v1",
                "family": family,
                "checks": evaluations,
                "factors": factors,
                "btcContext": btc_context,
                "atrMultiplier": parameters.get("atrMultiplier") or parameters.get("stop_atr") or 1.0,
                "targetRewardRiskRatio": parameters.get("targetRewardRiskRatio") or parameters.get("targetR") or 2.0,
            }
        else:
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
            factor_context = {"rules": evaluations, "factors": factors}
        if not matched:
            if instrument in candidate_by_id:
                candidate_by_id[instrument]["scanStatus"] = "rejected"
                candidate_by_id[instrument]["reason"] = "frozen_rules_not_matched"
            rejections.append({"instId": instrument, "reason": "frozen_rules_not_matched", "rules": evaluations})
            completed += 1
            continue
        signal, error = _size_signal(
            contract=contract,
            instrument=instrument,
            direction=direction,
            snapshot=snapshot,
            metadata=metadata,
            factor_context=factor_context,
        )
        if signal is None:
            if instrument in candidate_by_id:
                candidate_by_id[instrument]["scanStatus"] = "rejected"
                candidate_by_id[instrument]["reason"] = error
            rejections.append({"instId": instrument, "reason": error})
        else:
            if instrument in candidate_by_id:
                candidate_by_id[instrument]["scanStatus"] = "matched"
            signals.append(signal)
        completed += 1
    universe["strategyMatchedCount"] = len(signals)
    universe["rankedCandidates"] = ranked_candidates
    required = len(ordered_instruments)
    return {
        "signals": signals,
        "rejections": rejections,
        "blockers": [],
        "universe": universe,
        "progress": {
            "mode": "determinate",
            "status": "completed",
            "phase": "strategy_deep_screen",
            "label": "策略全市场深度扫描完成",
            "completed": completed,
            "required": required,
            "percent": round(completed / required * 100) if required else 0,
        },
        "publicMarketOnly": True,
        "externalSignalsAccepted": False,
        "createsOrder": False,
    }
