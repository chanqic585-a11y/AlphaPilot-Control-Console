"""Build a public-only OKX USDT perpetual universe for Demo research."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .exchange_connectors.public_exchange_registry import fetch_okx_public_payload
from .state_store import now_iso


DEFAULT_SCREENING_LIMIT = 20
MAX_SCREENING_LIMIT = 100
DEFAULT_MAX_SPREAD_PCT = 0.002


def _number(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _rows(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _rejection(inst_id: str, reason: str, detail: str) -> dict[str, Any]:
    return {"instId": inst_id or "--", "reason": reason, "detail": detail}


def build_okx_usdt_swap_universe(
    instruments: list[dict[str, Any]],
    tickers: list[dict[str, Any]],
    *,
    screening_limit: int = DEFAULT_SCREENING_LIMIT,
    max_spread_pct: float = DEFAULT_MAX_SPREAD_PCT,
) -> dict[str, Any]:
    """Filter and rank public instruments without fabricating missing fields."""

    instrument_rows = _rows(instruments)
    ticker_by_id = {
        str(row.get("instId") or "").upper(): row
        for row in _rows(tickers)
        if str(row.get("instId") or "").strip()
    }
    safe_limit = max(1, min(int(screening_limit or DEFAULT_SCREENING_LIMIT), MAX_SCREENING_LIMIT))
    ranked: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    usdt_linear_count = 0
    live_usdt_linear_count = 0

    for instrument in instrument_rows:
        inst_id = str(instrument.get("instId") or "").upper()
        is_usdt_linear = bool(
            inst_id.endswith("-USDT-SWAP")
            and str(instrument.get("instType") or "SWAP").upper() == "SWAP"
            and str(instrument.get("ctType") or "linear").lower() == "linear"
            and str(instrument.get("settleCcy") or "USDT").upper() == "USDT"
        )
        if not is_usdt_linear:
            rejections.append(_rejection(inst_id, "not_usdt_linear_swap", "不是 USDT 线性永续合约。"))
            continue
        usdt_linear_count += 1
        if str(instrument.get("state") or "").lower() != "live":
            rejections.append(_rejection(inst_id, "instrument_not_live", "合约当前不可正常交易。"))
            continue
        live_usdt_linear_count += 1
        ticker = ticker_by_id.get(inst_id)
        if ticker is None:
            rejections.append(_rejection(inst_id, "ticker_missing", "缺少公共 ticker，未填造行情。"))
            continue
        last = _number(ticker.get("last"))
        bid = _number(ticker.get("bidPx"))
        ask = _number(ticker.get("askPx"))
        volume = _number(ticker.get("volCcy24h") or ticker.get("vol24h"))
        if last is None or last <= 0:
            rejections.append(_rejection(inst_id, "price_invalid", "公共 ticker 价格缺失或无效。"))
            continue
        if volume is None or volume <= 0:
            rejections.append(_rejection(inst_id, "volume_invalid", "公共 24H 成交量缺失或无效。"))
            continue
        if bid is None or ask is None or bid <= 0 or ask < bid:
            rejections.append(_rejection(inst_id, "spread_invalid", "买卖一档价格缺失或无效。"))
            continue
        spread_pct = (ask - bid) / ((ask + bid) / 2.0)
        if spread_pct > max_spread_pct:
            rejections.append(_rejection(inst_id, "spread_too_wide", "买卖价差超过公共流动性门槛。"))
            continue
        ranked.append(
            {
                "instId": inst_id,
                "lastPrice": last,
                "bidPrice": bid,
                "askPrice": ask,
                "spreadPct": spread_pct,
                "volume24h": volume,
                "quoteVolumeProxy": last * volume,
                "state": "live",
                "publicOnly": True,
            }
        )

    ranked.sort(key=lambda row: (-float(row["quoteVolumeProxy"]), float(row["spreadPct"]), str(row["instId"])))
    total = len(instrument_rows)
    result = {
        "source": "okx_public_full_market_universe_v13_27_1_5",
        "generatedAt": now_iso(),
        "marketScope": "okx_usdt_linear_perpetual_full_market",
        "totalInstrumentCount": total,
        "usdtLinearSwapCount": usdt_linear_count,
        "liveUsdtLinearSwapCount": live_usdt_linear_count,
        "tickerCount": len(ticker_by_id),
        "liquidityEligibleCount": len(ranked),
        "screeningLimit": safe_limit,
        "rankedInstruments": ranked,
        "screeningPool": ranked[:safe_limit],
        "rejections": rejections,
        "progress": {
            "mode": "determinate",
            "status": "completed",
            "phase": "public_universe_filter",
            "label": "OKX USDT 永续全市场初筛完成",
            "completed": total,
            "required": total,
            "percent": 100 if total else 0,
        },
        "publicMarketOnly": True,
        "apiKeyUsed": False,
        "privateEndpointsUsed": False,
        "createsOrder": False,
    }
    manifest_projection = {
        "marketScope": result["marketScope"],
        "screeningLimit": safe_limit,
        "rankedInstrumentIds": [row["instId"] for row in ranked],
        "screeningPoolIds": [row["instId"] for row in ranked[:safe_limit]],
    }
    result["manifestHash"] = hashlib.sha256(
        json.dumps(
            manifest_projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return result


def fetch_okx_usdt_swap_universe(
    screening_limit: int = DEFAULT_SCREENING_LIMIT,
) -> dict[str, Any]:
    """Load public instruments and tickers, then build the ranked universe."""

    instruments_response = fetch_okx_public_payload(
        "/api/v5/public/instruments",
        {"instType": "SWAP"},
    )
    tickers_response = fetch_okx_public_payload(
        "/api/v5/market/tickers",
        {"instType": "SWAP"},
    )
    errors = [
        str(row.get("error"))
        for row in (instruments_response, tickers_response)
        if row.get("error")
    ]
    instruments_payload = instruments_response.get("payload") if isinstance(instruments_response.get("payload"), dict) else {}
    tickers_payload = tickers_response.get("payload") if isinstance(tickers_response.get("payload"), dict) else {}
    result = build_okx_usdt_swap_universe(
        _rows(instruments_payload.get("data")),
        _rows(tickers_payload.get("data")),
        screening_limit=screening_limit,
    )
    result["errors"] = errors
    if errors:
        result["progress"] = {
            **result["progress"],
            "status": "failed",
            "label": "OKX 全市场公共数据读取不完整",
        }
    result["requestLatencyMs"] = {
        "instruments": instruments_response.get("latencyMs"),
        "tickers": tickers_response.get("latencyMs"),
    }
    return result
