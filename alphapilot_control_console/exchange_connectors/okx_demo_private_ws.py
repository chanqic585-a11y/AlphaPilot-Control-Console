"""Credential-safe OKX Demo private WebSocket runtime for account reconciliation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from types import MappingProxyType
from typing import Any, Callable, Mapping

from ..credential_runtime import OkxDemoCredentials, load_okx_demo_credentials


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
_DEFAULT_RUNTIME_LOCK = threading.Lock()
_DEFAULT_RUNTIME: "OkxDemoPrivateWsRuntime | None" = None
_DEFAULT_RUNTIME_IDENTITY: str | None = None


class OkxPrivateWsUnavailable(RuntimeError):
    """Private order channel is unavailable before any request is sent."""


class OkxPrivateWsOrderUnknown(RuntimeError):
    """A private order request may have been sent but has no authoritative ack."""


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
        self._pending_orders: dict[str, dict[str, Any]] = {}

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
        request_id = str(payload.get("id") or "")
        if request_id:
            with self._lock:
                pending = self._pending_orders.get(request_id)
                if pending is not None:
                    pending["response"] = _redact(payload)
                    pending["event"].set()
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
            for pending in self._pending_orders.values():
                pending["error"] = "private_ws_closed_before_order_ack"
                pending["event"].set()

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

    def is_order_ready(self) -> bool:
        with self._lock:
            return bool(
                self._connected
                and self._authenticated
                and self._subscribed
                and self._app is not None
            )

    def place_order(
        self,
        payload: dict[str, Any],
        *,
        timeoutSeconds: float = 2.0,
    ) -> dict[str, Any]:
        """Submit one Demo order over private WS with correlated ack handling."""

        request_id = str(payload.get("clOrdId") or "").strip()
        if not request_id:
            raise ValueError("Private WebSocket order requires clOrdId")
        timeout = float(timeoutSeconds)
        if timeout <= 0:
            raise ValueError("Private WebSocket order timeout must be positive")
        with self._lock:
            if not self.is_order_ready():
                raise OkxPrivateWsUnavailable("private_ws_order_channel_not_ready")
            if request_id in self._pending_orders:
                raise OkxPrivateWsOrderUnknown("private_ws_duplicate_request_id")
            app = self._app
            pending = {"event": threading.Event(), "response": None, "error": None}
            self._pending_orders[request_id] = pending
        try:
            try:
                app.send(json.dumps(
                    {"id": request_id, "op": "order", "args": [dict(payload)]},
                    separators=(",", ":"),
                ))
            except Exception as error:
                raise OkxPrivateWsOrderUnknown(
                    f"private_ws_order_send_unknown:{type(error).__name__}"
                ) from error
            if not pending["event"].wait(timeout):
                raise OkxPrivateWsOrderUnknown("private_ws_order_ack_timeout")
            if pending.get("error"):
                raise OkxPrivateWsOrderUnknown(str(pending["error"]))
            response = pending.get("response")
            if not isinstance(response, dict):
                raise OkxPrivateWsOrderUnknown("private_ws_order_ack_invalid")
            return response
        finally:
            with self._lock:
                self._pending_orders.pop(request_id, None)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "connected": self._connected,
                "authenticated": self._authenticated,
                "subscribed": self._subscribed,
                "channels": ["orders", "positions", "account"],
                "lastChannel": self._last_channel,
                "lastError": self._last_error,
                "orderTransportReady": bool(
                    self._connected
                    and self._authenticated
                    and self._subscribed
                    and self._app is not None
                ),
                "pendingOrderAckCount": len(self._pending_orders),
                "credentialsStored": False,
                "demoOnly": True,
            }


def get_or_start_okx_demo_private_ws_runtime(
    credentials: OkxDemoCredentials,
    *,
    site: str = "global",
) -> OkxDemoPrivateWsRuntime:
    """Return one process-only private runtime for the active Demo credential set."""

    global _DEFAULT_RUNTIME, _DEFAULT_RUNTIME_IDENTITY
    identity = hashlib.sha256(
        f"{site}:{credentials.apiKey}".encode("utf-8")
    ).hexdigest()
    with _DEFAULT_RUNTIME_LOCK:
        if _DEFAULT_RUNTIME is None or _DEFAULT_RUNTIME_IDENTITY != identity:
            if _DEFAULT_RUNTIME is not None:
                _DEFAULT_RUNTIME.stop()
            _DEFAULT_RUNTIME = OkxDemoPrivateWsRuntime(credentials, site=site)
            _DEFAULT_RUNTIME_IDENTITY = identity
        runtime = _DEFAULT_RUNTIME
        runtime.start()
        return runtime


def start_okx_demo_private_order_runtime(
    environment: Mapping[str, str] | None = None,
    *,
    site: str = "global",
) -> dict[str, Any]:
    """Start the process-only Demo private channel without exposing credentials."""

    try:
        credentials = load_okx_demo_credentials(environment)
    except RuntimeError:
        return {
            "started": False,
            "blockers": ["okx_demo_runtime_credentials_incomplete"],
            "credentialsStored": False,
            "demoOnly": True,
        }
    runtime = get_or_start_okx_demo_private_ws_runtime(credentials, site=site)
    return {
        "started": True,
        "blockers": [],
        "credentialsStored": False,
        "demoOnly": True,
        "transport": runtime.status(),
    }


def stop_okx_demo_private_ws_runtime() -> None:
    global _DEFAULT_RUNTIME, _DEFAULT_RUNTIME_IDENTITY
    with _DEFAULT_RUNTIME_LOCK:
        runtime = _DEFAULT_RUNTIME
        _DEFAULT_RUNTIME = None
        _DEFAULT_RUNTIME_IDENTITY = None
    if runtime is not None:
        runtime.stop()
