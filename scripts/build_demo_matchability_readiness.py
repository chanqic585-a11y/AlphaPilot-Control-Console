from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.demo_matchability_readiness import (
    build_matchability_readiness,
    write_matchability_artifacts,
)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _candidate_cards(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.is_file():
        return {}
    payload = _json(path)
    rows = payload.get("selectedCandidates") if isinstance(payload, dict) else []
    return {
        str(row.get("candidateId")): dict(row)
        for row in rows or []
        if isinstance(row, dict) and row.get("candidateId")
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build public-only Demo matchability readiness.")
    parser.add_argument("--release", required=True, type=Path)
    parser.add_argument("--contract-inventory", required=True, type=Path)
    parser.add_argument("--trade-ledger-dir", required=True, type=Path)
    parser.add_argument("--candidate-cards", type=Path)
    parser.add_argument("--as-of")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import pandas as pd
    except ImportError as error:
        raise SystemExit("pandas with parquet support is required for this evidence builder") from error

    release = _json(args.release)
    component_ids = {str(value) for value in release.get("componentIds") or []}
    inventory = _json(args.contract_inventory)
    if not isinstance(inventory, list):
        raise SystemExit("contract inventory must be an array")
    cards = _candidate_cards(args.candidate_cards)
    components: list[dict[str, Any]] = []
    for row in inventory:
        if not isinstance(row, dict):
            continue
        candidate_id = str(row.get("strategyCandidateId") or "")
        if candidate_id not in component_ids:
            continue
        component = dict(row)
        card = cards.get(candidate_id) or {}
        asset_filter = card.get("assetFilter") if isinstance(card.get("assetFilter"), dict) else {}
        selected_pairs = asset_filter.get("selectedPairs")
        if isinstance(selected_pairs, list) and selected_pairs:
            component["selectedPairs"] = list(selected_pairs)
        components.append(component)
    missing_components = sorted(component_ids.difference({str(row.get("strategyCandidateId")) for row in components}))
    if missing_components:
        raise SystemExit("missing component contracts: " + ",".join(missing_components))

    trades_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for candidate_id in sorted(component_ids):
        path = args.trade_ledger_dir / f"{candidate_id}.parquet"
        if not path.is_file():
            raise SystemExit(f"missing component trade ledger: {path}")
        trades_by_candidate[candidate_id] = pd.read_parquet(path).to_dict(orient="records")

    result = build_matchability_readiness(
        release=release,
        components=components,
        trades_by_candidate=trades_by_candidate,
        as_of=args.as_of,
    )
    write_matchability_artifacts(args.output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "headline": result["headline"],
                "asOf": result["asOf"],
                "output": str(args.output.resolve()),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if result["status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
