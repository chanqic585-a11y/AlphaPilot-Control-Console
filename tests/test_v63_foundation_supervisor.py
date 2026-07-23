from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.server_foundation.contracts import (
    FOUNDATION_ROLES,
    FoundationRole,
)
from alphapilot_control_console.server_foundation.lease import (
    FoundationLeaseStore,
)
from alphapilot_control_console.server_foundation.manifest import (
    FoundationManifest,
)
from alphapilot_control_console.server_foundation.reconciliation import (
    StartupState,
)
from alphapilot_control_console.server_foundation.supervisor import (
    FoundationSupervisor,
)


def _manifest_payload(root: Path) -> dict[str, object]:
    budgets = {
        "control": (0.25, 512),
        "market": (0.75, 1024),
        "demo": (0.50, 768),
        "research": (1.25, 2048),
        "ai": (0.75, 1280),
        "factor": (0.50, 896),
    }
    return {
        "schemaVersion": "alphapilot_v63_server_manifest_v1",
        "deploymentId": "v63-supervisor-test",
        "environment": "local_v63_test",
        "mode": "shadow_no_order",
        "stateRoot": str(root / "state"),
        "repositoryCommit": "a" * 40,
        "repositoryTag": "v13.27.1.63-server-foundation-console",
        "configVersion": "v63-foundation-config-v1",
        "roles": [
            {
                "role": role.value,
                "enabled": True,
                "cpu": budgets[role.value][0],
                "memoryMb": budgets[role.value][1],
                "port": 8863 if role is FoundationRole.CONTROL else None,
            }
            for role in FOUNDATION_ROLES
        ],
        "hostReserveMemoryMb": 1536,
        "maxConcurrentBatchRoles": 2,
    }


class FoundationSupervisorTests(unittest.TestCase):
    def test_roles_start_health_and_stop_without_order_capability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(_manifest_payload(root)),
                encoding="utf-8",
            )
            manifest = FoundationManifest.load(manifest_path)
            supervisor = FoundationSupervisor(
                manifest_path=manifest_path,
                python_executable=Path(sys.executable),
                repository_root=Path(__file__).resolve().parents[1],
                source_environment=os.environ,
            )
            safe_state = StartupState(
                demoArmed=False,
                liveArmed=False,
                openOrderCount=0,
                unknownOrderCount=0,
                openPositionCount=0,
                withdrawEnabled=False,
            )

            start = supervisor.start(
                roles=(FoundationRole.CONTROL, FoundationRole.MARKET),
                startup_state=safe_state,
                startup_timeout_seconds=10,
                heartbeat_seconds=0.2,
            )
            self.assertEqual(start["status"], "started_shadow_no_order")
            self.assertEqual(set(start["startedRoles"]), {"control", "market"})

            health = supervisor.health(
                roles=(FoundationRole.CONTROL, FoundationRole.MARKET),
                maximum_age_seconds=3,
            )
            self.assertTrue(health["healthy"])
            self.assertEqual(health["healthyRoleCount"], 2)
            self.assertTrue(
                all(
                    role["orderCapabilityEnabled"] is False
                    for role in health["roles"]
                )
            )

            stop = supervisor.stop(
                roles=(FoundationRole.CONTROL, FoundationRole.MARKET),
                timeout_seconds=10,
            )
            self.assertEqual(stop["status"], "stopped")
            self.assertEqual(set(stop["stoppedRoles"]), {"control", "market"})
            lease_store = FoundationLeaseStore(
                manifest.stateRoot / "foundation_leases.sqlite"
            )
            try:
                self.assertEqual(lease_store.active_count(manifest.environment), 0)
            finally:
                lease_store.close()


if __name__ == "__main__":
    unittest.main()
