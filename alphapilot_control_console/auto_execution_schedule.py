"""UTC candle scheduling helpers for automatic strategy evaluation."""

from __future__ import annotations

from datetime import UTC, datetime


TIMEFRAME_SECONDS = {
    "5m": 5 * 60,
    "15m": 15 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
}

# OKX `1D` candles close at UTC+8 midnight, which is 16:00 UTC.
TIMEFRAME_CLOSE_OFFSET_SECONDS = {"1d": 16 * 60 * 60}


def parse_timeframe_seconds(timeframe: str) -> int:
    if timeframe not in TIMEFRAME_SECONDS:
        raise ValueError(f"Unsupported automatic execution timeframe: {timeframe!r}")
    return TIMEFRAME_SECONDS[timeframe]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Automatic execution timestamps must be timezone-aware")
    return value.astimezone(UTC)


def closed_candle_key(now: datetime, timeframe: str) -> str:
    seconds = parse_timeframe_seconds(timeframe)
    epoch = int(_utc(now).timestamp())
    offset = TIMEFRAME_CLOSE_OFFSET_SECONDS.get(timeframe, 0)
    closed_at = epoch - (epoch - offset) % seconds
    return datetime.fromtimestamp(closed_at, UTC).isoformat()


def next_candle_close(now: datetime, timeframe: str) -> datetime:
    seconds = parse_timeframe_seconds(timeframe)
    epoch = int(_utc(now).timestamp())
    offset = TIMEFRAME_CLOSE_OFFSET_SECONDS.get(timeframe, 0)
    next_close = epoch - (epoch - offset) % seconds + seconds
    return datetime.fromtimestamp(next_close, UTC)
