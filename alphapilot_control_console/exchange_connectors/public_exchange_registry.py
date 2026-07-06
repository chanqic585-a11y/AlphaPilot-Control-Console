from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import (
    DEFAULT_EXCHANGE_PROBE_LIMIT,
    DEFAULT_EXCHANGE_PROBE_SYMBOL,
    DEFAULT_EXCHANGE_PROBE_TIMEFRAME,
    PUBLIC_EXCHANGE_IDS,
    SAFETY_BOUNDARY,
)
from ..state_store import now_iso, write_exchange_probe_results


@dataclass(frozen=True)
class PublicExchangeSource:
    exchange: str
    display_name: str
    base_url: str
    public_only: bool
    supports_ticker: bool
    supports_ohlcv: bool
    supports_funding_rate: bool
    supports_open_interest: bool
    documentation_url: str


PUBLIC_EXCHANGES = {
    "okx": PublicExchangeSource(
        exchange="okx",
        display_name="OKX",
        base_url="https://www.okx.com",
        public_only=True,
        supports_ticker=True,
        supports_ohlcv=True,
        supports_funding_rate=True,
        supports_open_interest=True,
        documentation_url="https://www.okx.com/docs-v5/en/",
    ),
    "binance": PublicExchangeSource(
        exchange="binance",
        display_name="Binance USD-M Futures",
        base_url="https://fapi.binance.com",
        public_only=True,
        supports_ticker=True,
        supports_ohlcv=True,
        supports_funding_rate=True,
        supports_open_interest=True,
        documentation_url="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api",
    ),
    "bybit": PublicExchangeSource(
        exchange="bybit",
        display_name="Bybit USDT Perpetual",
        base_url="https://api.bybit.com",
        public_only=True,
        supports_ticker=True,
        supports_ohlcv=True,
        supports_funding_rate=True,
        supports_open_interest=True,
        documentation_url="https://bybit-exchange.github.io/docs/v5/market/tickers",
    ),
}


def list_public_exchange_sources() -> dict[str, Any]:
    return {
        "version": "V13.6.6",
        "source": "alphapilot_control_console_v13_6_6",
        "publicOnly": True,
        "safetyBoundary": SAFETY_BOUNDARY,
        "sources": [
            {
                "exchange": item.exchange,
                "displayName": item.display_name,
                "baseUrl": item.base_url,
                "publicOnly": item.public_only,
                "supportsTicker": item.supports_ticker,
                "supportsOhlcv": item.supports_ohlcv,
                "supportsFundingRate": item.supports_funding_rate,
                "supportsOpenInterest": item.supports_open_interest,
                "documentationUrl": item.documentation_url,
            }
            for item in PUBLIC_EXCHANGES.values()
        ],
    }


def probe_public_exchanges(
    exchanges: list[str] | None = None,
    symbol: str = DEFAULT_EXCHANGE_PROBE_SYMBOL,
    timeframe: str = DEFAULT_EXCHANGE_PROBE_TIMEFRAME,
    limit: int = DEFAULT_EXCHANGE_PROBE_LIMIT,
) -> dict[str, Any]:
    requested = [item.lower().strip() for item in exchanges or list(PUBLIC_EXCHANGE_IDS)]
    limit = max(1, min(int(limit or DEFAULT_EXCHANGE_PROBE_LIMIT), 10))
    results = [
        _probe_single_exchange(exchange, symbol=symbol, timeframe=timeframe, limit=limit)
        for exchange in requested
        if exchange in PUBLIC_EXCHANGES
    ]
    payload = {
        "version": "V13.6.6",
        "source": "alphapilot_control_console_v13_6_6",
        "publicOnly": True,
        "symbol": symbol,
        "timeframe": timeframe,
        "limit": limit,
        "generatedAt": now_iso(),
        "safetyBoundary": SAFETY_BOUNDARY,
        "results": results,
    }
    write_exchange_probe_results(payload)
    return payload


def _probe_single_exchange(exchange: str, symbol: str, timeframe: str, limit: int) -> dict[str, Any]:
    normalized = _normalize_symbol(symbol)
    started = time.perf_counter()
    checks: list[dict[str, Any]] = []

    if exchange == "okx":
        checks = _probe_okx(normalized["okx"], timeframe, limit)
    elif exchange == "binance":
        checks = _probe_binance(normalized["compact"], timeframe, limit)
    elif exchange == "bybit":
        checks = _probe_bybit(normalized["compact"], timeframe, limit)

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    ok = bool(checks) and any(item["ok"] for item in checks)
    missing = [item["name"] for item in checks if not item["ok"]]
    return {
        "exchange": exchange,
        "displayName": PUBLIC_EXCHANGES[exchange].display_name,
        "publicOnly": True,
        "ok": ok,
        "latencyMs": latency_ms,
        "symbol": symbol,
        "exchangeSymbol": normalized["okx"] if exchange == "okx" else normalized["compact"],
        "checks": checks,
        "missingPublicFields": missing,
        "privateEndpointsUsed": False,
        "apiKeyUsed": False,
        "ordersAllowed": False,
        "generatedAt": now_iso(),
    }


def _probe_okx(inst_id: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
    bar = _okx_timeframe(timeframe)
    return [
        _http_check("ticker", "https://www.okx.com/api/v5/market/ticker", {"instId": inst_id}, ["data"]),
        _http_check("ohlcv", "https://www.okx.com/api/v5/market/candles", {"instId": inst_id, "bar": bar, "limit": str(limit)}, ["data"]),
        _http_check("fundingRate", "https://www.okx.com/api/v5/public/funding-rate", {"instId": inst_id}, ["data"]),
        _http_check("openInterest", "https://www.okx.com/api/v5/public/open-interest", {"instType": "SWAP", "instId": inst_id}, ["data"]),
    ]


def _probe_binance(symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
    interval = _binance_timeframe(timeframe)
    return [
        _http_check("ticker", "https://fapi.binance.com/fapi/v1/ticker/24hr", {"symbol": symbol}, ["lastPrice"]),
        _http_check("ohlcv", "https://fapi.binance.com/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": str(limit)}, []),
        _http_check("fundingRate", "https://fapi.binance.com/fapi/v1/fundingRate", {"symbol": symbol, "limit": "1"}, []),
        _http_check("openInterest", "https://fapi.binance.com/fapi/v1/openInterest", {"symbol": symbol}, ["openInterest"]),
    ]


def _probe_bybit(symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
    interval = _bybit_timeframe(timeframe)
    return [
        _http_check("ticker", "https://api.bybit.com/v5/market/tickers", {"category": "linear", "symbol": symbol}, ["result"]),
        _http_check("ohlcv", "https://api.bybit.com/v5/market/kline", {"category": "linear", "symbol": symbol, "interval": interval, "limit": str(limit)}, ["result"]),
        _http_check("fundingRate", "https://api.bybit.com/v5/market/funding/history", {"category": "linear", "symbol": symbol, "limit": "1"}, ["result"]),
        _http_check("openInterest", "https://api.bybit.com/v5/market/open-interest", {"category": "linear", "symbol": symbol, "intervalTime": "5min", "limit": "1"}, ["result"]),
    ]


def _http_check(name: str, url: str, params: dict[str, str], required_keys: list[str]) -> dict[str, Any]:
    full_url = f"{url}?{urlencode(params)}" if params else url
    started = time.perf_counter()
    try:
        request = Request(full_url, headers={"User-Agent": "AlphaPilot-Control-Console/13.6.6"})
        with urlopen(request, timeout=8) as response:
            body = response.read(2_000_000)
            data = json.loads(body.decode("utf-8"))
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        ok = _has_required_payload(data, required_keys)
        return {
            "name": name,
            "ok": ok,
            "latencyMs": latency_ms,
            "statusCode": 200,
            "summary": _summarize_payload(data),
            "error": None,
        }
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        status_code = exc.code if isinstance(exc, HTTPError) else None
        return {
            "name": name,
            "ok": False,
            "latencyMs": latency_ms,
            "statusCode": status_code,
            "summary": None,
            "error": str(exc),
        }


def _has_required_payload(data: Any, required_keys: list[str]) -> bool:
    if not required_keys:
        return bool(data)
    if isinstance(data, dict):
        return all(key in data for key in required_keys)
    return False


def _summarize_payload(data: Any) -> dict[str, Any]:
    if isinstance(data, list):
        return {"type": "list", "count": len(data)}
    if isinstance(data, dict):
        summary: dict[str, Any] = {"type": "object", "keys": sorted(data.keys())[:8]}
        if isinstance(data.get("data"), list):
            summary["dataCount"] = len(data["data"])
        if isinstance(data.get("result"), dict):
            result = data["result"]
            summary["resultKeys"] = sorted(result.keys())[:8]
            if isinstance(result.get("list"), list):
                summary["resultListCount"] = len(result["list"])
        return summary
    return {"type": type(data).__name__}


def _normalize_symbol(symbol: str) -> dict[str, str]:
    value = (symbol or DEFAULT_EXCHANGE_PROBE_SYMBOL).upper().replace(":USDT", "").strip()
    if "/" in value:
        base, quote = value.split("/", 1)
    elif value.endswith("USDT"):
        base, quote = value[:-4], "USDT"
    else:
        base, quote = value, "USDT"
    compact = f"{base}{quote}".replace("-", "")
    return {
        "base": base,
        "quote": quote,
        "compact": compact,
        "okx": f"{base}-{quote}-SWAP",
    }


def _okx_timeframe(timeframe: str) -> str:
    mapping = {"15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D"}
    return mapping.get(timeframe, "1H")


def _binance_timeframe(timeframe: str) -> str:
    mapping = {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
    return mapping.get(timeframe, "1h")


def _bybit_timeframe(timeframe: str) -> str:
    mapping = {"15m": "15", "1h": "60", "4h": "240", "1d": "D"}
    return mapping.get(timeframe, "60")
