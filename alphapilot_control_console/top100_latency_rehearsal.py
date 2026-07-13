"""Deterministic public-only Top100 latency rehearsal with no order sink."""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .demo_arbitrator import arbitrate_demo_signals
from .demo_entry_latency_policy import evaluate_demo_entry_latency
from .demo_release_scanner import scan_immutable_demo_release
from .demo_universe_policy import DEMO_DEEP_SCREENING_LIMIT, DEMO_UNIVERSE_POLICY_VERSION


VERSION = "V13.27.9"
DEFAULT_REPORT_PATH = DATA_DIR / "ops" / "v13_27_9_top100_latency_rehearsal.json"


def _instrument(index: int) -> str:
    return f"AP{index:03d}-USDT-SWAP"


def _release(index: int) -> dict[str, Any]:
    return {
        "demoReleaseId": f"rehearsal-release-{index}",
        "strategyCandidateId": f"rehearsal-strategy-{index}",
        "riskEnvelope": {
            "initialEquityUsdt": 1000.0,
            "riskPerTradePercent": 0.25,
            "maxOrderNotionalUsdt": 100.0,
            "defaultMaxLeverage": 1,
        },
        "strategy": {
            "familyKey": f"rehearsal-family-{index}",
            "marketDefinition": {
                "timeframe": "5m",
                "universePolicy": {
                    "mode": "okx_usdt_linear_perpetual_full_market",
                    "screeningLimit": DEMO_DEEP_SCREENING_LIMIT,
                    "policyVersion": DEMO_UNIVERSE_POLICY_VERSION,
                },
            },
            "forwardSignalPolicy": {
                "direction": "long",
                "rules": [{"factorId": "rsi_14", "operator": "gte", "threshold": 50}],
            },
        },
    }


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return round(ordered[index], 3)


def run_top100_latency_rehearsal(
    *,
    iterations: int = 20,
    release_count: int = 10,
    report_path: Path | str = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    """Run scanner, arbitration, and latency gates entirely from in-memory public data."""

    run_count = max(1, int(iterations))
    strategy_count = max(1, int(release_count))
    now = datetime.now(UTC)
    instruments = [_instrument(index) for index in range(DEMO_DEEP_SCREENING_LIMIT)]
    candles = [
        {
            "timestamp": int((now - timedelta(minutes=(99 - index) * 5)).timestamp() * 1000),
            "open": 100.0,
            "high": 100.5,
            "low": 99.5,
            "close": 100.0,
            "volume": 1000.0,
            "confirmed": True,
        }
        for index in range(100)
    ]
    snapshots = {
        instrument: {
            "ok": True,
            "instId": instrument,
            "timeframe": "5m",
            "price": 100.0,
            "bidPrice": 99.99,
            "askPrice": 100.01,
            "spreadPct": 0.0002,
            "atr14": 1.0,
            "latestCandleAt": candles[-1]["timestamp"],
            "receivedAt": now.isoformat(),
            "_confirmedCandles": candles,
            "_precomputedFactors": {"rsi_14": 55.0, "atr_14": 1.0},
            "publicOnly": True,
        }
        for instrument in instruments
    }
    metadata = {
        instrument: {
            "ok": True,
            "instId": instrument,
            "state": "live",
            "ctVal": 0.01,
            "lotSz": 1.0,
            "minSz": 1.0,
            "tickSz": 0.01,
        }
        for instrument in instruments
    }
    universe = {
        "marketScope": "okx_usdt_linear_perpetual_full_market",
        "totalInstrumentCount": 405,
        "liveUsdtLinearSwapCount": 405,
        "liquidityEligibleCount": 375,
        "screeningPool": [
            {"instId": instrument, "quoteVolumeProxy": 1000 - index, "spreadPct": 0.0002}
            for index, instrument in enumerate(instruments)
        ],
        "errors": [],
        "publicOnly": True,
    }

    latencies: list[float] = []
    total_matches = 0
    selected_count = 0
    latency_classes: dict[str, int] = {}
    for _ in range(run_count):
        started = time.perf_counter()
        signals: list[dict[str, Any]] = []
        for release_index in range(strategy_count):
            scan = scan_immutable_demo_release(
                _release(release_index),
                snapshot_loader=lambda instrument, _timeframe, _limit: snapshots[instrument],
                metadata_loader=lambda instrument: metadata[instrument],
                universe_loader=lambda _limit: universe,
            )
            if scan.get("blockers"):
                raise RuntimeError("Top100 rehearsal scan failed: " + ",".join(scan["blockers"]))
            signals.extend(scan.get("signals") or [])
        total_matches += len(signals)
        arbitration = arbitrate_demo_signals(
            signals,
            maxPositions=min(10, len(instruments)),
            allowSameFamilyMultipleSymbols=True,
        )
        for signal in arbitration.selected:
            quote = snapshots[str(signal["instId"])]
            decision = evaluate_demo_entry_latency(
                signal,
                quote,
                close_received_at=now,
                order_ready_at=datetime.now(UTC),
                fee_rate=0.0005,
                slippage_rate=0.0002,
            )
            latency_classes[decision.latencyClass] = latency_classes.get(decision.latencyClass, 0) + 1
        selected_count += len(arbitration.selected)
        latencies.append((time.perf_counter() - started) * 1000.0)

    report = {
        "ok": True,
        "version": VERSION,
        "source": "top100_public_only_latency_rehearsal_v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "iterations": run_count,
        "releaseCount": strategy_count,
        "deepScreeningLimit": DEMO_DEEP_SCREENING_LIMIT,
        "marketScope": "okx_usdt_linear_perpetual_full_market",
        "matchedSignalCount": total_matches,
        "arbitratedSignalCount": selected_count,
        "latencyClasses": latency_classes,
        "latencyMs": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "max": round(max(latencies), 3),
        },
        "privateCallCount": 0,
        "orderCallCount": 0,
        "usesRecordedOrSyntheticPublicDataOnly": True,
        "createsDemoRelease": False,
        "changesRuntimeState": False,
    }
    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a no-order Top100 Demo latency rehearsal.")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--release-count", type=int, default=10)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()
    result = run_top100_latency_rehearsal(
        iterations=args.iterations,
        release_count=args.release_count,
        report_path=args.report,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
