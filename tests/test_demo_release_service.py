from __future__ import annotations

import unittest
from unittest.mock import patch

from alphapilot_control_console import demo_release_service as service


class DemoReleaseServiceTests(unittest.TestCase):
    def test_pre_arm_readiness_ignores_only_expected_empty_release_transition(
        self,
    ) -> None:
        release = {"dynamicUniversePolicyHash": "policy-hash"}

        def fake_load(path):
            if path == service.ENGINEERING_SMOKE_PATH:
                return {
                    "status": "passed",
                    "engineeringSmokeReady": True,
                    "unknownStateCount": 0,
                    "orphanOrderCount": 0,
                    "orphanPositionCount": 0,
                }
            if path == service.TOP200_SNAPSHOT_PATH:
                return {"policyHash": "policy-hash"}
            if path == service.TOP200_READINESS_PATH:
                return {"authenticatedInstrumentCount": 116}
            raise AssertionError(f"unexpected path: {path}")

        with (
            patch.object(service, "_load", side_effect=fake_load),
            patch.object(
                service,
                "build_evolution_demo_status",
                return_value={
                    "summary": {"killSwitch": False},
                    "blockers": [
                        "no_eligible_demo_release",
                        "demo_runtime_paused",
                    ],
                },
            ),
            patch.object(
                service,
                "runtime_credential_status",
                return_value={"allConfigured": True},
            ),
        ):
            readiness = service._runtime_readiness(release)

        self.assertEqual(readiness["riskBlockers"], ["demo_runtime_paused"])


if __name__ == "__main__":
    unittest.main()
