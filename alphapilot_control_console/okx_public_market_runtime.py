"""Public-only OKX WebSocket runtime for prewarmed Demo market evaluation."""

from __future__ import annotations

import copy
import json
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any, Callable, Iterable

from .demo_prewarmed_market_state import (
    ConfirmedCloseEvent,
    DemoPrewarmedMarketState,
)


OKX_PUBLIC_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
OKX_BUSINESS_WS_URL = "wss://ws.okx.com:8443/ws/v5/business"
_TIMEFRAME_CHANNELS = {
    "5m": "candle5m",
    "15m": "candle15m",
    "1h": "candle1H",
    "4h": "candle4H",
    "1d": "candle1D",
}
_CHANNEL_TIMEFRAMES = {value: key for key, value in _TIMEFRAME_CHANNELS.items()}
_SENSITIVE_KEYS = {"apikey", "secretkey", "passphrase", "authorization", "signature", "login"}


def _now() -> datetime:
    return datetime.now(UTC)


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _assert_public_payload(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).replace("_", "").lower()
            if normalized in _SENSITIVE_KEYS and nested not in (None, False, "", 0):
                raise ValueError("credential-like field cannot enter public WebSocket runtime")
            _assert_public_payload(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _assert_public_payload(nested)


def _release_timeframe(release: Any) -> str:
    if isinstance(release, dict):
        direct = release.get("timeframe")
        strategy = release.get("strategy") if isinstance(release.get("strategy"), dict) else {}
        market = strategy.get("marketDefinition") if isinstance(strategy.get("marketDefinition"), dict) else {}
        value = direct or market.get("timeframe")
    else:
        value = getattr(release, "timeframe", "")
    return str(value or "").strip().lower()


class OkxPublicMarketRuntime:
    def __init__(
        self,
        *,
        state: DemoPrewarmedMarketState,
        universe_loader: Callable[[int], dict[str, Any]],
        snapshot_loader: Callable[[str, str, int], dict[str, Any]],
        metadata_loader: Callable[[str], dict[str, Any]],
        websocket_factory: Callable[..., Any] | None = None,
        clock: Callable[[], datetime] = _now,
        subscription_batch_size: int = 50,
        seed_workers: int = 8,
    ) -> None:
        self.state = state
        self.universe_loader = universe_loader
        self.snapshot_loader = snapshot_loader
        self.metadata_loader = metadata_loader
        self.websocket_factory = websocket_factory
        self.clock = clock
        self.subscription_batch_size = max(1, int(subscription_batch_size))
        self.seed_workers = max(1, min(int(seed_workers), 16))
        self._lock = threading.RLock()
        self._refresh_lock = threading.Lock()
        self._listeners: list[Callable[[ConfirmedCloseEvent], None]] = []
        self._active_releases: tuple[Any, ...] = ()
        self._subscription_batches: list[dict[str, Any]] = []
        self._connections = {"public": False, "business": False}
        self._seeded = False
        self._last_error: str | None = None
        self._emitted_batch_closes: set[tuple[str, int]] = set()
        self._last_confirmed_close: dict[str, Any] | None = None
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._apps: dict[str, Any] = {}

    def refresh_subscriptions(self, releases: Iterable[Any]) -> dict[str, Any]:
        active_releases = tuple(releases)
        timeframes = tuple(
            dict.fromkeys(
                value
                for value in (_release_timeframe(release) for release in active_releases)
                if value in _TIMEFRAME_CHANNELS
            )
        )
        if not timeframes:
            raise ValueError("at least one supported Demo timeframe is required")
        universe = self.universe_loader(self.state.screening_limit)
        _assert_public_payload(universe)
        self.state.seed_universe(universe, timeframes=timeframes)
        instruments = self.state.required_instruments()
        failures: list[str] = []

        def load_metadata(instrument: str) -> tuple[str, dict[str, Any]]:
            return instrument, self.metadata_loader(instrument)

        def load_snapshot(instrument: str, timeframe: str) -> tuple[str, str, dict[str, Any]]:
            return instrument, timeframe, self.snapshot_loader(
                instrument,
                timeframe,
                max(260, self.state.minimum_history),
            )

        with ThreadPoolExecutor(max_workers=self.seed_workers) as executor:
            metadata_futures = [executor.submit(load_metadata, instrument) for instrument in instruments]
            snapshot_futures = [
                executor.submit(load_snapshot, instrument, timeframe)
                for instrument in instruments
                for timeframe in timeframes
            ]
            for future in as_completed(metadata_futures):
                try:
                    instrument, payload = future.result()
                    _assert_public_payload(payload)
                    self.state.seed_metadata(instrument, payload)
                    if not payload.get("ok"):
                        failures.append(f"metadata:{instrument}")
                except Exception as error:
                    failures.append(f"metadata:{type(error).__name__}")
            for future in as_completed(snapshot_futures):
                try:
                    instrument, timeframe, payload = future.result()
                    _assert_public_payload(payload)
                    self.state.seed_snapshot(instrument, timeframe, payload)
                    if not payload.get("ok"):
                        failures.append(f"snapshot:{instrument}:{timeframe}")
                except Exception as error:
                    failures.append(f"snapshot:{type(error).__name__}")

        batches = self._build_subscription_batches(instruments, timeframes)
        with self._lock:
            self._active_releases = active_releases
            self._subscription_batches = batches
            self._seeded = not failures and self.state.status()["synchronized"]
            self._last_error = ",".join(failures[:10]) if failures else None
        return {
            "seeded": self._seeded,
            "failures": failures,
            "marketState": self.state.status(),
            "subscriptionBatchCount": len(batches),
        }

    def _build_subscription_batches(
        self,
        instruments: tuple[str, ...],
        timeframes: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        public_args = [
            {"channel": "tickers", "instId": instrument}
            for instrument in instruments
        ]
        business_args = [
            {"channel": _TIMEFRAME_CHANNELS[timeframe], "instId": instrument}
            for timeframe in timeframes
            for instrument in instruments
        ]
        batches: list[dict[str, Any]] = []
        for url, args in (
            (OKX_PUBLIC_WS_URL, public_args),
            (OKX_BUSINESS_WS_URL, business_args),
        ):
            for index in range(0, len(args), self.subscription_batch_size):
                batches.append(
                    {
                        "url": url,
                        "payload": {
                            "id": f"ap{len(batches) + 1}",
                            "op": "subscribe",
                            "args": copy.deepcopy(args[index:index + self.subscription_batch_size]),
                        },
                    }
                )
        return batches

    def subscription_batches(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._subscription_batches)

    def add_close_listener(self, listener: Callable[[ConfirmedCloseEvent], None]) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def mark_connected(self, connection: str) -> None:
        if connection not in self._connections:
            raise ValueError("unknown public WebSocket connection")
        with self._lock:
            self._connections[connection] = True
            self._last_error = None

    def mark_disconnected(self, connection: str, reason: str) -> None:
        if connection not in self._connections:
            raise ValueError("unknown public WebSocket connection")
        with self._lock:
            self._connections[connection] = False
            self._seeded = False
            self._last_error = str(reason or "connection_lost")

    def handle_message(self, connection: str, message: str | dict[str, Any]) -> None:
        payload = json.loads(message) if isinstance(message, str) else copy.deepcopy(message)
        _assert_public_payload(payload)
        if not isinstance(payload, dict):
            raise ValueError("public WebSocket payload must be an object")
        if payload.get("event") == "error":
            self.mark_disconnected(connection, str(payload.get("code") or "subscription_error"))
            return
        arg = payload.get("arg") if isinstance(payload.get("arg"), dict) else {}
        channel = str(arg.get("channel") or "")
        instrument = str(arg.get("instId") or "").upper()
        data = payload.get("data") if isinstance(payload.get("data"), list) else []
        if channel == "tickers":
            for row in data:
                if not isinstance(row, dict):
                    continue
                bid = _number(row.get("bidPx"))
                ask = _number(row.get("askPx"))
                spread = (
                    (ask - bid) / ((ask + bid) / 2.0)
                    if bid is not None and ask is not None and bid > 0 and ask >= bid
                    else None
                )
                self.state.apply_ticker(
                    instrument,
                    {
                        "price": _number(row.get("last")),
                        "bidPrice": bid,
                        "askPrice": ask,
                        "spreadPct": spread,
                        "liquidityPassed": spread is not None and 0 <= spread <= 0.002,
                    },
                    received_at=self.clock(),
                )
            return
        timeframe = _CHANNEL_TIMEFRAMES.get(channel)
        if timeframe is None:
            return
        for row in data:
            if not isinstance(row, list) or len(row) < 9:
                continue
            normalized = {
                "timestamp": int(row[0]),
                "open": _number(row[1]),
                "high": _number(row[2]),
                "low": _number(row[3]),
                "close": _number(row[4]),
                "volume": _number(row[5]),
                "confirmed": str(row[8]) == "1",
            }
            event = self.state.apply_candle(
                instrument,
                timeframe,
                normalized,
                received_at=self.clock(),
            )
            if event is None:
                continue
            coverage = self.state.confirmed_coverage(timeframe, event.candleStartMs)
            batch_key = (timeframe, event.candleStartMs)
            with self._lock:
                if not coverage["complete"] or batch_key in self._emitted_batch_closes:
                    continue
                self._emitted_batch_closes.add(batch_key)
                listeners = tuple(self._listeners)
            batch_event = ConfirmedCloseEvent(
                instrumentId="*",
                timeframe=timeframe,
                candleStartMs=event.candleStartMs,
                receivedAt=event.receivedAt,
                sequenceId=f"{timeframe}:{event.candleStartMs}",
            )
            with self._lock:
                self._last_confirmed_close = {
                    "timeframe": batch_event.timeframe,
                    "candleStartMs": batch_event.candleStartMs,
                    "receivedAt": batch_event.receivedAt,
                    "sequenceId": batch_event.sequenceId,
                }
            for listener in listeners:
                listener(batch_event)

    def status(self) -> dict[str, Any]:
        with self._lock:
            connections = dict(self._connections)
            seeded = self._seeded
            error = self._last_error
            running = bool(self._threads) and not self._stop.is_set()
            last_confirmed_close = copy.deepcopy(self._last_confirmed_close)
        blockers: list[str] = []
        if not seeded:
            blockers.append("okx_public_market_seed_incomplete")
        if not connections["public"]:
            blockers.append("okx_public_websocket_disconnected")
        if not connections["business"]:
            blockers.append("okx_business_websocket_disconnected")
        market_status = self.state.status()
        if not market_status["warm"]:
            blockers.append("prewarmed_market_state_not_ready")
        return {
            "source": "okx_public_market_runtime_v1",
            "running": running,
            "seeded": seeded,
            "warm": not blockers,
            "synchronized": market_status["synchronized"],
            "connections": connections,
            "marketState": market_status,
            "lastConfirmedClose": last_confirmed_close,
            "blockers": list(dict.fromkeys(blockers)),
            "lastError": error,
            "publicOnly": True,
            "rawCredentialsStored": False,
        }

    def freeze_for_timeframe(
        self,
        timeframe: str,
        *,
        received_at: datetime | None = None,
    ) -> Any:
        return self.state.freeze_for_timeframe(timeframe, received_at=received_at)

    def quote(self, instrument: str) -> dict[str, Any]:
        return self.state.quote(instrument)

    def start(self) -> dict[str, Any]:
        if not self._seeded:
            raise RuntimeError("public market runtime must be seeded before start")
        with self._lock:
            if self._threads:
                return self.status()
            self._stop.clear()
            for connection, url in (
                ("public", OKX_PUBLIC_WS_URL),
                ("business", OKX_BUSINESS_WS_URL),
            ):
                thread = threading.Thread(
                    target=self._run_connection,
                    args=(connection, url),
                    name=f"alphapilot-okx-{connection}-market",
                    daemon=True,
                )
                self._threads.append(thread)
                thread.start()
        return self.status()

    def _run_connection(self, connection: str, url: str) -> None:
        factory = self.websocket_factory
        if factory is None:
            try:
                from websocket import WebSocketApp
            except ImportError as error:
                self.mark_disconnected(connection, "websocket_client_dependency_missing")
                return
            factory = WebSocketApp
        while not self._stop.is_set():
            app = factory(
                url,
                on_open=lambda socket, name=connection: self._on_open(name, socket),
                on_message=lambda _socket, message, name=connection: self.handle_message(name, message),
                on_error=lambda _socket, error, name=connection: self.mark_disconnected(name, type(error).__name__),
                on_close=lambda _socket, _code, reason, name=connection: self.mark_disconnected(name, str(reason or "closed")),
            )
            with self._lock:
                self._apps[connection] = app
            app.run_forever(ping_interval=20, ping_timeout=10)
            if not self._stop.wait(1.0):
                continue

    def _on_open(self, connection: str, app: Any) -> None:
        with self._refresh_lock:
            with self._lock:
                seeded = self._seeded
                active_releases = self._active_releases
            if not seeded:
                if not active_releases:
                    self.mark_disconnected(connection, "reconnect_without_active_releases")
                    return
                refreshed = self.refresh_subscriptions(active_releases)
                if not refreshed["seeded"]:
                    self.mark_disconnected(connection, "reconnect_seed_failed")
                    return
        self.mark_connected(connection)
        target_url = OKX_PUBLIC_WS_URL if connection == "public" else OKX_BUSINESS_WS_URL
        for batch in self.subscription_batches():
            if batch["url"] == target_url:
                app.send(json.dumps(batch["payload"], separators=(",", ":")))

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            apps = tuple(self._apps.values())
            threads = tuple(self._threads)
            self._threads = []
            self._apps = {}
        for app in apps:
            try:
                app.close()
            except Exception:
                pass
        for thread in threads:
            thread.join(timeout=2.0)
        for connection in self._connections:
            self.mark_disconnected(connection, "runtime_stopped")
