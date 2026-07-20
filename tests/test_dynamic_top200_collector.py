from datetime import UTC, datetime

from alphapilot_control_console.dynamic_top200_collector import (
    build_top200_market_readiness,
    collect_dynamic_top200_snapshot,
)


def _instrument(inst_id: str, **overrides):
    base = inst_id.split("-")[0]
    row = {
        "instId": inst_id,
        "instType": "SWAP",
        "settleCcy": "USDT",
        "quoteCcy": "USDT",
        "ctType": "linear",
        "state": "live",
        "baseCcy": base,
        "tickSz": "0.01",
        "lotSz": "0.01",
        "minSz": "0.01",
        "ctVal": "1",
    }
    row.update(overrides)
    return row


def _candles(count: int, *, timeframe_ms: int, quote_start: int = 1000):
    end = int(datetime(2026, 7, 20, tzinfo=UTC).timestamp() * 1000)
    return [
        [
            str(end - timeframe_ms * (index + 1)),
            "10",
            "11",
            "9",
            "10",
            "100",
            "100",
            str(quote_start + index),
            "1",
        ]
        for index in range(count)
    ]


def test_market_readiness_uses_complete_exact_quote_turnover_and_component_lookbacks():
    public = [
        _instrument("BTC-USDT-SWAP"),
        _instrument("USDC-USDT-SWAP"),
        _instrument("XAU-USDT-SWAP"),
    ]
    authenticated = list(public)
    tickers = [
        {"instId": "BTC-USDT-SWAP", "last": "10", "ts": "1784505599000"},
        {"instId": "USDC-USDT-SWAP", "last": "1", "ts": "1784505599000"},
        {"instId": "XAU-USDT-SWAP", "last": "2400", "ts": "1784505599000"},
    ]
    rows, audit = build_top200_market_readiness(
        public_instruments=public,
        authenticated_instruments=authenticated,
        tickers=tickers,
        daily_candles_by_instrument={
            "BTC-USDT-SWAP": _candles(200, timeframe_ms=86_400_000),
            "USDC-USDT-SWAP": _candles(200, timeframe_ms=86_400_000),
            "XAU-USDT-SWAP": _candles(200, timeframe_ms=86_400_000),
        },
        hourly_candles_by_instrument={
            "BTC-USDT-SWAP": _candles(240, timeframe_ms=3_600_000),
            "USDC-USDT-SWAP": _candles(240, timeframe_ms=3_600_000),
            "XAU-USDT-SWAP": _candles(240, timeframe_ms=3_600_000),
        },
        generated_at="2026-07-20T01:00:00Z",
    )

    by_id = {row["instId"]: row for row in rows}
    btc = by_id["BTC-USDT-SWAP"]
    assert btc["assetClass"] == "crypto_native"
    assert btc["runtimeMarketDataReady"] is True
    assert btc["componentLookbackReady"] is True
    assert len(btc["completedDailyQuoteTurnover"]) == 30
    assert btc["completedDailyQuoteTurnover"][-1] == 1000.0
    assert btc["capacityReady"] is True
    assert by_id["USDC-USDT-SWAP"]["assetClass"] == "stablecoin_fx_like"
    assert by_id["XAU-USDT-SWAP"]["assetClass"] == "tokenized_commodity"
    assert audit["exactQuoteTurnoverReadyCount"] == 3
    assert audit["componentLookbackReadyCount"] == 3


class _PrivateClient:
    def get_account_instruments(self, instrumentType="SWAP"):
        assert instrumentType == "SWAP"
        return {"code": "0", "data": [_instrument("BTC-USDT-SWAP")]}


def test_collector_builds_and_freezes_snapshot_from_injected_okx_responses(tmp_path):
    public = [_instrument("BTC-USDT-SWAP")]
    calls = []

    def fetch(path, params=None):
        calls.append((path, dict(params or {})))
        if path.endswith("/public/instruments"):
            payload = {"code": "0", "data": public}
        elif path.endswith("/market/tickers"):
            payload = {
                "code": "0",
                "data": [{"instId": "BTC-USDT-SWAP", "last": "10", "ts": "1784505599000"}],
            }
        elif (params or {}).get("bar") == "1Dutc":
            payload = {"code": "0", "data": _candles(200, timeframe_ms=86_400_000)}
        else:
            payload = {"code": "0", "data": _candles(240, timeframe_ms=3_600_000)}
        return {"ok": True, "payload": payload, "error": None}

    result = collect_dynamic_top200_snapshot(
        private_client=_PrivateClient(),
        snapshot_dir=tmp_path,
        public_fetch=fetch,
        now_factory=lambda: datetime(2026, 7, 20, 1, tzinfo=UTC),
        sleep=lambda _seconds: None,
    )

    assert result["snapshot"]["instrumentIds"] == ["BTC-USDT-SWAP"]
    assert result["freeze"]["reused"] is False
    assert result["readinessAudit"]["collectionStatus"] == "completed"
    assert len(calls) == 4
    assert any(params.get("bar") == "1H" for _path, params in calls)
    assert any(params.get("bar") == "1Dutc" and params.get("limit") == "201" for _path, params in calls)
    assert any(params.get("bar") == "1H" and params.get("limit") == "241" for _path, params in calls)

    repeated = collect_dynamic_top200_snapshot(
        private_client=_PrivateClient(),
        snapshot_dir=tmp_path,
        public_fetch=fetch,
        now_factory=lambda: datetime(2026, 7, 20, 2, tzinfo=UTC),
        sleep=lambda _seconds: None,
    )
    assert repeated["freeze"]["reused"] is True
    assert repeated["snapshot"]["snapshotHash"] == result["snapshot"]["snapshotHash"]
