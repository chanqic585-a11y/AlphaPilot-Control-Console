from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.v62_4_1_matchability import (
    build_factor_frame,
    evaluate_factor_frame_windows,
)


DEFAULT_SNAPSHOT = Path(
    "D:/Codex-Workspace/回测数据/_alphapilot/manifests/snapshots/"
    "data_snapshot_8dfc277bce273551edbad8cc83598c0146486fb568c5bbb7236cdd4d7fb7b118.json"
)
DEFAULT_RUNTIME_EVIDENCE = Path(
    "D:/Codex-Workspace/validation/v62-4-1-runtime-evidence-20260723"
)
RELEASE_RELATIVE_PATH = Path(
    "data/v54_v60/release/final_superseding_provisional_release.json"
)
CONTRACTS_RELATIVE_PATH = Path(
    "data/v54_v60/release/source_component_contracts"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _artifact(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["artifactHash"] = _canonical_hash(result)
    return result


def _manifest_files_by_key(snapshot: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item in snapshot.get("files", []):
        relative = str(item.get("path") or "").replace("\\", "/")
        parts = relative.split("/")
        if len(parts) < 6 or parts[2] != "ohlcv":
            continue
        result[(parts[3], parts[4])] = dict(item)
    return result


def _load_candles(
    *,
    canonical_root: Path,
    entry: dict[str, Any],
    cutoff: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = canonical_root / str(entry["path"])
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_size = path.stat().st_size
    actual_hash = _sha256(path)
    if actual_size != int(entry["size"]):
        raise ValueError(f"snapshot size mismatch: {path}")
    if actual_hash != str(entry["sha256"]):
        raise ValueError(f"snapshot sha256 mismatch: {path}")
    columns = [
        "timestamp_ms",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "confirmed",
    ]
    candles = pd.read_parquet(path, columns=columns)
    candles["date"] = pd.to_datetime(candles["date"], utc=True)
    candles = candles.loc[candles["date"] <= cutoff].copy()
    receipt = {
        "path": str(path),
        "relativePath": str(entry["path"]),
        "sha256": actual_hash,
        "size": actual_size,
        "rowCountAtOrBeforeCutoff": int(len(candles)),
        "firstAt": (
            candles["date"].min().isoformat() if not candles.empty else None
        ),
        "lastAt": (
            candles["date"].max().isoformat() if not candles.empty else None
        ),
        "validated": True,
    }
    return candles, receipt


def _contract(repo: Path, candidate_id: str) -> dict[str, Any]:
    path = repo / CONTRACTS_RELATIVE_PATH / f"{candidate_id}.json"
    value = _read_json(path)
    if value.get("strategyCandidateId") != candidate_id:
        raise ValueError(f"component identity mismatch: {path}")
    return value


def _merge_failed_checks(results: list[dict[str, Any]], window: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for result in results:
        counts.update(result["windows"][window]["failedCheckCounts"])
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _component_summary(
    *,
    candidate_id: str,
    timeframe: str,
    policy: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    windows: dict[str, Any] = {}
    for window in ("30d", "90d"):
        signal_count = sum(
            int(result["windows"][window]["matchedSignalCount"])
            for result in results
        )
        matched = [
            {
                "instrument": result["instrument"],
                "matchedSignalCount": result["windows"][window][
                    "matchedSignalCount"
                ],
                "firstSignalAt": result["windows"][window]["firstSignalAt"],
                "lastSignalAt": result["windows"][window]["lastSignalAt"],
            }
            for result in results
            if result["windows"][window]["matchedSignalCount"] > 0
        ]
        matched.sort(
            key=lambda item: (-int(item["matchedSignalCount"]), item["instrument"])
        )
        windows[window] = {
            "evaluatedInstrumentCount": len(results),
            "matchedInstrumentCount": len(matched),
            "matchedSignalCount": signal_count,
            "evaluatedBarCount": sum(
                int(result["windows"][window]["evaluatedBarCount"])
                for result in results
            ),
            "indicatorReadyCount": sum(
                int(result["windows"][window]["indicatorReadyCount"])
                for result in results
            ),
            "topMatchedInstruments": matched[:20],
            "failedCheckCounts": _merge_failed_checks(results, window),
        }
    return {
        "candidateId": candidate_id,
        "timeframe": timeframe,
        "family": policy.get("family"),
        "direction": policy.get("direction"),
        "policy": policy,
        "windows": windows,
        "perInstrument": results,
    }


def _summary_markdown(
    *,
    release: dict[str, Any],
    snapshot: dict[str, Any],
    components: list[dict[str, Any]],
    broad: dict[str, Any],
    frequency: dict[str, Any],
) -> str:
    lines = [
        "# V62.4.1 Matchability Evidence",
        "",
        f"- Release: `{release['releaseId']}`",
        f"- Release Hash: `{release['releaseHash']}`",
        f"- Risk Overlay Hash: `{release['riskOverlayHash']}`",
        f"- Data Snapshot: `{snapshot['dataSnapshotId']}`",
        f"- PIT Cutoff: `{snapshot['pointInTimeCutoff']}`",
        f"- Historical universe: {len(snapshot['universeMembers'])} instruments",
        "- Execution boundary: read-only historical policy replay; no private API and no orders.",
        "",
        "## Components",
        "",
        "| Candidate | Timeframe | 30d signals | 90d signals |",
        "|---|---:|---:|---:|",
    ]
    for component in components:
        lines.append(
            "| {candidate} | {timeframe} | {signals30} | {signals90} |".format(
                candidate=component["candidateId"],
                timeframe=component["timeframe"],
                signals30=component["windows"]["30d"]["matchedSignalCount"],
                signals90=component["windows"]["90d"]["matchedSignalCount"],
            )
        )
    lines.extend(
        [
            "",
            "## Scope truth",
            "",
            f"- Historical TOP200 replay: `{broad['top200HistoricalReplayStatus']}`.",
            f"- Current Release instruments: {broad['currentReleaseActualInstrumentCount']}.",
            f"- Maximum recorded runtime market instruments: {broad['runtimeMaximumObservedMarketInstrumentCount']}.",
            f"- Mid-frequency evidence: `{frequency['status']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--runtime-evidence", type=Path, default=DEFAULT_RUNTIME_EVIDENCE
    )
    parser.add_argument("--repo", type=Path, default=REPOSITORY_ROOT)
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    snapshot_path = args.snapshot.resolve()
    snapshot = _read_json(snapshot_path)
    release_path = args.repo.resolve() / RELEASE_RELATIVE_PATH
    release = _read_json(release_path)
    cutoff = pd.Timestamp(snapshot["pointInTimeCutoff"])
    canonical_root = snapshot_path.parents[2] / "canonical"
    files_by_key = _manifest_files_by_key(snapshot)
    universe = [str(value) for value in snapshot["universeMembers"]]
    component_ids = [str(value) for value in release["componentIds"]]
    created_at = datetime.now(UTC).isoformat()

    component_contracts = [_contract(args.repo.resolve(), value) for value in component_ids]
    timeframes = sorted(
        {
            str(contract["strategy"]["marketDefinition"]["timeframe"])
            for contract in component_contracts
        }
    )
    btc_frames: dict[str, pd.DataFrame] = {}
    file_receipts: dict[tuple[str, str], dict[str, Any]] = {}
    factor_cache: dict[tuple[str, str], pd.DataFrame] = {}

    for timeframe in timeframes:
        entry = files_by_key.get(("BTC-USDT-SWAP", timeframe))
        if entry is None:
            raise ValueError(f"BTC snapshot file missing for {timeframe}")
        candles, receipt = _load_candles(
            canonical_root=canonical_root,
            entry=entry,
            cutoff=cutoff,
        )
        file_receipts[("BTC-USDT-SWAP", timeframe)] = receipt
        btc_frames[timeframe] = build_factor_frame(candles)
        factor_cache[("BTC-USDT-SWAP", timeframe)] = btc_frames[timeframe]

    component_summaries: list[dict[str, Any]] = []
    funnel_rows: list[dict[str, Any]] = []
    for contract in component_contracts:
        candidate_id = str(contract["strategyCandidateId"])
        strategy = contract["strategy"]
        timeframe = str(strategy["marketDefinition"]["timeframe"])
        policy = dict(strategy["forwardSignalPolicy"])
        per_instrument: list[dict[str, Any]] = []
        for instrument in universe:
            entry = files_by_key.get((instrument, timeframe))
            if entry is None:
                raise ValueError(f"snapshot file missing: {instrument} {timeframe}")
            cache_key = (instrument, timeframe)
            factors = factor_cache.get(cache_key)
            if factors is None:
                candles, receipt = _load_candles(
                    canonical_root=canonical_root,
                    entry=entry,
                    cutoff=cutoff,
                )
                file_receipts[cache_key] = receipt
                factors = build_factor_frame(candles)
                factor_cache[cache_key] = factors
            result = evaluate_factor_frame_windows(
                candidate_id=candidate_id,
                instrument=instrument,
                factor_frame=factors,
                btc_factor_frame=btc_frames[timeframe],
                policy=policy,
                as_of=cutoff.to_pydatetime(),
                windows=(30, 90),
            )
            per_instrument.append(result)
        summary = _component_summary(
            candidate_id=candidate_id,
            timeframe=timeframe,
            policy=policy,
            results=per_instrument,
        )
        component_summaries.append(summary)
        for window in ("30d", "90d"):
            row = summary["windows"][window]
            funnel_rows.append(
                {
                    "candidateId": candidate_id,
                    "timeframe": timeframe,
                    "family": summary["family"],
                    "direction": summary["direction"],
                    "window": window,
                    "evaluatedInstrumentCount": row["evaluatedInstrumentCount"],
                    "matchedInstrumentCount": row["matchedInstrumentCount"],
                    "evaluatedBarCount": row["evaluatedBarCount"],
                    "indicatorReadyCount": row["indicatorReadyCount"],
                    "matchedSignalCount": row["matchedSignalCount"],
                }
            )

    runtime_audit = _read_json(
        args.runtime_evidence.resolve() / "matchability_recorded_runtime_audit.json"
    )
    parity = _read_json(
        args.runtime_evidence.resolve() / "historical_shadow_parity_1h_1d.json"
    )
    broad = _artifact(
        {
            "schemaVersion": "v62_4_1_broad_universe_successor_audit_v1",
            "createdAt": created_at,
            "releaseId": release["releaseId"],
            "releaseHash": release["releaseHash"],
            "historicalSnapshotId": snapshot["dataSnapshotId"],
            "historicalInstrumentCount": len(universe),
            "currentReleaseActualInstrumentCount": release["actualInstrumentCount"],
            "currentReleaseMaximumInstrumentCount": release[
                "maximumInstrumentCount"
            ],
            "runtimeMaximumObservedMarketInstrumentCount": runtime_audit[
                "broadUniverse"
            ]["maximumObservedMarketInstrumentCount"],
            "runtimeMaximumObservedLiquidityEligibleCount": runtime_audit[
                "broadUniverse"
            ]["maximumObservedLiquidityEligibleCount"],
            "runtimeMaximumObservedDeepEvaluationCount": runtime_audit[
                "broadUniverse"
            ]["maximumObservedDeepEvaluationCount"],
            "historical50InstrumentReplayStatus": "completed",
            "top200HistoricalReplayStatus": "not_run_snapshot_limited_to_50",
            "runtimeClosedBatchParityStatus": parity["status"],
            "scopeBoundary": (
                "Historical policy replay covers 50 governed user-approved local "
                "instruments. It is not relabeled as a TOP200 historical replay."
            ),
            "privateEndpointReachable": False,
            "orderClientReachable": False,
        }
    )
    one_hour = [
        value for value in component_summaries if value["timeframe"] == "1h"
    ]
    frequency = _artifact(
        {
            "schemaVersion": "v62_4_1_frequency_evidence_v1",
            "createdAt": created_at,
            "currentReleaseTimeframes": timeframes,
            "existingOneHourMechanismCount": len(one_hour),
            "oneHour30dMatchedSignalCount": sum(
                value["windows"]["30d"]["matchedSignalCount"] for value in one_hour
            ),
            "oneHour90dMatchedSignalCount": sum(
                value["windows"]["90d"]["matchedSignalCount"] for value in one_hour
            ),
            "fourHourCurrentReleaseMechanismCount": sum(
                1 for value in component_summaries if value["timeframe"] == "4h"
            ),
            "status": (
                "passed_existing_1h_mechanism_replayed"
                if one_hour
                else "not_evaluable_no_mid_frequency_component"
            ),
            "newCandidateInvented": False,
            "promotionClaimed": False,
        }
    )
    mid_frequency = _artifact(
        {
            "schemaVersion": "v62_4_1_mid_frequency_mechanism_pilot_v1",
            "createdAt": created_at,
            "candidateId": one_hour[0]["candidateId"] if one_hour else None,
            "family": one_hour[0]["family"] if one_hour else None,
            "direction": one_hour[0]["direction"] if one_hour else None,
            "timeframe": "1h" if one_hour else None,
            "windowResults": one_hour[0]["windows"] if one_hour else None,
            "evidenceClass": "bounded_historical_policy_replay",
            "formalPass": False,
            "demoPromotionEligible": False,
            "note": (
                "This audits the existing frozen one-hour component; it does not "
                "create or promote a new strategy."
            ),
        }
    )

    common = {
        "schemaVersion": "v62_4_1_historical_matchability_v1",
        "createdAt": created_at,
        "releaseId": release["releaseId"],
        "releaseHash": release["releaseHash"],
        "riskOverlayHash": release["riskOverlayHash"],
        "dataSnapshotId": snapshot["dataSnapshotId"],
        "dataSnapshotManifestHash": snapshot["manifestHash"],
        "snapshotFileSha256": _sha256(snapshot_path),
        "pointInTimeCutoff": snapshot["pointInTimeCutoff"],
        "historicalInstrumentCount": len(universe),
        "dataSource": snapshot["source"],
        "exchangeLabel": snapshot["exchange"],
        "evidenceClass": "bounded_historical_policy_replay",
        "formalPass": False,
        "securityBoundary": {
            "privateEndpointReachable": False,
            "orderClientReachable": False,
            "canCreateOrder": False,
            "liveEnabled": False,
            "withdrawEnabled": False,
        },
    }
    details = _artifact({**common, "components": component_summaries})
    matchability_30d = _artifact(
        {
            **common,
            "windowDays": 30,
            "components": [
                {
                    "candidateId": value["candidateId"],
                    "timeframe": value["timeframe"],
                    "family": value["family"],
                    "direction": value["direction"],
                    **value["windows"]["30d"],
                }
                for value in component_summaries
            ],
        }
    )
    matchability_90d = _artifact(
        {
            **common,
            "windowDays": 90,
            "components": [
                {
                    "candidateId": value["candidateId"],
                    "timeframe": value["timeframe"],
                    "family": value["family"],
                    "direction": value["direction"],
                    **value["windows"]["90d"],
                }
                for value in component_summaries
            ],
        }
    )
    snapshot_receipt = _artifact(
        {
            "schemaVersion": "v62_4_1_snapshot_validation_receipt_v1",
            "createdAt": created_at,
            "snapshotPath": str(snapshot_path),
            "snapshotFileSha256": _sha256(snapshot_path),
            "declaredDataSnapshotId": snapshot["dataSnapshotId"],
            "declaredManifestHash": snapshot["manifestHash"],
            "pointInTimeCutoff": snapshot["pointInTimeCutoff"],
            "validatedFileCount": len(file_receipts),
            "files": sorted(
                file_receipts.values(), key=lambda item: item["relativePath"]
            ),
            "status": "passed",
        }
    )

    outputs = {
        "strategy_matchability_by_component.json": details,
        "matchability_30d.json": matchability_30d,
        "matchability_90d.json": matchability_90d,
        "broad_universe_successor_audit.json": broad,
        "frequency_evidence.json": frequency,
        "mid_frequency_mechanism_pilot.json": mid_frequency,
        "snapshot_validation_receipt.json": snapshot_receipt,
    }
    for name, value in outputs.items():
        _write_json(output / name, value)
    _write_csv(output / "component_matchability_funnel.csv", funnel_rows)
    (output / "summary.md").write_text(
        _summary_markdown(
            release=release,
            snapshot=snapshot,
            components=component_summaries,
            broad=broad,
            frequency=frequency,
        ),
        encoding="utf-8",
    )

    manifest_rows: list[dict[str, Any]] = []
    for path in sorted(output.iterdir(), key=lambda value: value.name):
        if path.is_file():
            manifest_rows.append(
                {
                    "path": path.name,
                    "size": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    manifest = _artifact(
        {
            "schemaVersion": "v62_4_1_matchability_artifact_manifest_v1",
            "createdAt": created_at,
            "releaseId": release["releaseId"],
            "releaseHash": release["releaseHash"],
            "artifacts": manifest_rows,
        }
    )
    _write_json(output / "artifact_manifest.json", manifest)

    print(
        json.dumps(
            {
                "status": "completed",
                "output": str(output),
                "historicalInstrumentCount": len(universe),
                "components": [
                    {
                        "candidateId": value["candidateId"],
                        "timeframe": value["timeframe"],
                        "signals30d": value["windows"]["30d"][
                            "matchedSignalCount"
                        ],
                        "signals90d": value["windows"]["90d"][
                            "matchedSignalCount"
                        ],
                    }
                    for value in component_summaries
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
