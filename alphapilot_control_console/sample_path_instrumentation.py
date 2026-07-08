from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .config import DEFAULT_QUANT_ENGINE_PATH, get_quant_engine_path


INSTRUMENTATION_VERSION = "V13.7.46"
INSTRUMENTATION_MODE = "estimated_from_local_ohlcv_cache"
DEFAULT_FEE_RATE_ROUND_TRIP = 0.0008
DEFAULT_SLIPPAGE_RATE_ROUND_TRIP = 0.0005
DEFAULT_RISK_UNIT_PERCENT = 1.0
DEFAULT_VIRTUAL_CAPITAL = 1000.0


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed else fallback


def _digest_payload(value: Any) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    except TypeError:
        encoded = str(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _timeframe_minutes(timeframe: str) -> int:
    text = str(timeframe or "").strip().lower()
    if text.endswith("m"):
        return max(1, int(_safe_float(text[:-1], 1)))
    if text.endswith("h"):
        return max(1, int(_safe_float(text[:-1], 1)) * 60)
    if text.endswith("d"):
        return max(1, int(_safe_float(text[:-1], 1)) * 1440)
    return 60


def _lookahead_candles(timeframe: str) -> int:
    minutes = _timeframe_minutes(timeframe)
    if minutes <= 15:
        return 160
    if minutes <= 60:
        return 96
    if minutes <= 240:
        return 72
    return 45


def _quant_data_root(quant_path: Path | None = None) -> Path:
    root = quant_path or Path(str(get_quant_engine_path() or DEFAULT_QUANT_ENGINE_PATH)).expanduser().resolve()
    return root / "user_data" / "data"


def _path_from_hint(path_hint: Any, quant_path: Path | None = None) -> Path | None:
    text = str(path_hint or "").strip()
    if not text:
        return None
    normalized = text.replace("\\", "/")
    path = Path(normalized)
    if path.is_absolute():
        return path
    return _quant_data_root(quant_path) / Path(*normalized.split("/"))


def _read_ohlcv_window(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    try:
        import pandas as pd  # type: ignore

        suffix = path.suffix.lower()
        if suffix == ".feather":
            frame = pd.read_feather(path)
        elif suffix == ".csv":
            frame = pd.read_csv(path)
        elif suffix == ".json":
            frame = pd.read_json(path)
        else:
            return []
    except Exception:
        return []
    required = {"open", "high", "low", "close"}
    if not required.issubset(set(frame.columns)):
        return []
    if "date" not in frame.columns:
        frame = frame.reset_index().rename(columns={"index": "date"})
    safe = frame[["date", "open", "high", "low", "close", *(['volume'] if "volume" in frame.columns else [])]].dropna()
    return safe.to_dict("records")


def _select_entry_index(rows: list[dict[str, Any]], log: dict[str, Any], timeframe: str) -> tuple[int, int]:
    lookahead = _lookahead_candles(timeframe)
    if len(rows) <= lookahead + 2:
        return 0, max(1, len(rows) - 1)
    seed = log.get("sampleKey") or log.get("logId") or log.get("createdAt") or "sample"
    digest = int(_digest_payload(seed), 16)
    max_start = max(1, len(rows) - lookahead - 1)
    entry_index = digest % max_start
    return entry_index, lookahead


def infer_research_direction(task_or_log: dict[str, Any]) -> tuple[str, str]:
    text = " ".join(
        str(task_or_log.get(key) or "")
        for key in ("family", "title", "strategyName", "strategyId", "candidateId", "taskId")
    ).lower()
    if "short" in text or "空头" in text or "做空" in text:
        return "short", "strategy_family_inference"
    return "long", "default_research_long"


def _market_regime(entry: float, last_close: float, risk_price: float) -> str:
    if risk_price <= 0:
        return "window_unknown"
    move_r = (last_close - entry) / risk_price
    if move_r >= 2:
        return "window_uptrend"
    if move_r <= -2:
        return "window_downtrend"
    return "window_range"


def build_estimated_path_fields(
    log: dict[str, Any],
    task: dict[str, Any] | None = None,
    quant_path: Path | None = None,
) -> dict[str, Any]:
    path = _path_from_hint(log.get("dataSourcePathHint"), quant_path)
    if path is None:
        return {
            "instrumentationVersion": INSTRUMENTATION_VERSION,
            "instrumentationMode": "missing_local_ohlcv_path",
            "instrumentationStatus": "unavailable",
            "instrumentationMissingReason": "dataSourcePathHint_missing",
            "actualExchangeFill": False,
        }
    rows = _read_ohlcv_window(path)
    if len(rows) < 3:
        return {
            "instrumentationVersion": INSTRUMENTATION_VERSION,
            "instrumentationMode": "missing_local_ohlcv_rows",
            "instrumentationStatus": "unavailable",
            "instrumentationMissingReason": "ohlcv_rows_unavailable",
            "actualExchangeFill": False,
        }
    timeframe = str(log.get("timeframe") or (task or {}).get("timeframe") or "1h")
    entry_index, lookahead = _select_entry_index(rows, log, timeframe)
    window = rows[entry_index:entry_index + lookahead + 1]
    if len(window) < 2:
        window = rows[entry_index:entry_index + 2]
    entry_row = window[0]
    future_rows = window[1:] or window
    direction, direction_source = infer_research_direction({**(task or {}), **log})
    entry_price = _safe_float(entry_row.get("close"))
    if entry_price <= 0:
        return {
            "instrumentationVersion": INSTRUMENTATION_VERSION,
            "instrumentationMode": "invalid_entry_price",
            "instrumentationStatus": "unavailable",
            "instrumentationMissingReason": "entry_price_invalid",
            "actualExchangeFill": False,
        }
    risk_pct = max(_safe_float(log.get("riskUnitPercent"), DEFAULT_RISK_UNIT_PERCENT), 0.01)
    risk_price = entry_price * (risk_pct / 100)
    outcome_r = _safe_float(log.get("outcomeR"), 0.0)
    target_r = 2.0 if outcome_r >= 0 else -1.0
    if direction == "short":
        target_price = entry_price - (target_r * risk_price)
        stop_price = entry_price + risk_price
    else:
        target_price = entry_price + (target_r * risk_price)
        stop_price = entry_price - risk_price

    exit_row = future_rows[-1]
    exit_price = _safe_float(exit_row.get("close"), entry_price)
    exit_reason = "window_close_estimate"
    for row in future_rows:
        high = _safe_float(row.get("high"))
        low = _safe_float(row.get("low"))
        if direction == "short":
            if outcome_r >= 0 and low <= target_price:
                exit_row = row
                exit_price = target_price
                exit_reason = "estimated_target_threshold_hit"
                break
            if outcome_r < 0 and high >= stop_price:
                exit_row = row
                exit_price = stop_price
                exit_reason = "estimated_stop_threshold_hit"
                break
        else:
            if outcome_r >= 0 and high >= target_price:
                exit_row = row
                exit_price = target_price
                exit_reason = "estimated_target_threshold_hit"
                break
            if outcome_r < 0 and low <= stop_price:
                exit_row = row
                exit_price = stop_price
                exit_reason = "estimated_stop_threshold_hit"
                break

    highs = [_safe_float(row.get("high")) for row in future_rows]
    lows = [_safe_float(row.get("low")) for row in future_rows]
    if direction == "short":
        mfe_r = max((entry_price - low) / risk_price for low in lows) if risk_price > 0 else 0.0
        mae_r = -max((high - entry_price) / risk_price for high in highs) if risk_price > 0 else 0.0
    else:
        mfe_r = max((high - entry_price) / risk_price for high in highs) if risk_price > 0 else 0.0
        mae_r = -max((entry_price - low) / risk_price for low in lows) if risk_price > 0 else 0.0
    capital = _safe_float(log.get("virtualCapital"), DEFAULT_VIRTUAL_CAPITAL)
    risk_usd = capital * (risk_pct / 100)
    fee_estimate = capital * DEFAULT_FEE_RATE_ROUND_TRIP
    slippage_estimate = capital * DEFAULT_SLIPPAGE_RATE_ROUND_TRIP
    entry_time = str(entry_row.get("date"))
    exit_time = str(exit_row.get("date"))
    holding_minutes = max(0, (window.index(exit_row) if exit_row in window else len(window) - 1) * _timeframe_minutes(timeframe))
    last_close = _safe_float(future_rows[-1].get("close"), entry_price)
    return {
        "instrumentationVersion": INSTRUMENTATION_VERSION,
        "instrumentationMode": INSTRUMENTATION_MODE,
        "instrumentationStatus": "estimated",
        "actualExchangeFill": False,
        "isEstimatedReplay": True,
        "entryTime": entry_time,
        "exitTime": exit_time,
        "entryPrice": round(entry_price, 10),
        "exitPrice": round(exit_price, 10),
        "exitPriceSource": exit_reason,
        "direction": direction,
        "directionSource": direction_source,
        "marketRegime": _market_regime(entry_price, last_close, risk_price),
        "mfeR": round(mfe_r, 4),
        "maeR": round(mae_r, 4),
        "pathOutcomeR": round(((entry_price - exit_price) if direction == "short" else (exit_price - entry_price)) / risk_price, 4),
        "feeEstimate": round(fee_estimate, 6),
        "slippageEstimate": round(slippage_estimate, 6),
        "feeEstimateR": round(fee_estimate / risk_usd, 4) if risk_usd > 0 else None,
        "slippageEstimateR": round(slippage_estimate / risk_usd, 4) if risk_usd > 0 else None,
        "feeRateEstimate": DEFAULT_FEE_RATE_ROUND_TRIP,
        "slippageRateEstimate": DEFAULT_SLIPPAGE_RATE_ROUND_TRIP,
        "costEstimateMode": "conservative_round_trip_placeholder",
        "holdingTimeMinutes": holding_minutes,
        "replayWindowCandleCount": len(window),
        "replayWindowStart": entry_time,
        "replayWindowEnd": str(window[-1].get("date")),
    }


def enrich_log_with_estimated_path(log: dict[str, Any], task: dict[str, Any] | None = None, quant_path: Path | None = None) -> dict[str, Any]:
    if not isinstance(log, dict):
        return {}
    if log.get("instrumentationStatus") in {"estimated", "actual"}:
        return dict(log)
    return {**log, **build_estimated_path_fields(log, task=task, quant_path=quant_path)}
