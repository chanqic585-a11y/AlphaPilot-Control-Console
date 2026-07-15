from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_validation_approval_store import (
    StrategyValidationApprovalStore,
)
from alphapilot_control_console.strategy_validation_release_store import (
    StrategyValidationReleaseStore,
)
from tests.strategy_validation_fixtures import canonical_bytes, make_release


class StrategyValidationApprovalTests(unittest.TestCase):
    def test_approval_is_hash_bound_append_only_and_does_not_arm(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = StrategyValidationReleaseStore(root / "releases.sqlite", root / "contracts")
            release = make_release()
            releases.import_bytes(canonical_bytes(release))
            approvals = StrategyValidationApprovalStore(root / "approvals.sqlite", releases)

            approved = approvals.approve(
                releaseId=release["releaseId"],
                releaseHash=release["releaseHash"],
                riskConfigHash=release["riskConfigHash"],
                reason="Local operator reviewed the immutable evidence.",
                actor="human_local_operator",
            )
            revoked = approvals.revoke(
                releaseId=release["releaseId"],
                releaseHash=release["releaseHash"],
                riskConfigHash=release["riskConfigHash"],
                reason="Operator stopped validation.",
                actor="human_local_operator",
            )

            self.assertTrue(approved["approved"])
            self.assertFalse(approved["runtimeArmed"])
            self.assertFalse(revoked["approved"])
            self.assertEqual(len(approvals.list_actions()), 2)
            self.assertEqual(
                approvals.list_actions()[1]["previousApprovalHash"],
                approvals.list_actions()[0]["recordHash"],
            )
            approvals.close()
            releases.close()

    def test_wrong_hash_or_non_human_actor_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = StrategyValidationReleaseStore(root / "releases.sqlite", root / "contracts")
            release = make_release()
            releases.import_bytes(canonical_bytes(release))
            approvals = StrategyValidationApprovalStore(root / "approvals.sqlite", releases)
            for actor in ("ai", "automation", "ml"):
                with self.assertRaises(PermissionError):
                    approvals.approve(
                        releaseId=release["releaseId"],
                        releaseHash=release["releaseHash"],
                        riskConfigHash=release["riskConfigHash"],
                        reason="not allowed",
                        actor=actor,
                    )
            with self.assertRaises(ValueError):
                approvals.approve(
                    releaseId=release["releaseId"],
                    releaseHash=release["releaseHash"],
                    riskConfigHash="changed-risk",
                    reason="wrong hash",
                    actor="human_local_operator",
                )
            approvals.close()
            releases.close()


if __name__ == "__main__":
    unittest.main()
