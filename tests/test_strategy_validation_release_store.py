from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_validation_release_store import (
    StrategyValidationReleaseStore,
)
from tests.strategy_validation_fixtures import (
    canonical_bytes,
    make_advisory_release,
    make_exit_policy,
    make_release,
)


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

    def test_schema_v2_accepts_fixed_r_below_two_and_structure_without_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StrategyValidationReleaseStore(root / "releases.sqlite", root / "contracts")
            fixed = make_advisory_release()
            structure = make_advisory_release(
                strategy_id="structure-candidate",
                exit_policy=make_exit_policy(
                    mode="structure_or_time",
                    parameters={
                        "structureRule": {
                            "kind": "event_reversal",
                            "confirmationBars": 2,
                        }
                    },
                ),
            )

            fixed_result = store.import_bytes(canonical_bytes(fixed))
            structure_result = store.import_bytes(canonical_bytes(structure))

            self.assertEqual(fixed_result["status"], "demo_waiting_approval")
            self.assertFalse(fixed_result["runtimeEligible"])
            self.assertEqual(structure_result["candidateId"], "structure-candidate")
            self.assertEqual(store.payload(structure["releaseId"])["canonicalExitPolicy"]["mode"], "structure_or_time")
            store.close()

    def test_schema_v2_rejects_incomplete_mutable_or_hash_changed_exit_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StrategyValidationReleaseStore(root / "releases.sqlite", root / "contracts")

            incomplete = make_advisory_release()
            incomplete["canonicalExitPolicy"] = {
                key: value
                for key, value in incomplete["canonicalExitPolicy"].items()
                if key != "parameters"
            }
            with self.assertRaisesRegex(ValueError, "exit policy"):
                store.import_bytes(canonical_bytes(incomplete))

            mutable = make_advisory_release(
                exit_policy=make_exit_policy(initial_stop_may_widen=True)
            )
            with self.assertRaisesRegex(ValueError, "stop"):
                store.import_bytes(canonical_bytes(mutable))

            wrong_hash = make_advisory_release()
            wrong_hash["exitPolicyHash"] = "exit_policy_changed"
            with self.assertRaisesRegex(ValueError, "policy hash"):
                store.import_bytes(canonical_bytes(wrong_hash))
            store.close()


if __name__ == "__main__":
    unittest.main()
