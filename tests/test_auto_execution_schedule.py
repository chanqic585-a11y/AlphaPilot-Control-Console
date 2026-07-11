from __future__ import annotations

import unittest
from datetime import UTC, datetime

from alphapilot_control_console.auto_execution_schedule import (
    closed_candle_key,
    next_candle_close,
    parse_timeframe_seconds,
)


class AutoExecutionScheduleTests(unittest.TestCase):
    def test_hourly_strategy_uses_the_latest_closed_candle_once(self) -> None:
        now = datetime(2026, 7, 12, 10, 37, tzinfo=UTC)

        self.assertEqual(
            closed_candle_key(now, "1h"),
            "2026-07-12T10:00:00+00:00",
        )
        self.assertEqual(
            next_candle_close(now, "1h"),
            datetime(2026, 7, 12, 11, 0, tzinfo=UTC),
        )

    def test_daily_strategy_uses_utc_boundaries(self) -> None:
        now = datetime(2026, 7, 12, 23, 59, tzinfo=UTC)

        self.assertEqual(
            closed_candle_key(now, "1d"),
            "2026-07-12T00:00:00+00:00",
        )
        self.assertEqual(
            next_candle_close(now, "1d"),
            datetime(2026, 7, 13, 0, 0, tzinfo=UTC),
        )

    def test_supported_timeframes_are_explicit_and_invalid_values_fail_closed(self) -> None:
        self.assertEqual(parse_timeframe_seconds("5m"), 300)
        self.assertEqual(parse_timeframe_seconds("15m"), 900)
        self.assertEqual(parse_timeframe_seconds("4h"), 14_400)

        for value in ("", "13m", "1M", "5min", " 1h "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_timeframe_seconds(value)


if __name__ == "__main__":
    unittest.main()
