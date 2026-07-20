"""Collect causal OKX inputs for the daily-frozen Demo TOP200 universe."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol

from .dynamic_top200_universe import (
    QUOTE_TURNOVER_SOURCE,
    build_dynamic_top200_policy,
    build_dynamic_top200_snapshot,
    freeze_daily_top200_snapshot,
)
from .exchange_connectors.public_exchange_registry import fetch_okx_public_payload


DAILY_LOOKBACK_BARS = 200
HOURLY_LOOKBACK_BARS = 240
MAXIMUM_MINIMUM_ORDER_NOTIONAL_USDT = 100.0
_CRYPTO_SYMBOL = re.compile(r"^[A-Z0-9]{2,20}$")
_STABLECOIN_BASES = {
    "DAI",
    "FDUSD",
    "PYUSD",
    "TUSD",
    "USDC",
    "USDD",
    "USDE",
    "USDP",
    "USDT",
}
_TOKENIZED_EQUITY_BASES = {
    "AAPL",
    "AMZN",
    "COIN",
    "GOOGL",
    "META",
    "MSFT",
    "MSTR",
    "NVDA",
    "SPY",
    "TSLA",
}
_TOKENIZED_COMMODITY_BASES = {"XAG", "XAU"}


class ReadOnlyAccountInstrumentClient(Protocol):
    def get_account_instruments(self, instrumentType: str = "SWAP") -> dict[str, Any]: ...


PublicFetch = Callable[[str, dict[str, str] | None], dict[str, Any]]


def _payload_rows(result: Mapping[str, Any], label: str) -> list[dict[str, Any]]:
    if result.get("ok") is False:
        raise RuntimeError(f"{label}:{result.get('error') or 'public_request_failed'}")
    payload = result.get("payload") if "payload" in result else result
    if not isinstance(payload, Mapping) or str(payload.get("code") or "") != "0":
        message = payload.get("msg") if isinstance(payload, Mapping) else "invalid_response"
        raise RuntimeError(f"{label}:{message}")
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise RuntimeError(f"{label}:missing_data")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _private_rows(result: Mapping[str, Any], label: str) -> list[dict[str, Any]]:
    if str(result.get("code") or "") != "0":
        raise RuntimeError(f"{label}:{result.get('code') or 'private_request_failed'}")
    rows = result.get("data")
    if not isinstance(rows, list):
        raise RuntimeError(f"{label}:missing_data")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _asset_class(row: Mapping[str, Any]) -> str:
    hinted = str(row.get("assetClassHint") or "").strip().lower()
    if hinted in {
        "crypto_native",
        "stablecoin_fx_like",
        "tokenized_commodity",
        "tokenized_equity",
    }:
        return hinted
    base = str(row.get("baseCcy") or str(row.get("instId") or "").split("-")[0]).upper()
    if base in _STABLECOIN_BASES:
        return "stablecoin_fx_like"
    if base in _TOKENIZED_EQUITY_BASES:
        return "tokenized_equity"
    if base in _TOKENIZED_COMMODITY_BASES:
        return "tokenized_commodity"
    if _CRYPTO_SYMBOL.fullmatch(base):
        return "crypto_native"
    return "unknown_asset_class"


def _completed_candles(
    rows: Iterable[Any],
    *,
    before_epoch_ms: int,
) -> list[list[Any]]:
    completed: list[list[Any]] = []
    for raw in rows:
        if not isinstance(raw, list) or len(raw) < 9 or str(raw[8]) != "1":
            continue
        try:
            timestamp = int(raw[0])
        except (TypeError, ValueError):
            continue
        if timestamp < before_epoch_ms:
            completed.append(raw)
    return sorted(completed, key=lambda row: int(row[0]))


def build_top200_market_readiness(
    *,
    public_instruments: Iterable[Mapping[str, Any]],
    authenticated_instruments: Iterable[Mapping[str, Any]],
    tickers: Iterable[Mapping[str, Any]],
    daily_candles_by_instrument: Mapping[str, Iterable[Any]],
    hourly_candles_by_instrument: Mapping[str, Iterable[Any]],
    generated_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normalize exact quote turnover and component lookback evidence."""

    now = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00")).astimezone(UTC)
    day_boundary = int(
        datetime(now.year, now.month, now.day, tzinfo=UTC).timestamp() * 1000
    )
    hour_boundary = int(
        now.replace(minute=0, second=0, microsecond=0).timestamp() * 1000
    )
    authenticated = {
        str(row.get("instId") or "").strip().upper(): dict(row)
        for row in authenticated_instruments
        if str(row.get("instId") or "").strip()
    }
    ticker_map = {
        str(row.get("instId") or "").strip().upper(): dict(row)
        for row in tickers
        if str(row.get("instId") or "").strip()
    }
    readiness: list[dict[str, Any]] = []
    exact_count = 0
    lookback_count = 0
    capacity_count = 0

    for raw_public in public_instruments:
        public = dict(raw_public)
        inst_id = str(public.get("instId") or "").strip().upper()
        private = authenticated.get(inst_id, {})
        ticker = ticker_map.get(inst_id, {})
        daily = _completed_candles(
            daily_candles_by_instrument.get(inst_id, []),
            before_epoch_ms=day_boundary,
        )
        hourly = _completed_candles(
            hourly_candles_by_instrument.get(inst_id, []),
            before_epoch_ms=hour_boundary,
        )
        quote_turnover = [
            value
            for row in daily[-30:]
            if (value := _number(row[7] if len(row) > 7 else None)) is not None
        ]
        exact_ready = len(quote_turnover) == 30
        lookback_ready = len(daily) >= DAILY_LOOKBACK_BARS and len(hourly) >= HOURLY_LOOKBACK_BARS
        last_price = _number(ticker.get("last"))
        min_size = _number(private.get("minSz") or public.get("minSz"))
        contract_value = _number(private.get("ctVal") or public.get("ctVal"))
        minimum_notional = (
            min_size * contract_value * last_price
            if None not in {min_size, contract_value, last_price}
            else None
        )
        capacity_ready = bool(
            minimum_notional is not None
            and minimum_notional > 0
            and minimum_notional <= MAXIMUM_MINIMUM_ORDER_NOTIONAL_USDT
        )
        market_ready = bool(last_price is not None and last_price > 0)
        exact_count += int(exact_ready)
        lookback_count += int(lookback_ready)
        capacity_count += int(capacity_ready)
        readiness.append(
            {
                "instId": inst_id,
                "assetClass": _asset_class(public),
                "runtimeMarketDataReady": market_ready,
                "componentLookbackReady": lookback_ready,
                "componentLookbackCounts": {
                    "1Hutc": len(hourly),
                    "1Dutc": len(daily),
                },
                "quoteTurnoverSource": QUOTE_TURNOVER_SOURCE,
                "completedDailyQuoteTurnover": quote_turnover if exact_ready else [],
                "capacityReady": capacity_ready,
                "minimumOrderNotionalUsdt": minimum_notional,
                "tickerTimestamp": str(ticker.get("ts") or ""),
            }
        )

    audit = {
        "schemaVersion": "okx_demo_top200_input_readiness_v1",
        "generatedAt": generated_at,
        "publicInstrumentCount": len(readiness),
        "authenticatedInstrumentCount": len(authenticated),
        "exactQuoteTurnoverReadyCount": exact_count,
        "componentLookbackReadyCount": lookback_count,
        "capacityReadyCount": capacity_count,
        "dailyLookbackRequirement": DAILY_LOOKBACK_BARS,
        "hourlyLookbackRequirement": HOURLY_LOOKBACK_BARS,
        "maximumMinimumOrderNotionalUsdt": MAXIMUM_MINIMUM_ORDER_NOTIONAL_USDT,
        "resultMetricsUsed": False,
    }
    return readiness, audit


def collect_dynamic_top200_snapshot(
    *,
    private_client: ReadOnlyAccountInstrumentClient,
    snapshot_dir: Path | str,
    public_fetch: PublicFetch = fetch_okx_public_payload,
    now_factory: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Collect and freeze one TOP200 snapshot using read-only endpoints only."""

    now = now_factory().astimezone(UTC)
    generated_at = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    public = _payload_rows(
        public_fetch("/api/v5/public/instruments", {"instType": "SWAP"}),
        "public_instruments",
    )
    private = _private_rows(
        private_client.get_account_instruments(instrumentType="SWAP"),
        "account_instruments",
    )
    tickers = _payload_rows(
        public_fetch("/api/v5/market/tickers", {"instType": "SWAP"}),
        "market_tickers",
    )
    private_ids = {str(row.get("instId") or "").strip().upper() for row in private}
    eligible_ids = [
        str(row.get("instId") or "").strip().upper()
        for row in public
        if str(row.get("instId") or "").strip().upper() in private_ids
        and str(row.get("instType") or "").upper() == "SWAP"
        and str(row.get("settleCcy") or "").upper() == "USDT"
        and str(row.get("ctType") or "").lower() == "linear"
        and str(row.get("state") or "").lower() == "live"
    ]
    daily: dict[str, list[Any]] = {}
    hourly: dict[str, list[Any]] = {}
    errors: list[dict[str, str]] = []
    for inst_id in eligible_ids:
        try:
            daily[inst_id] = _payload_rows_as_lists(
                public_fetch(
                    "/api/v5/market/candles",
                    {"instId": inst_id, "bar": "1Dutc", "limit": str(DAILY_LOOKBACK_BARS + 1)},
                ),
                f"daily_candles:{inst_id}",
            )
            sleep(0.05)
            hourly[inst_id] = _payload_rows_as_lists(
                public_fetch(
                    "/api/v5/market/candles",
                    {"instId": inst_id, "bar": "1H", "limit": str(HOURLY_LOOKBACK_BARS + 1)},
                ),
                f"hourly_candles:{inst_id}",
            )
            sleep(0.05)
        except RuntimeError as error:
            errors.append({"instId": inst_id, "error": str(error)})

    readiness, input_audit = build_top200_market_readiness(
        public_instruments=public,
        authenticated_instruments=private,
        tickers=tickers,
        daily_candles_by_instrument=daily,
        hourly_candles_by_instrument=hourly,
        generated_at=generated_at,
    )
    snapshot, readiness_audit = build_dynamic_top200_snapshot(
        public_instruments=public,
        authenticated_instruments=private,
        market_readiness=readiness,
        utc_date=now.date().isoformat(),
        generated_at=generated_at,
    )
    freeze = freeze_daily_top200_snapshot(snapshot_dir, snapshot)
    readiness_audit.update(
        {
            "collectionStatus": "completed" if not errors else "completed_with_rejections",
            "collectionErrors": errors,
            "inputReadiness": input_audit,
        }
    )
    return {
        "policy": build_dynamic_top200_policy(),
        "snapshot": freeze["snapshot"],
        "readinessAudit": readiness_audit,
        "freeze": {"reused": freeze["reused"], "path": freeze["path"]},
    }


def _payload_rows_as_lists(result: Mapping[str, Any], label: str) -> list[list[Any]]:
    if result.get("ok") is False:
        raise RuntimeError(f"{label}:{result.get('error') or 'public_request_failed'}")
    payload = result.get("payload") if "payload" in result else result
    if not isinstance(payload, Mapping) or str(payload.get("code") or "") != "0":
        message = payload.get("msg") if isinstance(payload, Mapping) else "invalid_response"
        raise RuntimeError(f"{label}:{message}")
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise RuntimeError(f"{label}:missing_data")
    return [list(row) for row in rows if isinstance(row, list)]
