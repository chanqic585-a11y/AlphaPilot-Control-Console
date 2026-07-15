from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.strategy_validation_approval_store import StrategyValidationApprovalStore
from alphapilot_control_console.strategy_validation_release_store import StrategyValidationReleaseStore
from alphapilot_control_console.strategy_validation_runtime_admission import StrategyValidationRuntimeAdmission
from tests.strategy_validation_fixtures import canonical_bytes, make_release


class StrategyValidationRuntimeAdmissionTests(unittest.TestCase):
    def test_approval_and_arm_are_independent_and_all_runtime_gates_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = StrategyValidationReleaseStore(root / "releases.sqlite", root / "contracts")
            release = make_release()
            releases.import_bytes(canonical_bytes(release))
            approvals = StrategyValidationApprovalStore(root / "approvals.sqlite", releases)
            runtime = StrategyValidationRuntimeAdmission(root / "runtime.sqlite", releases, approvals)

            self.assertEqual(runtime.evaluate(release["releaseId"], universeFresh=True)["status"], "not_approved")
            approvals.approve(
                releaseId=release["releaseId"], releaseHash=release["releaseHash"],
                riskConfigHash=release["riskConfigHash"], reason="reviewed",
                actor="human_local_operator",
            )
            self.assertEqual(runtime.evaluate(release["releaseId"], universeFresh=True)["status"], "not_armed")
            runtime.arm(reason="Start isolated strategy validation", actor="human_local_operator")
            self.assertEqual(runtime.evaluate(release["releaseId"], universeFresh=False)["status"], "universe_stale")
            self.assertTrue(runtime.evaluate(release["releaseId"], universeFresh=True)["eligible"])
            runtime.close()
            approvals.close()
            releases.close()


if __name__ == "__main__":
    unittest.main()
