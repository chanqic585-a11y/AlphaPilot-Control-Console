from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
import unittest

from alphapilot_control_console.runtime_identity import (
    RuntimeIdentity,
    RuntimeIdentityMismatch,
    assert_runtime_identity,
    evaluate_runtime_identity,
)


def _identity(**overrides: object) -> RuntimeIdentity:
    values: dict[str, object] = {
        "runtimeId": "runtime-demo-1",
        "environment": "okx_demo",
        "processId": 4321,
        "repositoryCommit": "a" * 40,
        "repositoryTag": "v13.27.1.62.4",
        "moduleRootHashes": {"execution": "b" * 64, "risk": "c" * 64},
        "releaseId": "release-1",
        "releaseHash": "d" * 64,
        "riskOverlayHash": "e" * 64,
        "modelHash": "f" * 64,
        "modelPolicyHash": "1" * 64,
        "approvalHash": "2" * 64,
        "armHash": "3" * 64,
        "runtimeLeaseId": "lease-1",
        "startedAt": "2026-07-23T01:00:00+00:00",
        "lastHeartbeatAt": "2026-07-23T01:01:00+00:00",
        "lastScanAt": "2026-07-23T01:00:30+00:00",
        "nextScanAt": "2026-07-23T02:00:00+00:00",
    }
    values.update(overrides)
    return RuntimeIdentity(**values)  # type: ignore[arg-type]


class RuntimeIdentityTest(unittest.TestCase):
    def test_identity_is_immutable_and_serializable(self) -> None:
        identity = _identity()

        with self.assertRaises(FrozenInstanceError):
            identity.releaseId = "changed"  # type: ignore[misc]

        payload = identity.to_dict()
        self.assertEqual(payload["releaseId"], "release-1")
        self.assertEqual(payload["moduleRootHashes"]["execution"], "b" * 64)
        self.assertEqual(payload["newEntriesAllowed"], True)
        self.assertEqual(payload["route"], "runtime_identity_verified")

    def test_missing_critical_identity_fails_closed(self) -> None:
        decision = evaluate_runtime_identity(_identity(modelHash=""))

        self.assertFalse(decision.newEntriesAllowed)
        self.assertEqual(decision.route, "runtime_identity_unverified")
        self.assertIn("modelHash", decision.reasonCodes)

    def test_mismatched_expected_binding_fails_closed(self) -> None:
        decision = evaluate_runtime_identity(
            _identity(),
            expected={"releaseHash": "9" * 64, "environment": "okx_demo"},
        )

        self.assertFalse(decision.newEntriesAllowed)
        self.assertEqual(decision.route, "runtime_identity_unverified")
        self.assertIn("releaseHash_mismatch", decision.reasonCodes)

    def test_assertion_raises_stable_blocker(self) -> None:
        with self.assertRaisesRegex(RuntimeIdentityMismatch, "runtime_identity_unverified"):
            assert_runtime_identity(_identity(approvalHash=""))

    def test_timestamp_order_and_environment_are_validated(self) -> None:
        decision = evaluate_runtime_identity(
            _identity(
                environment="paper",
                lastHeartbeatAt="2026-07-23T00:59:00+00:00",
            )
        )

        self.assertFalse(decision.newEntriesAllowed)
        self.assertIn("environment_invalid", decision.reasonCodes)
        self.assertIn("lastHeartbeatAt_before_startedAt", decision.reasonCodes)


if __name__ == "__main__":
    unittest.main()
