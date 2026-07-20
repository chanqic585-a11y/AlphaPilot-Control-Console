"""Public-evidence-only readiness checks for a frozen Demo release."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


def canonical_demo_instrument_from_pair(value: object) -> str | None:
    text = str(value or "").strip().upper()
    if text.endswith("-USDT-SWAP") and text.count("-") == 2:
        return text
    if "/USDT:USDT" not in text:
        return None
    base, suffix = text.split("/", 1)
    if not base or suffix != "USDT:USDT":
        return None
    return f"{base}-USDT-SWAP"


def _utc(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _component_id(component: Mapping[str, Any]) -> str:
    return str(component.get("strategyCandidateId") or component.get("candidateId") or "")


def _selected_instruments(component: Mapping[str, Any]) -> set[str]:
    values = component.get("selectedPairs")
    if not isinstance(values, list):
        return set()
    return {
        instrument
        for value in values
        if (instrument := canonical_demo_instrument_from_pair(value))
    }


def _uses_full_market(component: Mapping[str, Any]) -> bool:
    market = component.get("marketDefinition")
    if not isinstance(market, Mapping):
        return False
    universe = market.get("universePolicy")
    if not isinstance(universe, Mapping):
        return False
    return str(universe.get("mode") or "") == "okx_usdt_linear_perpetual_full_market"


def _trade_instrument(row: Mapping[str, Any]) -> str | None:
    return canonical_demo_instrument_from_pair(row.get("instId") or row.get("pair"))


def build_matchability_readiness(
    *,
    release: Mapping[str, Any],
    components: Iterable[Mapping[str, Any]],
    trades_by_candidate: Mapping[str, Iterable[Mapping[str, Any]]],
    as_of: str | None = None,
) -> dict[str, Any]:
    release_instruments = {
        str(value).strip().upper()
        for value in release.get("executionInstruments") or []
        if str(value).strip()
    }
    component_rows = [dict(row) for row in components]
    observed_dates = [
        parsed
        for rows in trades_by_candidate.values()
        for row in rows
        if (parsed := _utc(row.get("entryDate"))) is not None
    ]
    as_of_date = _utc(as_of) if as_of else (max(observed_dates) if observed_dates else None)
    if as_of_date is None:
        raise ValueError("matchability_as_of_is_required_without_trade_dates")

    blockers: list[str] = []
    warnings: list[str] = []
    results: list[dict[str, Any]] = []
    total_30d = 0
    total_90d = 0
    compatible_component_count = 0
    components_with_30d = 0
    components_with_90d = 0
    historically_observed: set[str] = set()

    for component in component_rows:
        candidate_id = _component_id(component)
        selected = _selected_instruments(component)
        full_market = _uses_full_market(component)
        eligible = release_instruments if full_market and not selected else selected
        compatible = sorted(release_instruments.intersection(eligible))
        if compatible:
            compatible_component_count += 1
        else:
            blockers.append("component_universe_intersection_empty")

        trades = [dict(row) for row in trades_by_candidate.get(candidate_id, [])]
        compatible_set = set(compatible)
        dated_rows: list[tuple[datetime, str]] = []
        for trade in trades:
            entry_date = _utc(trade.get("entryDate"))
            instrument = _trade_instrument(trade)
            if entry_date is None or instrument is None:
                continue
            historically_observed.add(instrument)
            if instrument in compatible_set:
                dated_rows.append((entry_date, instrument))

        count_30d = sum(1 for date, _ in dated_rows if date >= as_of_date - timedelta(days=30))
        count_90d = sum(1 for date, _ in dated_rows if date >= as_of_date - timedelta(days=90))
        total_30d += count_30d
        total_90d += count_90d
        components_with_30d += int(count_30d > 0)
        components_with_90d += int(count_90d > 0)
        if count_30d == 0:
            warnings.append(f"component_without_signal_30d:{candidate_id}")
        if count_90d == 0:
            warnings.append(f"component_without_signal_90d:{candidate_id}")

        results.append(
            {
                "candidateId": candidate_id,
                "family": component.get("familyKey") or component.get("family"),
                "direction": component.get("direction"),
                "timeframe": component.get("timeframe")
                or (component.get("marketDefinition") or {}).get("timeframe"),
                "sourceUniverseMode": (
                    "selected_pairs" if selected else "full_market" if full_market else "undefined"
                ),
                "sourceInstrumentCount": len(selected) if selected else len(release_instruments),
                "compatibleInstrumentCount": len(compatible),
                "historicallyObservedInstrumentCount": len({value for _, value in dated_rows}),
                "historicalTradeCount": len(dated_rows),
                "signalCount30d": count_30d,
                "signalCount90d": count_90d,
                "lastSignalAt": _iso_z(max(date for date, _ in dated_rows)) if dated_rows else None,
                "blockers": [] if compatible else ["component_universe_intersection_empty"],
            }
        )

    blockers = sorted(set(blockers))
    if total_90d == 0:
        warnings.append("no_historical_signal_in_90d")
    warnings = sorted(set(warnings))
    status = (
        "blocked"
        if blockers
        else "ready_with_sparse_signal_warning"
        if warnings
        else "ready"
    )
    return {
        "schemaVersion": "demo_matchability_readiness_v1",
        "status": status,
        "releaseId": release.get("releaseId"),
        "releaseHash": release.get("releaseHash"),
        "asOf": _iso_z(as_of_date),
        "headline": {
            "releaseInstrumentCount": len(release_instruments),
            "compatibleComponentCount": compatible_component_count,
            "signalCount30d": total_30d,
            "signalCount90d": total_90d,
        },
        "components": results,
        "preArmFunnel": {
            "releaseInstrumentCount": len(release_instruments),
            "historicallyObservedInstrumentCount": len(
                release_instruments.intersection(historically_observed)
            ),
            "compatibleComponentCount": compatible_component_count,
            "componentWithSignal30dCount": components_with_30d,
            "componentWithSignal90dCount": components_with_90d,
            "strategyOrderCount": 0,
        },
        "securityBoundary": {
            "publicEvidenceOnly": True,
            "privateEndpointReachable": False,
            "orderClientReachable": False,
            "canCreateOrder": False,
        },
        "blockers": blockers,
        "warnings": warnings,
    }


def write_matchability_artifacts(output_dir: Path | str, result: Mapping[str, Any]) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    body = dict(result)
    components = list(body.get("components") or [])
    for days in (30, 90):
        payload = {
            "schemaVersion": f"demo_signal_matchability_{days}d_v1",
            "status": body.get("status"),
            "releaseId": body.get("releaseId"),
            "releaseHash": body.get("releaseHash"),
            "asOf": body.get("asOf"),
            "windowDays": days,
            "signalCount": int((body.get("headline") or {}).get(f"signalCount{days}d") or 0),
            "components": [
                {
                    "candidateId": row.get("candidateId"),
                    "timeframe": row.get("timeframe"),
                    "compatibleInstrumentCount": row.get("compatibleInstrumentCount"),
                    "signalCount": row.get(f"signalCount{days}d"),
                    "lastSignalAt": row.get("lastSignalAt"),
                }
                for row in components
            ],
            "securityBoundary": body.get("securityBoundary"),
            "blockers": body.get("blockers"),
            "warnings": body.get("warnings"),
        }
        (root / f"signal_matchability_{days}d.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (root / "pre_arm_scan_funnel.json").write_text(
        json.dumps(
            {
                "schemaVersion": "demo_pre_arm_scan_funnel_v1",
                "status": body.get("status"),
                "releaseId": body.get("releaseId"),
                "asOf": body.get("asOf"),
                **dict(body.get("preArmFunnel") or {}),
                "blockers": body.get("blockers"),
                "warnings": body.get("warnings"),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    with (root / "component_signal_matchability.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        columns = [
            "candidateId",
            "family",
            "direction",
            "timeframe",
            "sourceUniverseMode",
            "sourceInstrumentCount",
            "compatibleInstrumentCount",
            "historicallyObservedInstrumentCount",
            "historicalTradeCount",
            "signalCount30d",
            "signalCount90d",
            "lastSignalAt",
        ]
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(components)
