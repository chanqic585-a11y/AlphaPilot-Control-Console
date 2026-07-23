from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from alphapilot_control_console.demo_release_scanner import calculate_demo_factors
from alphapilot_control_console.v62_4_1_matchability import (
    build_factor_frame,
    evaluate_factor_frame_windows,
)


def _candles(count: int = 260) -> pd.DataFrame:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []
    close = 100.0
    for index in range(count):
        close += 0.08 + ((index % 11) - 5) * 0.01
        rows.append(
            {
                "timestamp_ms": int(
                    (start + timedelta(hours=index)).timestamp() * 1000
                ),
                "date": start + timedelta(hours=index),
                "open": close - 0.04,
                "high": close + 0.25,
                "low": close - 0.25,
                "close": close,
                "volume": 1_000.0 + index * 3,
                "confirmed": 1,
            }
        )
    return pd.DataFrame(rows)


def test_vectorized_factor_frame_matches_runtime_factor_contract() -> None:
    candles = _candles()
    factors = build_factor_frame(candles)
    last = factors.iloc[-1].to_dict()
    source_rows = [
        {
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
            "volume": float(row.volume),
        }
        for row in candles.itertuples(index=False)
    ]
    runtime = calculate_demo_factors(
        {
            "_confirmedCandles": source_rows,
            "atr14": last["atr_14"],
        }
    )

    for key in (
        "ema_20",
        "ema_50",
        "ema_200",
        "rsi_14",
        "macd_histogram",
        "macd_histogram_prev",
        "bb_width_pct",
        "bb_width_median_120",
        "atr_14",
        "prior_high_20",
        "prior_low_20",
        "return_3",
        "return_18",
        "return_42",
    ):
        assert last[key] == pytest.approx(runtime[key], rel=1e-10, abs=1e-10)


def test_window_evaluation_uses_frozen_policy_and_never_creates_orders() -> None:
    candles = _candles()
    factor_frame = build_factor_frame(candles)
    btc_frame = factor_frame.copy()
    as_of = candles.iloc[-1]["date"].isoformat()
    result = evaluate_factor_frame_windows(
        candidate_id="candidate-short",
        instrument="BTC-USDT-SWAP",
        factor_frame=factor_frame,
        btc_factor_frame=btc_frame,
        policy={
            "family": "short_rejection",
            "direction": "short",
            "parameters": {
                "rsi_high": 101,
                "upper_buffer": 0,
                "volume_min": 0,
                "trend_tolerance": 10,
            },
        },
        as_of=as_of,
        windows=(30, 90),
    )

    assert result["candidateId"] == "candidate-short"
    assert result["instrument"] == "BTC-USDT-SWAP"
    assert result["windows"]["30d"]["evaluatedBarCount"] > 0
    assert result["windows"]["30d"]["matchedSignalCount"] == 0
    assert result["windows"]["90d"]["failedCheckCounts"]["rsi_high"] > 0
    assert result["securityBoundary"] == {
        "privateEndpointReachable": False,
        "orderClientReachable": False,
        "canCreateOrder": False,
    }
