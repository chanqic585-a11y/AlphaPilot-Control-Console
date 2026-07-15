from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_validation_release_store import (
    StrategyValidationReleaseStore,
)
from tests.strategy_validation_fixtures import canonical_bytes, make_release


class StrategyValidationReleaseStoreTests(unittest.TestCase):
    def test_import_preserves_canonical_bytes_and_does_not_enable_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StrategyValidationReleaseStore(root / "releases.sqlite", root / "contracts")
            release = make_release()
            raw = canonical_bytes(release)

            first = store.import_bytes(raw)
            second = store.import_bytes(raw)

            self.assertEqual(first["status"], "demo_waiting_approval")
            self.assertFalse(first["runtimeEligible"])
            self.assertEqual(second["importStatus"], "already_imported")
            self.assertEqual((root / "contracts" / f"{release['releaseHash']}.json").read_bytes(), raw)
            store.close()

    def test_changed_bytes_and_non_strategy_release_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StrategyValidationReleaseStore(root / "releases.sqlite", root / "contracts")
            release = make_release()
            store.import_bytes(canonical_bytes(release))

            changed = {**release, "strategyId": "changed"}
            with self.assertRaises(ValueError):
                store.import_bytes(canonical_bytes(changed))

            legacy = make_release(candidate_id="legacy")
            legacy["releasePurpose"] = "legacy_diagnostic"
            with self.assertRaises(ValueError):
                store.import_bytes(canonical_bytes(legacy))
            store.close()


if __name__ == "__main__":
    unittest.main()
