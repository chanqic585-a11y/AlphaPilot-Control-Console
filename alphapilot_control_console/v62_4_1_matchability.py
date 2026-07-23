"""Historical matchability replay using the frozen Demo policy contract."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Iterable

import pandas as pd

from .demo_release_scanner import (
    calculate_demo_btc_context,
    evaluate_demo_strategy_policy,
)


_FACTOR_COLUMNS = (
    "return_1",
    "return_6",
    "volatility_12",
    "volume_ratio_20",
    "ema_distance_20",
    "ema_distance_50",
    "ema_20",
    "ema_50",
    "ema_200",
    "rsi_14",
    "macd_histogram",
    "macd_histogram_prev",
    "bollinger_position",
    "bb_upper",
    "bb_lower",
    "bb_width_pct",
    "bb_width_median_120",
    "atr_pct_14",
    "atr_14",
    "open",
    "high",
    "low",
    "close",
    "prior_high_20",
    "prior_low_20",
    "return_3",
    "return_18",
    "return_42",
)


def _ema(series: pd.Series, span: int) -> pd.Series:
    result = series.ewm(span=span, adjust=False).mean()
    return result.where(series.expanding().count() >= span)


def _runtime_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    changes = close.diff()
    gains = changes.clip(lower=0).rolling(window, min_periods=window).mean()
    losses = (-changes.clip(upper=0)).rolling(window, min_periods=window).mean()
    strength = gains / losses
    result = 100.0 - 100.0 / (1.0 + strength)
    result = result.where(losses != 0, 100.0)
    return result.where((gains != 0) | (losses != 0), 50.0)


def build_factor_frame(candles: pd.DataFrame) -> pd.DataFrame:
    """Vectorize the exact factor contract used by the immutable Demo scanner."""

    required = {"timestamp_ms", "date", "open", "high", "low", "close", "volume"}
    missing = sorted(required.difference(candles.columns))
    if missing:
        raise ValueError(f"candle columns missing: {', '.join(missing)}")

    frame = candles.copy()
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    frame = frame.sort_values(["date", "timestamp_ms"]).drop_duplicates(
        subset=["timestamp_ms"], keep="last"
    )
    if "confirmed" in frame.columns:
        frame = frame.loc[frame["confirmed"].astype(str).isin({"1", "True", "true"})]
    frame = frame.reset_index(drop=True)
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    close = frame["close"]
    volume = frame["volume"]
    ema20 = _ema(close, 20)
    ema50 = _ema(close, 50)
    ema200 = _ema(close, 200)

    ema12_raw = close.ewm(span=12, adjust=False).mean()
    ema26_raw = close.ewm(span=26, adjust=False).mean()
    macd_raw = ema12_raw - ema26_raw
    signal_raw = macd_raw.ewm(span=9, adjust=False).mean()
    macd_histogram = (macd_raw - signal_raw).where(
        close.expanding().count() >= 26
    )

    band_mean = close.rolling(20, min_periods=20).mean()
    band_std = close.rolling(20, min_periods=20).std(ddof=0)
    bb_upper = band_mean + 2 * band_std
    bb_lower = band_mean - 2 * band_std
    bb_width = (4 * band_std / close * 100).where(close != 0)

    previous_close = close.shift(1)
    true_range = pd.concat(
        (
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ),
        axis=1,
    ).max(axis=1)
    true_range = true_range.where(previous_close.notna())
    atr14 = true_range.rolling(14, min_periods=14).mean().round(12)
    returns = close.pct_change(fill_method=None)
    volume_mean20 = volume.rolling(20, min_periods=20).mean()

    factors = pd.DataFrame(
        {
            "timestamp_ms": frame["timestamp_ms"].astype("int64"),
            "date": frame["date"],
            "return_1": returns,
            "return_6": close / close.shift(6) - 1.0,
            "volatility_12": returns.rolling(12, min_periods=12).std(ddof=0),
            "volume_ratio_20": (volume / volume_mean20).where(volume_mean20 > 0),
            "ema_distance_20": (close / ema20 - 1.0).where(ema20.notna()),
            "ema_distance_50": (close / ema50 - 1.0).where(ema50.notna()),
            "ema_20": ema20,
            "ema_50": ema50,
            "ema_200": ema200,
            "rsi_14": _runtime_rsi(close),
            "macd_histogram": macd_histogram,
            "macd_histogram_prev": macd_histogram.shift(1),
            "bollinger_position": ((close - band_mean) / (band_std * 2)).where(
                band_std != 0
            ),
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_width_pct": bb_width,
            "bb_width_median_120": bb_width.rolling(
                120, min_periods=60
            ).median(),
            "atr_pct_14": (atr14 / close).where(close != 0),
            "atr_14": atr14,
            "open": frame["open"],
            "high": frame["high"],
            "low": frame["low"],
            "close": close,
            "prior_high_20": frame["high"].shift(1).rolling(
                20, min_periods=20
            ).max(),
            "prior_low_20": frame["low"].shift(1).rolling(
                20, min_periods=20
            ).min(),
            "return_3": close / close.shift(3) - 1.0,
            "return_18": close / close.shift(18) - 1.0,
            "return_42": close / close.shift(42) - 1.0,
        }
    )
    return factors.reset_index(drop=True)


def _as_utc(value: str | datetime) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(
        value, str
    ) else value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _factor_dict(row: pd.Series) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for column in _FACTOR_COLUMNS:
        value = row.get(column)
        result[column] = None if pd.isna(value) else float(value)
    return result


def _window_result(
    *,
    frame: pd.DataFrame,
    btc_by_timestamp: dict[int, dict[str, float | None]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    failed_counts: dict[str, int] = {}
    matched_times: list[str] = []
    indicator_ready_count = 0
    for _, row in frame.iterrows():
        timestamp_ms = int(row["timestamp_ms"])
        btc_factors = btc_by_timestamp.get(timestamp_ms)
        if btc_factors is None:
            continue
        factors = _factor_dict(row)
        matched, checks = evaluate_demo_strategy_policy(
            factors,
            calculate_demo_btc_context(btc_factors),
            policy,
        )
        for check in checks:
            if check["checkId"] == "indicators_ready" and check["matched"]:
                indicator_ready_count += 1
            if not check["matched"]:
                check_id = str(check["checkId"])
                failed_counts[check_id] = failed_counts.get(check_id, 0) + 1
        if matched:
            matched_times.append(pd.Timestamp(row["date"]).isoformat())

    return {
        "evaluatedBarCount": int(len(frame)),
        "indicatorReadyCount": indicator_ready_count,
        "matchedSignalCount": len(matched_times),
        "firstSignalAt": matched_times[0] if matched_times else None,
        "lastSignalAt": matched_times[-1] if matched_times else None,
        "failedCheckCounts": dict(
            sorted(failed_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
    }


def evaluate_factor_frame_windows(
    *,
    candidate_id: str,
    instrument: str,
    factor_frame: pd.DataFrame,
    btc_factor_frame: pd.DataFrame,
    policy: dict[str, Any],
    as_of: str | datetime,
    windows: Iterable[int] = (30, 90),
) -> dict[str, Any]:
    """Replay a frozen policy over bounded historical windows without order access."""

    as_of_utc = _as_utc(as_of)
    source = factor_frame.loc[
        pd.to_datetime(factor_frame["date"], utc=True) <= as_of_utc
    ].copy()
    btc_source = btc_factor_frame.loc[
        pd.to_datetime(btc_factor_frame["date"], utc=True) <= as_of_utc
    ].copy()
    btc_by_timestamp = {
        int(row["timestamp_ms"]): _factor_dict(row)
        for _, row in btc_source.iterrows()
    }
    window_results: dict[str, Any] = {}
    for days in windows:
        bounded = source.loc[
            pd.to_datetime(source["date"], utc=True)
            > as_of_utc - timedelta(days=int(days))
        ]
        window_results[f"{int(days)}d"] = _window_result(
            frame=bounded,
            btc_by_timestamp=btc_by_timestamp,
            policy=policy,
        )

    return {
        "candidateId": candidate_id,
        "instrument": instrument,
        "asOf": as_of_utc.isoformat(),
        "windows": window_results,
        "securityBoundary": {
            "privateEndpointReachable": False,
            "orderClientReachable": False,
            "canCreateOrder": False,
        },
    }
