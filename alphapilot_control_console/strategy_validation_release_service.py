"""Import formal candidate releases from one bounded Quant campaign."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import get_quant_engine_path
from .strategy_validation_release_store import StrategyValidationReleaseStore


CAMPAIGN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")


class StrategyValidationReleaseService:
    def __init__(
        self,
        store: StrategyValidationReleaseStore,
        *,
        quant_root: Path | str | None = None,
    ):
        self.store = store
        self.quant_root = Path(quant_root) if quant_root is not None else get_quant_engine_path()

    def import_campaign(self, campaign_id: str) -> dict[str, Any]:
        if not CAMPAIGN_ID_PATTERN.fullmatch(campaign_id):
            raise ValueError("invalid campaign id")
        campaign_dir = self.quant_root / "reports" / "backtest_screening" / campaign_id
        candidate_dir = campaign_dir / "candidate_releases"
        if not candidate_dir.is_dir():
            raise FileNotFoundError("candidate release directory not found")
        summary_path = candidate_dir / "generation_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
        imported: list[dict[str, Any]] = []
        for path in sorted(candidate_dir.glob("*.json")):
            if path.name in {"generation_summary.json", "demo_risk_profile.json"}:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid release JSON: {path.name}") from error
            if payload.get("schemaVersion") not in {
                "strategy_validation_release_v1",
                "strategy_validation_release_v2",
            }:
                continue
            imported.append(self.store.import_file(path))
        expected = int(summary.get("releaseCount") or 0)
        if expected != len(imported):
            raise ValueError("release generation summary does not match immutable files")
        return {
            "campaignId": campaign_id,
            "expectedReleaseCount": expected,
            "importedReleaseCount": len(imported),
            "releases": imported,
            "runtimeEnabled": False,
            "ordersCreated": 0,
            "approvalRecordsCreated": 0,
        }
