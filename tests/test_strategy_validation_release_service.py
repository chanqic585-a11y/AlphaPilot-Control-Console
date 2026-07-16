from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_validation_release_service import StrategyValidationReleaseService
from alphapilot_control_console.strategy_validation_release_store import StrategyValidationReleaseStore
from tests.strategy_validation_fixtures import canonical_bytes, make_advisory_release


class StrategyValidationReleaseServiceTests(unittest.TestCase):
    def test_zero_release_campaign_import_is_valid_and_creates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_dir = root / "reports" / "backtest_screening" / "campaign-1" / "candidate_releases"
            candidate_dir.mkdir(parents=True)
            (candidate_dir / "generation_summary.json").write_text(
                json.dumps({"campaignId": "campaign-1", "releaseCount": 0}), encoding="utf-8"
            )
            (candidate_dir / "demo_risk_profile.json").write_text("{}", encoding="utf-8")
            store = StrategyValidationReleaseStore(root / "releases.sqlite", root / "contracts")
            service = StrategyValidationReleaseService(store, quant_root=root)

            result = service.import_campaign("campaign-1")

            self.assertEqual(result["importedReleaseCount"], 0)
            self.assertEqual(result["ordersCreated"], 0)
            self.assertEqual(result["approvalRecordsCreated"], 0)
            store.close()

    def test_campaign_import_accepts_schema_v2_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_dir = root / "reports" / "backtest_screening" / "campaign-2" / "candidate_releases"
            candidate_dir.mkdir(parents=True)
            release = make_advisory_release()
            (candidate_dir / f"{release['releaseHash']}.json").write_bytes(canonical_bytes(release))
            (candidate_dir / "generation_summary.json").write_text(
                json.dumps({"campaignId": "campaign-2", "releaseCount": 1}),
                encoding="utf-8",
            )
            store = StrategyValidationReleaseStore(root / "releases.sqlite", root / "contracts")
            service = StrategyValidationReleaseService(store, quant_root=root)

            result = service.import_campaign("campaign-2")

            self.assertEqual(result["importedReleaseCount"], 1)
            self.assertFalse(result["runtimeEnabled"])
            self.assertEqual(result["ordersCreated"], 0)
            store.close()


if __name__ == "__main__":
    unittest.main()
