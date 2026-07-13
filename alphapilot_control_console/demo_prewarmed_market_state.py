"""Thread-safe public market state used by low-latency Demo evaluation."""

from __future__ import annotations

import copy
import math
import threading
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Iterable

from .demo_release_scanner import calculate_demo_factors


_SENSITIVE_KEYS = {
    "apikey",
    "secretkey",
    "passphrase",
    "authorization",
    "signature",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str) and value.strip():
        try:
            result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if result.tzinfo is None:
        return result.replace(tzinfo=UTC)
    return result.astimezone(UTC)


def _assert_public_payload(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).replace("_", "").lower()
            if normalized in _SENSITIVE_KEYS and nested not in (None, False, "", 0):
                raise ValueError("credential-like field cannot enter public market state")
            _assert_public_payload(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _assert_public_payload(nested)


def _instrument(value: Any) -> str:
    return str(value or "").strip().upper()


def _timestamp(value: Any) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, result)


def _atr14(candles: list[dict[str, Any]]) -> float | None:
    if len(candles) < 15:
        return None
    true_ranges: list[float] = []
    for previous, current in zip(candles[-15:-1], candles[-14:]):
        try:
            high = float(current["high"])
            low = float(current["low"])
            previous_close = float(previous["close"])
        except (KeyError, TypeError, ValueError):
            return None
        true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return sum(true_ranges) / len(true_ranges) if true_ranges else None


def _precomputed_extras(
    extras: dict[str, Any],
    candles: list[dict[str, Any]],
) -> dict[str, Any]:
    updated = copy.deepcopy(extras)
    atr = _atr14(candles)
    if atr is not None:
        updated["atr14"] = atr
    factor_input = {**updated, "_confirmedCandles": candles}
    updated["_precomputedFactors"] = calculate_demo_factors(factor_input)
    return updated


@dataclass(frozen=True)
class ConfirmedCloseEvent:
    instrumentId: str
    timeframe: str
    candleStartMs: int
    receivedAt: str
    sequenceId: str


class FrozenDemoMarketSnapshot:
    """Immutable loader facade shared by every release in one batch."""

    def __init__(
        self,
        *,
        universe: dict[str, Any],
        metadata: dict[str, dict[str, Any]],
        snapshots: dict[tuple[str, str], dict[str, Any]],
        quotes: dict[str, dict[str, Any]],
        timeframe: str,
        frozen_at: str,
    ) -> None:
        self._universe = copy.deepcopy(universe)
        self._metadata = copy.deepcopy(metadata)
        self._snapshots = copy.deepcopy(snapshots)
        self._quotes = copy.deepcopy(quotes)
        self.timeframe = timeframe
        self.frozenAt = frozen_at

    def load_universe(self, limit: int) -> dict[str, Any]:
        payload = copy.deepcopy(self._universe)
        pool = payload.get("screeningPool") if isinstance(payload.get("screeningPool"), list) else []
        safe_limit = max(1, int(limit))
        payload["screeningPool"] = pool[:safe_limit]
        payload["screeningLimit"] = safe_limit
        payload["screeningPoolCount"] = len(payload["screeningPool"])
        return payload

    def load_snapshot(self, instrument: str, timeframe: str, limit: int) -> dict[str, Any]:
        key = (_instrument(instrument), str(timeframe))
        payload = copy.deepcopy(self._snapshots.get(key) or {})
        if not payload:
            return {
                "ok": False,
                "prewarmedMarketMissing": True,
                "instId": key[0],
                "timeframe": key[1],
                "errors": ["prewarmed_market_snapshot_missing"],
            }
        candles = payload.get("_confirmedCandles")
        if isinstance(candles, list):
            payload["_confirmedCandles"] = candles[-max(1, int(limit)):]
            payload["confirmedCandleCount"] = len(payload["_confirmedCandles"])
        return payload

    def load_metadata(self, instrument: str) -> dict[str, Any]:
        normalized = _instrument(instrument)
        payload = copy.deepcopy(self._metadata.get(normalized) or {})
        if payload:
            return payload
        return {
            "ok": False,
            "prewarmedMarketMissing": True,
            "instId": normalized,
            "errors": ["prewarmed_market_metadata_missing"],
        }

    def quote(self, instrument: str) -> dict[str, Any]:
        return copy.deepcopy(self._quotes.get(_instrument(instrument)) or {})


class DemoPrewarmedMarketState:
    def __init__(
        self,
        *,
        screening_limit: int = 100,
        minimum_history: int = 260,
        max_quote_age_seconds: float = 2.0,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.screening_limit = max(1, min(int(screening_limit), 100))
        self.minimum_history = max(1, int(minimum_history))
        self.max_quote_age_seconds = max(0.1, float(max_quote_age_seconds))
        self._clock = clock
        self._lock = threading.RLock()
        self._universe: dict[str, Any] = {}
        self._universe_instruments: tuple[str, ...] = ()
        self._required_instruments: tuple[str, ...] = ()
        self._timeframes: tuple[str, ...] = ()
        self._metadata: dict[str, dict[str, Any]] = {}
        self._quotes: dict[str, dict[str, Any]] = {}
        self._candles: dict[tuple[str, str], deque[dict[str, Any]]] = {}
        self._snapshot_extras: dict[tuple[str, str], dict[str, Any]] = {}
        self._provisional: dict[tuple[str, str, int], dict[str, Any]] = {}
        self._emitted_confirmations: set[tuple[str, str, int]] = set()

    def set_clock(self, clock: Callable[[], datetime]) -> None:
        with self._lock:
            self._clock = clock

    def seed_universe(
        self,
        payload: dict[str, Any],
        *,
        timeframes: Iterable[str],
    ) -> None:
        _assert_public_payload(payload)
        pool = payload.get("screeningPool") if isinstance(payload.get("screeningPool"), list) else []
        instruments: list[str] = []
        for row in pool:
            if not isinstance(row, dict):
                continue
            value = _instrument(row.get("instId"))
            if value and value not in instruments:
                instruments.append(value)
            if len(instruments) >= self.screening_limit:
                break
        normalized_timeframes = tuple(
            dict.fromkeys(str(value or "").strip().lower() for value in timeframes if str(value or "").strip())
        )
        required = list(instruments)
        if "BTC-USDT-SWAP" not in required:
            required.append("BTC-USDT-SWAP")
        with self._lock:
            self._universe = copy.deepcopy(payload)
            self._universe["screeningPool"] = copy.deepcopy(pool[: self.screening_limit])
            self._universe["screeningLimit"] = self.screening_limit
            self._universe["screeningPoolCount"] = len(instruments)
            self._universe_instruments = tuple(instruments)
            self._required_instruments = tuple(required)
            self._timeframes = normalized_timeframes

    def seed_metadata(self, instrument: str, payload: dict[str, Any]) -> None:
        _assert_public_payload(payload)
        normalized = _instrument(instrument)
        if not normalized:
            raise ValueError("instrument is required")
        with self._lock:
            self._metadata[normalized] = copy.deepcopy(payload)

    def seed_snapshot(
        self,
        instrument: str,
        timeframe: str,
        payload: dict[str, Any],
    ) -> None:
        _assert_public_payload(payload)
        normalized = _instrument(instrument)
        normalized_timeframe = str(timeframe or "").strip().lower()
        if not normalized or not normalized_timeframe:
            raise ValueError("instrument and timeframe are required")
        candles = payload.get("_confirmedCandles") if isinstance(payload.get("_confirmedCandles"), list) else []
        confirmed = [copy.deepcopy(row) for row in candles if isinstance(row, dict) and row.get("confirmed") is not False]
        confirmed.sort(key=lambda row: _timestamp(row.get("timestamp")))
        received_at = _as_utc(payload.get("receivedAt") or payload.get("generatedAt")) or self._clock()
        quote = {
            "instId": normalized,
            "price": payload.get("price"),
            "bidPrice": payload.get("bidPrice"),
            "askPrice": payload.get("askPrice"),
            "spreadPct": payload.get("spreadPct"),
            "receivedAt": received_at.astimezone(UTC).isoformat(),
            "liquidityPassed": True,
        }
        extras = {
            key: copy.deepcopy(value)
            for key, value in payload.items()
            if key not in {
                "_confirmedCandles",
                "_precomputedFactors",
                "price",
                "bidPrice",
                "askPrice",
                "spreadPct",
            }
        }
        extras = _precomputed_extras(extras, confirmed)
        key = (normalized, normalized_timeframe)
        with self._lock:
            self._candles[key] = deque(confirmed[-max(300, self.minimum_history):], maxlen=max(300, self.minimum_history))
            self._snapshot_extras[key] = extras
            self._quotes[normalized] = quote

    def apply_ticker(
        self,
        instrument: str,
        payload: dict[str, Any],
        *,
        received_at: datetime | None = None,
    ) -> None:
        _assert_public_payload(payload)
        normalized = _instrument(instrument)
        timestamp = (received_at or self._clock()).astimezone(UTC).isoformat()
        with self._lock:
            current = dict(self._quotes.get(normalized) or {})
            current.update(copy.deepcopy(payload))
            current["instId"] = normalized
            current["receivedAt"] = timestamp
            current.setdefault("liquidityPassed", True)
            self._quotes[normalized] = current

    def apply_candle(
        self,
        instrument: str,
        timeframe: str,
        payload: dict[str, Any],
        *,
        received_at: datetime | None = None,
    ) -> ConfirmedCloseEvent | None:
        _assert_public_payload(payload)
        normalized = _instrument(instrument)
        normalized_timeframe = str(timeframe or "").strip().lower()
        candle_start = _timestamp(payload.get("timestamp"))
        if not normalized or not normalized_timeframe or candle_start <= 0:
            raise ValueError("normalized candle identity is required")
        key = (normalized, normalized_timeframe, candle_start)
        with self._lock:
            if payload.get("confirmed") is not True:
                self._provisional[key] = copy.deepcopy(payload)
                return None
            if key in self._emitted_confirmations:
                return None
            candle_key = (normalized, normalized_timeframe)
            rows = list(self._candles.get(candle_key) or ())
            rows = [row for row in rows if _timestamp(row.get("timestamp")) != candle_start]
            rows.append(copy.deepcopy(payload))
            rows.sort(key=lambda row: _timestamp(row.get("timestamp")))
            self._candles[candle_key] = deque(rows[-max(300, self.minimum_history):], maxlen=max(300, self.minimum_history))
            self._snapshot_extras[candle_key] = _precomputed_extras(
                self._snapshot_extras.get(candle_key) or {},
                list(self._candles[candle_key]),
            )
            self._provisional.pop(key, None)
            self._emitted_confirmations.add(key)
            observed = (received_at or self._clock()).astimezone(UTC)
            return ConfirmedCloseEvent(
                instrumentId=normalized,
                timeframe=normalized_timeframe,
                candleStartMs=candle_start,
                receivedAt=observed.isoformat(),
                sequenceId=f"{normalized}:{normalized_timeframe}:{candle_start}",
            )

    def freeze_for_timeframe(
        self,
        timeframe: str,
        *,
        received_at: datetime | None = None,
    ) -> FrozenDemoMarketSnapshot:
        normalized_timeframe = str(timeframe or "").strip().lower()
        with self._lock:
            status = self._status_locked()
            if not status["warm"] or normalized_timeframe not in self._timeframes:
                raise RuntimeError("prewarmed market state is not ready")
            snapshots = {
                key: self._snapshot_payload_locked(*key)
                for key in self._candles
                if key[1] == normalized_timeframe and key[0] in self._required_instruments
            }
            return FrozenDemoMarketSnapshot(
                universe=self._universe,
                metadata=self._metadata,
                snapshots=snapshots,
                quotes=self._quotes,
                timeframe=normalized_timeframe,
                frozen_at=(received_at or self._clock()).astimezone(UTC).isoformat(),
            )

    def status(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._status_locked())

    def required_instruments(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._required_instruments)

    def timeframes(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._timeframes)

    def quote(self, instrument: str) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._quotes.get(_instrument(instrument)) or {})

    def confirmed_coverage(self, timeframe: str, candle_start_ms: int) -> dict[str, int | bool]:
        normalized_timeframe = str(timeframe or "").strip().lower()
        target = max(0, int(candle_start_ms))
        with self._lock:
            confirmed = sum(
                1
                for instrument in self._required_instruments
                if any(
                    _timestamp(row.get("timestamp")) == target
                    for row in self._candles.get((instrument, normalized_timeframe)) or ()
                )
            )
            required = len(self._required_instruments)
            return {
                "confirmed": confirmed,
                "required": required,
                "complete": required > 0 and confirmed == required,
            }

    def _snapshot_payload_locked(self, instrument: str, timeframe: str) -> dict[str, Any]:
        key = (instrument, timeframe)
        candles = [copy.deepcopy(row) for row in self._candles.get(key) or ()]
        quote = dict(self._quotes.get(instrument) or {})
        extras = copy.deepcopy(self._snapshot_extras.get(key) or {})
        latest = candles[-1] if candles else {}
        return {
            **extras,
            "ok": True,
            "source": "prewarmed_okx_public_market_v13_27_9",
            "publicOnly": True,
            "instId": instrument,
            "timeframe": timeframe,
            "price": quote.get("price") or latest.get("close"),
            "bidPrice": quote.get("bidPrice"),
            "askPrice": quote.get("askPrice"),
            "spreadPct": quote.get("spreadPct"),
            "receivedAt": quote.get("receivedAt"),
            "latestCandleAt": latest.get("timestamp"),
            "confirmedCandleCount": len(candles),
            "_confirmedCandles": candles,
            "apiKeyUsed": False,
            "privateEndpointsUsed": False,
            "ordersAllowed": False,
        }

    def _status_locked(self) -> dict[str, Any]:
        now = self._clock().astimezone(UTC)
        missing_metadata = [
            instrument
            for instrument in self._required_instruments
            if not (self._metadata.get(instrument) or {}).get("ok")
        ]
        missing_history: list[str] = []
        for instrument in self._required_instruments:
            for timeframe in self._timeframes:
                if len(self._candles.get((instrument, timeframe)) or ()) < self.minimum_history:
                    missing_history.append(f"{instrument}:{timeframe}")
        stale_quotes: list[str] = []
        for instrument in self._required_instruments:
            quote = self._quotes.get(instrument) or {}
            received_at = _as_utc(quote.get("receivedAt"))
            age = (now - received_at).total_seconds() if received_at is not None else math.inf
            if age < 0 or age > self.max_quote_age_seconds:
                stale_quotes.append(instrument)
        ready_instruments = [
            instrument
            for instrument in self._universe_instruments
            if instrument not in missing_metadata
            and instrument not in stale_quotes
            and all(
                f"{instrument}:{timeframe}" not in missing_history
                for timeframe in self._timeframes
            )
        ]
        synchronized = bool(self._universe_instruments and self._timeframes) and not missing_metadata and not missing_history
        warm = synchronized and not stale_quotes and len(self._universe_instruments) == self.screening_limit
        return {
            "source": "demo_prewarmed_market_state_v1",
            "warm": warm,
            "synchronized": synchronized,
            "screeningLimit": self.screening_limit,
            "screeningInstrumentCount": len(self._universe_instruments),
            "requiredInstrumentCount": len(self._required_instruments),
            "readyInstrumentCount": len(ready_instruments),
            "timeframes": list(self._timeframes),
            "missingMetadata": missing_metadata,
            "missingHistory": missing_history,
            "staleQuotes": stale_quotes,
            "generatedAt": now.isoformat(),
            "publicOnly": True,
            "rawCredentialsStored": False,
        }
