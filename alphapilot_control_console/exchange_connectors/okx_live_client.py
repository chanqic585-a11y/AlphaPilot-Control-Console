"""Allowlisted OKX Live REST client with process-only credentials."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..credential_runtime import OkxLiveCredentials
from .okx_demo_client import resolve_okx_rest_url


OKX_LIVE_USER_AGENT = "AlphaPilot-Control-Console/13.25.0"
_CLIENT_ID = re.compile(r"^[A-Za-z0-9]{1,32}$")
_READ_ONLY_ENDPOINTS = {
    ("GET", "/api/v5/account/config"),
    ("GET", "/api/v5/account/instruments"),
    ("GET", "/api/v5/account/leverage-info"),
    ("GET", "/api/v5/account/balance"),
    ("GET", "/api/v5/account/positions"),
    ("GET", "/api/v5/trade/order"),
    ("GET", "/api/v5/trade/orders-pending"),
    ("GET", "/api/v5/trade/fills"),
}
_ALLOWED_ENDPOINTS = _READ_ONLY_ENDPOINTS | {
    ("POST", "/api/v5/trade/order"),
    ("POST", "/api/v5/trade/cancel-order"),
    ("POST", "/api/v5/trade/cancel-all-after"),
    ("POST", "/api/v5/trade/close-position"),
}


@dataclass(frozen=True)
class OkxLiveRequest:
    method: str
    url: str
    path: str
    query: dict[str, Any]
    body: dict[str, Any]
    headers: dict[str, str]
    timeoutSeconds: float


class LiveTransport(Protocol):
    def send(self, request: OkxLiveRequest) -> dict[str, Any]: ...


class OkxLiveError(RuntimeError):
    pass


def _compact_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _redact(value: Any) -> Any:
    sensitive = {"apikey", "secretkey", "passphrase", "ok-access-key", "ok-access-sign"}
    if isinstance(value, dict):
        return {
            key: "<redacted>" if str(key).replace("_", "").lower() in sensitive else _redact(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class UrllibLiveTransport:
    def send(self, request: OkxLiveRequest) -> dict[str, Any]:
        body_text = _compact_json(request.body) if request.body else ""
        outbound = Request(
            request.url,
            data=body_text.encode("utf-8") if body_text else None,
            headers=request.headers,
            method=request.method,
        )
        try:
            with urlopen(outbound, timeout=request.timeoutSeconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return _redact(json.loads(raw) if raw else {})
        except HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"code": str(error.code), "msg": "OKX Live HTTP request failed"}
            return _redact(payload)
        except (URLError, TimeoutError, OSError) as error:
            raise OkxLiveError(f"OKX Live network request failed: {type(error).__name__}") from error


class OkxLiveClient:
    def __init__(
        self,
        credentials: OkxLiveCredentials,
        *,
        transport: LiveTransport | None = None,
        timestampFactory: Callable[[], str] = _timestamp,
        site: str = "global",
        baseUrl: str | None = None,
        timeoutSeconds: float = 12.0,
    ):
        normalized_site = str(site or "global").strip().lower()
        resolved = resolve_okx_rest_url(normalized_site)
        if baseUrl is not None and baseUrl.rstrip("/") != resolved:
            raise ValueError(f"OKX Live REST base URL does not match the selected {normalized_site} site")
        self._credentials = credentials
        self._transport = transport or UrllibLiveTransport()
        self._timestamp_factory = timestampFactory
        self._site = normalized_site
        self._base_url = resolved
        self._timeout_seconds = timeoutSeconds

    @property
    def site(self) -> str:
        return self._site

    @staticmethod
    def read_only_endpoint_paths() -> tuple[str, ...]:
        return tuple(sorted(path for method, path in _READ_ONLY_ENDPOINTS if method == "GET"))

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_method = method.upper()
        if (normalized_method, path) not in _ALLOWED_ENDPOINTS:
            raise PermissionError(f"OKX Live endpoint is not allowlisted: {normalized_method} {path}")
        query_payload = {key: value for key, value in (query or {}).items() if value is not None}
        body_payload = dict(body or {})
        query_string = urlencode(query_payload)
        request_path = f"{path}?{query_string}" if query_string else path
        body_text = _compact_json(body_payload) if body_payload else ""
        timestamp = self._timestamp_factory()
        prehash = f"{timestamp}{normalized_method}{request_path}{body_text}"
        digest = hmac.new(
            self._credentials.secretKey.encode("utf-8"),
            prehash.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": OKX_LIVE_USER_AGENT,
            "OK-ACCESS-KEY": self._credentials.apiKey,
            "OK-ACCESS-SIGN": base64.b64encode(digest).decode("ascii"),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self._credentials.passphrase,
        }
        return _redact(
            self._transport.send(
                OkxLiveRequest(
                    normalized_method,
                    f"{self._base_url}{request_path}",
                    path,
                    query_payload,
                    body_payload,
                    headers,
                    self._timeout_seconds,
                )
            )
        )

    def get_account_config(self) -> dict[str, Any]:
        return self.request("GET", "/api/v5/account/config")

    def get_account_instruments(self, instrumentType: str = "SWAP") -> dict[str, Any]:
        return self.request(
            "GET",
            "/api/v5/account/instruments",
            query={"instType": instrumentType},
        )

    def get_leverage(self, *, instId: str, marginMode: str) -> dict[str, Any]:
        if marginMode not in {"cross", "isolated"}:
            raise ValueError("OKX Live margin mode must be cross or isolated")
        return self.request(
            "GET",
            "/api/v5/account/leverage-info",
            query={"instId": instId, "mgnMode": marginMode},
        )

    def get_balance(self, currency: str = "USDT") -> dict[str, Any]:
        return self.request("GET", "/api/v5/account/balance", query={"ccy": currency})

    def get_positions(self, instrumentId: str | None = None) -> dict[str, Any]:
        return self.request("GET", "/api/v5/account/positions", query={"instId": instrumentId, "instType": "SWAP"})

    def get_open_orders(self, instrumentId: str | None = None) -> dict[str, Any]:
        return self.request("GET", "/api/v5/trade/orders-pending", query={"instId": instrumentId, "instType": "SWAP"})

    def get_fills(self, instrumentId: str | None = None, limit: int = 100) -> dict[str, Any]:
        if not 1 <= int(limit) <= 100:
            raise ValueError("OKX Live fill limit must be between 1 and 100")
        return self.request("GET", "/api/v5/trade/fills", query={"instId": instrumentId, "instType": "SWAP", "limit": limit})

    def place_protected_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = ("instId", "tdMode", "side", "ordType", "sz", "clOrdId", "attachAlgoOrds")
        missing = [key for key in required if not payload.get(key)]
        if missing:
            raise ValueError("OKX Live protected order is missing: " + ",".join(missing))
        if payload.get("tdMode") != "isolated":
            raise ValueError("OKX Live Canary requires isolated margin")
        if not _CLIENT_ID.fullmatch(str(payload["clOrdId"])):
            raise ValueError("clOrdId must contain 1-32 case-sensitive alphanumeric characters")
        attached = payload.get("attachAlgoOrds")
        first = attached[0] if isinstance(attached, list) and attached and isinstance(attached[0], dict) else {}
        required_protection = ("tpTriggerPx", "tpOrdPx", "slTriggerPx", "slOrdPx")
        if any(not str(first.get(key) or "").strip() for key in required_protection):
            raise ValueError("OKX Live Canary requires attached take-profit and stop-loss")
        return self.request("POST", "/api/v5/trade/order", body=payload)

    def get_order(self, *, instId: str, ordId: str | None = None, clOrdId: str | None = None) -> dict[str, Any]:
        if not ordId and not clOrdId:
            raise ValueError("ordId or clOrdId is required")
        return self.request("GET", "/api/v5/trade/order", query={"instId": instId, "ordId": ordId, "clOrdId": clOrdId})

    def cancel_order(self, *, instId: str, ordId: str | None = None, clOrdId: str | None = None) -> dict[str, Any]:
        if not ordId and not clOrdId:
            raise ValueError("ordId or clOrdId is required")
        return self.request("POST", "/api/v5/trade/cancel-order", body={"instId": instId, "ordId": ordId, "clOrdId": clOrdId})

    def cancel_all_after(self, timeoutSeconds: int) -> dict[str, Any]:
        if timeoutSeconds != 0 and not 10 <= timeoutSeconds <= 120:
            raise ValueError("Cancel-all-after timeout must be 0 or between 10 and 120 seconds")
        return self.request("POST", "/api/v5/trade/cancel-all-after", body={"timeOut": str(timeoutSeconds), "tag": "alphapilot"})

    def close_position(
        self,
        *,
        instId: str,
        marginMode: str,
        posSide: str | None = None,
    ) -> dict[str, Any]:
        if not str(instId).endswith("-SWAP"):
            raise ValueError("Emergency close is limited to OKX swap instruments")
        if marginMode != "isolated":
            raise ValueError("Emergency close is limited to isolated positions")
        if posSide not in {None, "", "net", "long", "short"}:
            raise ValueError("Unsupported OKX position side")
        body = {
            "instId": str(instId),
            "mgnMode": "isolated",
            "posSide": posSide if posSide not in {None, "", "net"} else None,
            "autoCxl": True,
            "tag": "alphapilot",
        }
        return self.request("POST", "/api/v5/trade/close-position", body=body)
