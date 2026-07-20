from __future__ import annotations

import json
from pathlib import Path

import pytest

from alphapilot_control_console.dynamic_top200_universe import (
    POLICY_ID,
    build_dynamic_top200_policy,
    build_dynamic_top200_snapshot,
    freeze_daily_top200_snapshot,
)


def _instrument(inst_id: str, **overrides: object) -> dict[str, object]:
    base = inst_id.split("-", 1)[0]
    return {
        "instId": inst_id,
        "instType": "SWAP",
        "ctType": "linear",
        "settleCcy": "USDT",
        "baseCcy": base,
        "quoteCcy": "USDT",
        "state": "live",
        "tickSz": "0.1",
        "lotSz": "0.01",
        "minSz": "0.01",
        **overrides,
    }


def _market_state(
    inst_id: str,
    turnover: float,
    *,
    exact: bool = True,
    asset_class: str = "crypto_native",
) -> dict[str, object]:
    return {
        "instId": inst_id,
        "assetClass": asset_class,
        "runtimeMarketDataReady": True,
        "componentLookbackReady": True,
        "capacityReady": True,
        "quoteTurnoverSource": "okx_completed_1Dutc_volCcyQuote" if exact else "close_times_contract_volume",
        "completedDailyQuoteTurnover": [turnover] * 30,
    }


def test_policy_is_exact_daily_frozen_top200_contract() -> None:
    policy = build_dynamic_top200_policy()

    assert policy["policyId"] == POLICY_ID
    assert policy["maximumInstrumentCount"] == 200
    assert policy["refreshCadence"] == "daily_frozen_snapshot"
    assert policy["rankingMetric"] == "medianDailyQuoteTurnover"
    assert policy["rankingWindowCompleteUtcDays"] == 30
    assert policy["quoteTurnoverSource"] == "okx_completed_1Dutc_volCcyQuote"
    assert policy["resultBasedSelectionAllowed"] is False
    assert policy["policyHash"].startswith("top200_universe_policy_")


def test_snapshot_filters_then_ranks_by_exact_turnover_with_stable_tie_break() -> None:
    public = [
        _instrument("AAA-USDT-SWAP"),
        _instrument("BBB-USDT-SWAP"),
        _instrument("CCC-USDT-SWAP"),
        _instrument("USDC-USDT-SWAP"),
        _instrument("TSLA-USDT-SWAP"),
        _instrument("DEAD-USDT-SWAP", state="suspend"),
    ]
    authenticated = list(public)
    market = [
        _market_state("AAA-USDT-SWAP", 10_000),
        _market_state("BBB-USDT-SWAP", 20_000),
        _market_state("CCC-USDT-SWAP", 20_000),
        _market_state("USDC-USDT-SWAP", 50_000, asset_class="stablecoin_fx_like"),
        _market_state("TSLA-USDT-SWAP", 50_000, asset_class="tokenized_equity"),
        _market_state("DEAD-USDT-SWAP", 50_000),
    ]

    snapshot, audit = build_dynamic_top200_snapshot(
        public_instruments=public,
        authenticated_instruments=authenticated,
        market_readiness=market,
        utc_date="2026-07-20",
        generated_at="2026-07-20T00:01:00Z",
    )

    assert snapshot["actualInstrumentCount"] == 3
    assert snapshot["instrumentIds"] == [
        "BBB-USDT-SWAP",
        "CCC-USDT-SWAP",
        "AAA-USDT-SWAP",
    ]
    assert snapshot["snapshotHash"].startswith("demo_top200_universe_snapshot_")
    assert audit["status"] == "ready"
    assert audit["eligibleBeforeLimitCount"] == 3
    assert audit["rejectionReasonCounts"] == {
        "asset_class_not_crypto_native": 2,
        "state_not_live": 1,
    }


def test_snapshot_fails_closed_without_exact_quote_turnover_or_readiness() -> None:
    public = [_instrument("AAA-USDT-SWAP"), _instrument("BBB-USDT-SWAP")]
    authenticated = list(public)
    proxy = _market_state("AAA-USDT-SWAP", 10_000, exact=False)
    incomplete = _market_state("BBB-USDT-SWAP", 20_000)
    incomplete["completedDailyQuoteTurnover"] = [20_000] * 29

    snapshot, audit = build_dynamic_top200_snapshot(
        public_instruments=public,
        authenticated_instruments=authenticated,
        market_readiness=[proxy, incomplete],
        utc_date="2026-07-20",
        generated_at="2026-07-20T00:01:00Z",
    )

    assert snapshot["status"] == "blocked_empty_universe"
    assert snapshot["instrumentIds"] == []
    assert audit["status"] == "blocked_empty_universe"
    assert audit["rejectionReasonCounts"] == {
        "exact_quote_turnover_unavailable": 1,
        "history_not_ready": 1,
    }


def test_daily_snapshot_is_immutable_after_first_freeze(tmp_path: Path) -> None:
    public = [_instrument("AAA-USDT-SWAP"), _instrument("BBB-USDT-SWAP")]
    first, _ = build_dynamic_top200_snapshot(
        public_instruments=public,
        authenticated_instruments=public,
        market_readiness=[
            _market_state("AAA-USDT-SWAP", 20_000),
            _market_state("BBB-USDT-SWAP", 10_000),
        ],
        utc_date="2026-07-20",
        generated_at="2026-07-20T00:01:00Z",
    )
    second, _ = build_dynamic_top200_snapshot(
        public_instruments=public,
        authenticated_instruments=public,
        market_readiness=[
            _market_state("AAA-USDT-SWAP", 1),
            _market_state("BBB-USDT-SWAP", 99_999),
        ],
        utc_date="2026-07-20",
        generated_at="2026-07-20T12:00:00Z",
    )

    first_result = freeze_daily_top200_snapshot(tmp_path, first)
    second_result = freeze_daily_top200_snapshot(tmp_path, second)

    assert first_result["reused"] is False
    assert second_result["reused"] is True
    assert second_result["snapshot"]["snapshotHash"] == first["snapshotHash"]
    assert second_result["snapshot"]["instrumentIds"] == [
        "AAA-USDT-SWAP",
        "BBB-USDT-SWAP",
    ]
    files = list(tmp_path.glob("demo_top200_universe_snapshot_2026-07-20_*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text(encoding="utf-8"))["snapshotHash"] == first["snapshotHash"]


def test_freeze_rejects_tampered_snapshot(tmp_path: Path) -> None:
    public = [_instrument("AAA-USDT-SWAP")]
    snapshot, _ = build_dynamic_top200_snapshot(
        public_instruments=public,
        authenticated_instruments=public,
        market_readiness=[_market_state("AAA-USDT-SWAP", 20_000)],
        utc_date="2026-07-20",
        generated_at="2026-07-20T00:01:00Z",
    )
    snapshot["instrumentIds"] = ["TAMPERED-USDT-SWAP"]

    with pytest.raises(ValueError, match="snapshot_hash_mismatch"):
        freeze_daily_top200_snapshot(tmp_path, snapshot)


def test_freeze_refuses_an_empty_universe(tmp_path: Path) -> None:
    snapshot, _ = build_dynamic_top200_snapshot(
        public_instruments=[],
        authenticated_instruments=[],
        market_readiness=[],
        utc_date="2026-07-20",
        generated_at="2026-07-20T01:00:00Z",
    )

    with pytest.raises(ValueError, match="snapshot_not_ready"):
        freeze_daily_top200_snapshot(tmp_path, snapshot)
