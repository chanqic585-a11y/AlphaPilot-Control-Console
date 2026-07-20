from __future__ import annotations

from pathlib import Path

from alphapilot_control_console.demo_matchability_readiness import (
    build_matchability_readiness,
    canonical_demo_instrument_from_pair,
    write_matchability_artifacts,
)


def _release() -> dict:
    return {
        "releaseId": "release_fixture",
        "releaseHash": "release_hash_fixture",
        "componentIds": ["short_1h", "long_1d"],
        "executionInstruments": [
            "BTC-USDT-SWAP",
            "ETH-USDT-SWAP",
            "SOL-USDT-SWAP",
        ],
        "actualInstrumentCount": 3,
    }


def _components() -> list[dict]:
    return [
        {
            "strategyCandidateId": "short_1h",
            "familyKey": "short_rejection",
            "direction": "short",
            "timeframe": "1h",
            "selectedPairs": ["BTC/USDT:USDT", "SOL/USDT:USDT"],
        },
        {
            "strategyCandidateId": "long_1d",
            "familyKey": "squeeze_breakout",
            "direction": "long",
            "timeframe": "1d",
            "marketDefinition": {
                "universePolicy": {"mode": "okx_usdt_linear_perpetual_full_market"}
            },
        },
    ]


def _trades() -> dict[str, list[dict]]:
    return {
        "short_1h": [
            {"entryDate": "2026-06-29T00:00:00Z", "pair": "BTC/USDT:USDT"},
            {"entryDate": "2026-06-01T00:00:00Z", "pair": "SOL/USDT:USDT"},
            {"entryDate": "2026-03-01T00:00:00Z", "pair": "BTC/USDT:USDT"},
        ],
        "long_1d": [
            {"entryDate": "2026-04-15T00:00:00Z", "pair": "ETH/USDT:USDT"}
        ],
    }


def test_normalizes_swap_pairs_without_guessing_other_markets() -> None:
    assert canonical_demo_instrument_from_pair("BTC/USDT:USDT") == "BTC-USDT-SWAP"
    assert canonical_demo_instrument_from_pair("sol-usdt-swap") == "SOL-USDT-SWAP"
    assert canonical_demo_instrument_from_pair("BTC/USD") is None


def test_builds_deterministic_component_and_window_matchability() -> None:
    result = build_matchability_readiness(
        release=_release(),
        components=_components(),
        trades_by_candidate=_trades(),
        as_of="2026-06-30T00:00:00Z",
    )

    assert result["status"] == "ready_with_sparse_signal_warning"
    assert result["asOf"] == "2026-06-30T00:00:00Z"
    assert result["headline"] == {
        "releaseInstrumentCount": 3,
        "compatibleComponentCount": 2,
        "signalCount30d": 2,
        "signalCount90d": 3,
    }
    rows = {row["candidateId"]: row for row in result["components"]}
    assert rows["short_1h"]["signalCount30d"] == 2
    assert rows["short_1h"]["signalCount90d"] == 2
    assert rows["short_1h"]["compatibleInstrumentCount"] == 2
    assert rows["long_1d"]["signalCount30d"] == 0
    assert rows["long_1d"]["signalCount90d"] == 1
    assert rows["long_1d"]["compatibleInstrumentCount"] == 3
    assert result["preArmFunnel"]["componentWithSignal30dCount"] == 1
    assert result["preArmFunnel"]["strategyOrderCount"] == 0


def test_zero_recent_signals_are_warning_not_a_fabricated_blocker() -> None:
    result = build_matchability_readiness(
        release=_release(),
        components=_components(),
        trades_by_candidate={"short_1h": [], "long_1d": []},
        as_of="2026-06-30T00:00:00Z",
    )

    assert result["status"] == "ready_with_sparse_signal_warning"
    assert result["headline"]["signalCount90d"] == 0
    assert "no_historical_signal_in_90d" in result["warnings"]
    assert result["blockers"] == []


def test_empty_component_universe_is_a_real_blocker() -> None:
    components = _components()
    components[0]["selectedPairs"] = ["DOGE/USDT:USDT"]
    components[1]["marketDefinition"] = {
        "universePolicy": {"mode": "fixed_selected_pairs"}
    }
    components[1]["selectedPairs"] = ["XRP/USDT:USDT"]

    result = build_matchability_readiness(
        release=_release(),
        components=components,
        trades_by_candidate=_trades(),
        as_of="2026-06-30T00:00:00Z",
    )

    assert result["status"] == "blocked"
    assert "component_universe_intersection_empty" in result["blockers"]


def test_rehearsal_module_has_no_private_or_order_client_dependency() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "alphapilot_control_console"
        / "demo_matchability_readiness.py"
    ).read_text(encoding="utf-8")

    assert "okx_demo_client" not in source
    assert "okx_demo_private" not in source
    assert "create_order" not in source
    assert "place_order" not in source


def test_writes_all_required_matchability_artifacts(tmp_path: Path) -> None:
    result = build_matchability_readiness(
        release=_release(),
        components=_components(),
        trades_by_candidate=_trades(),
        as_of="2026-06-30T00:00:00Z",
    )

    write_matchability_artifacts(tmp_path, result)

    assert {path.name for path in tmp_path.iterdir()} == {
        "component_signal_matchability.csv",
        "signal_matchability_30d.json",
        "signal_matchability_90d.json",
        "pre_arm_scan_funnel.json",
    }
