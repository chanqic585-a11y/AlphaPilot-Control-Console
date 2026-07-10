"""Small allowlisted OKX Demo REST client with injectable transport for tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..credential_runtime import OkxDemoCredentials


OKX_SITE_REST_URLS = MappingProxyType({
    "global": "https://openapi.okx.com",
    "us": "https://us.okx.com",
    "eea": "https://eea.okx.com",
})
OKX_DEMO_REST_URL = OKX_SITE_REST_URLS["global"]
_CLIENT_ID = re.compile(r"^[A-Za-z0-9]{1,32}$")
_ALLOWED_ENDPOINTS = {
    ("GET", "/api/v5/account/config"),
    ("GET", "/api/v5/account/balance"),
    ("GET", "/api/v5/account/positions"),
    ("GET", "/api/v5/trade/order"),
    ("GET", "/api/v5/trade/orders-pending"),
    ("GET", "/api/v5/trade/fills"),
    ("POST", "/api/v5/trade/order"),
    ("POST", "/api/v5/trade/cancel-order"),
    ("POST", "/api/v5/trade/cancel-all-after"),
}


def resolve_okx_rest_url(site: str = "global") -> str:
    normalized = str(site or "global").strip().lower()
    try:
        return OKX_SITE_REST_URLS[normalized]
    except KeyError as error:
        raise ValueError(f"Unsupported OKX account site: {normalized}") from error


@dataclass(frozen=True)
class OkxDemoRequest:
    method: str
    url: str
    path: str
    query: dict[str, Any]
    body: dict[str, Any]
    headers: dict[str, str]
    timeoutSeconds: float


class DemoTransport(Protocol):
    def send(self, request: OkxDemoRequest) -> dict[str, Any]: ...


class OkxDemoError(RuntimeError):
    pass


class UrllibDemoTransport:
    def send(self, request: OkxDemoRequest) -> dict[str, Any]:
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
                return json.loads(raw) if raw else {}
        except HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"code": str(error.code), "msg": "OKX Demo HTTP request failed"}
            return _redact_payload(payload)
        except (URLError, TimeoutError, OSError) as error:
            raise OkxDemoError(f"OKX Demo network request failed: {type(error).__name__}") from error


def _compact_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _redact_payload(value: Any) -> Any:
    sensitive = {"apikey", "secretkey", "passphrase", "ok-access-key", "ok-access-sign"}
    if isinstance(value, dict):
        return {
            key: "<redacted>" if str(key).replace("_", "").lower() in sensitive else _redact_payload(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    return value


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class OkxDemoClient:
    def __init__(
        self,
        credentials: OkxDemoCredentials,
        *,
        transport: DemoTransport | None = None,
        timestampFactory: Callable[[], str] = _timestamp,
        site: str = "global",
        baseUrl: str | None = None,
        timeoutSeconds: float = 12.0,
    ):
        normalized_site = str(site or "global").strip().lower()
        resolved_base_url = resolve_okx_rest_url(normalized_site)
        if baseUrl is not None and baseUrl.rstrip("/") != resolved_base_url:
            raise ValueError(f"OKX Demo REST base URL does not match the selected {normalized_site} site")
        self._credentials = credentials
        self._transport = transport or UrllibDemoTransport()
        self._timestamp_factory = timestampFactory
        self._site = normalized_site
        self._base_url = resolved_base_url
        self._timeout_seconds = timeoutSeconds

    @property
    def site(self) -> str:
        return self._site

    @property
    def base_url(self) -> str:
        return self._base_url

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
            raise PermissionError(f"OKX Demo endpoint is not allowlisted: {normalized_method} {path}")
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
            "OK-ACCESS-KEY": self._credentials.apiKey,
            "OK-ACCESS-SIGN": base64.b64encode(digest).decode("ascii"),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self._credentials.passphrase,
            "x-simulated-trading": "1",
        }
        response = self._transport.send(
            OkxDemoRequest(
                method=normalized_method,
                url=f"{self._base_url}{request_path}",
                path=path,
                query=query_payload,
                body=body_payload,
                headers=headers,
                timeoutSeconds=self._timeout_seconds,
            )
        )
        return _redact_payload(response)

    def get_account_config(self) -> dict[str, Any]:
        return self.request("GET", "/api/v5/account/config")

    def get_balance(self, currency: str = "USDT") -> dict[str, Any]:
        return self.request("GET", "/api/v5/account/balance", query={"ccy": currency})

    def get_positions(
        self,
        instrumentId: str | None = None,
        instrumentType: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "GET",
            "/api/v5/account/positions",
            query={"instId": instrumentId, "instType": instrumentType},
        )

    def place_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = ("instId", "tdMode", "side", "ordType", "sz", "clOrdId")
        missing = [key for key in required if not str(payload.get(key, "")).strip()]
        if missing:
            raise ValueError(f"OKX Demo order is missing required fields: {', '.join(missing)}")
        if not _CLIENT_ID.fullmatch(str(payload["clOrdId"])):
            raise ValueError("clOrdId must contain 1-32 case-sensitive alphanumeric characters")
        return self.request("POST", "/api/v5/trade/order", body=payload)

    def get_order(
        self, *, instId: str, ordId: str | None = None, clOrdId: str | None = None
    ) -> dict[str, Any]:
        if not ordId and not clOrdId:
            raise ValueError("ordId or clOrdId is required")
        return self.request(
            "GET", "/api/v5/trade/order", query={"instId": instId, "ordId": ordId, "clOrdId": clOrdId}
        )

    def cancel_order(
        self, *, instId: str, ordId: str | None = None, clOrdId: str | None = None
    ) -> dict[str, Any]:
        if not ordId and not clOrdId:
            raise ValueError("ordId or clOrdId is required")
        return self.request(
            "POST", "/api/v5/trade/cancel-order", body={"instId": instId, "ordId": ordId, "clOrdId": clOrdId}
        )

    def cancel_all_after(self, timeoutSeconds: int) -> dict[str, Any]:
        if timeoutSeconds != 0 and not 10 <= timeoutSeconds <= 120:
            raise ValueError("Cancel-all-after timeout must be 0 or between 10 and 120 seconds")
        return self.request(
            "POST", "/api/v5/trade/cancel-all-after", body={"timeOut": str(timeoutSeconds), "tag": "alphapilot"}
        )
