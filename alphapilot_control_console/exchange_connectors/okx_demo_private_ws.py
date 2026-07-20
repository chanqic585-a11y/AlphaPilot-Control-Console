"""Credential-safe OKX Demo private WebSocket runtime for account reconciliation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from types import MappingProxyType
from typing import Any, Callable

from ..credential_runtime import OkxDemoCredentials


OKX_DEMO_PRIVATE_WS_URLS = MappingProxyType({
    "global": "wss://wspap.okx.com:8443/ws/v5/private",
    "us": "wss://wsuspap.okx.com:8443/ws/v5/private",
})
_LOGIN_PATH = "/users/self/verify"
_SUBSCRIPTIONS = (
    {"channel": "orders", "instType": "SWAP"},
    {"channel": "positions", "instType": "SWAP"},
    {"channel": "account", "ccy": "USDT"},
)
_SENSITIVE_KEYS = {"apikey", "secretkey", "passphrase", "sign", "signature"}


def resolve_okx_demo_private_ws_url(site: str = "global") -> str:
    normalized = str(site or "global").strip().lower()
    try:
        return OKX_DEMO_PRIVATE_WS_URLS[normalized]
    except KeyError as error:
        raise ValueError(f"Unsupported OKX Demo private WebSocket site: {normalized}") from error


def build_okx_private_ws_login(
    credentials: OkxDemoCredentials,
    *,
    timestamp: str,
) -> dict[str, Any]:
    prehash = f"{timestamp}GET{_LOGIN_PATH}"
    digest = hmac.new(
        credentials.secretKey.encode("utf-8"),
        prehash.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return {
        "op": "login",
        "args": [{
            "apiKey": credentials.apiKey,
            "passphrase": credentials.passphrase,
            "timestamp": timestamp,
            "sign": base64.b64encode(digest).decode("ascii"),
        }],
    }


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if str(key).replace("_", "").lower() in _SENSITIVE_KEYS else _redact(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class OkxDemoPrivateWsRuntime:
    def __init__(
        self,
        credentials: OkxDemoCredentials,
        *,
        site: str = "global",
        websocket_factory: Callable[..., Any] | None = None,
        timestamp_factory: Callable[[], str] = lambda: str(int(time.time())),
        event_listener: Callable[[dict[str, Any]], None] | None = None,
        reconnect_delays: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0),
    ) -> None:
        self._credentials = credentials
        self._url = resolve_okx_demo_private_ws_url(site)
        self._websocket_factory = websocket_factory
        self._timestamp_factory = timestamp_factory
        self._event_listener = event_listener
        self._reconnect_delays = reconnect_delays or (1.0,)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._app: Any = None
        self._connected = False
        self._authenticated = False
        self._subscribed = False
        self._last_error: str | None = None
        self._last_channel: str | None = None

    def create_app(self) -> Any:
        factory = self._websocket_factory
        if factory is None:
            try:
                from websocket import WebSocketApp
            except ImportError as error:
                raise RuntimeError("websocket-client runtime dependency is missing") from error
            factory = WebSocketApp
        app = factory(
            self._url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        with self._lock:
            self._app = app
        return app

    def _on_open(self, app: Any) -> None:
        with self._lock:
            self._connected = True
            self._authenticated = False
            self._subscribed = False
            self._last_error = None
        app.send(json.dumps(
            build_okx_private_ws_login(
                self._credentials,
                timestamp=str(self._timestamp_factory()),
            ),
            separators=(",", ":"),
        ))

    def _on_message(self, app: Any, raw_message: str) -> None:
        try:
            payload = json.loads(raw_message)
        except (TypeError, json.JSONDecodeError):
            with self._lock:
                self._last_error = "private_ws_invalid_json"
            return
        if not isinstance(payload, dict):
            with self._lock:
                self._last_error = "private_ws_invalid_payload"
            return
        event = str(payload.get("event") or "")
        if event == "login":
            code = str(payload.get("code") or "")
            if code != "0":
                with self._lock:
                    self._authenticated = False
                    self._last_error = f"private_ws_authentication_failed:{code or 'unknown'}"
                return
            with self._lock:
                self._authenticated = True
                self._last_error = None
            app.send(json.dumps(
                {"op": "subscribe", "args": list(_SUBSCRIPTIONS)},
                separators=(",", ":"),
            ))
            with self._lock:
                self._subscribed = True
            return
        if event == "error":
            with self._lock:
                self._last_error = f"private_ws_event_error:{str(payload.get('code') or 'unknown')}"
            return
        argument = payload.get("arg") if isinstance(payload.get("arg"), dict) else {}
        channel = str(argument.get("channel") or "")
        if channel in {"orders", "positions", "account"}:
            with self._lock:
                self._last_channel = channel
            if self._event_listener is not None:
                self._event_listener(_redact(payload))

    def _on_error(self, _app: Any, error: Any) -> None:
        with self._lock:
            self._last_error = f"private_ws_transport_error:{type(error).__name__}"

    def _on_close(self, _app: Any, _status_code: Any, _message: Any) -> None:
        with self._lock:
            self._connected = False
            self._authenticated = False
            self._subscribed = False

    def _run(self) -> None:
        attempt = 0
        while not self._stop.is_set():
            app = self.create_app()
            try:
                app.run_forever()
            except Exception as error:
                self._on_error(app, error)
            if self._stop.is_set():
                break
            delay = self._reconnect_delays[min(attempt, len(self._reconnect_delays) - 1)]
            attempt += 1
            self._stop.wait(max(0.0, float(delay)))

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="alphapilot-okx-demo-private-ws",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        app = self._app
        if app is not None:
            try:
                app.close()
            except Exception:
                pass
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "connected": self._connected,
                "authenticated": self._authenticated,
                "subscribed": self._subscribed,
                "channels": ["orders", "positions", "account"],
                "lastChannel": self._last_channel,
                "lastError": self._last_error,
                "credentialsStored": False,
                "demoOnly": True,
            }
