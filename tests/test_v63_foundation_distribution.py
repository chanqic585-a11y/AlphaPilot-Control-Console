from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.server_foundation.contracts import FOUNDATION_ROLES
from alphapilot_control_console.server_foundation.manifest import FoundationManifest
from alphapilot_control_console.server_foundation.resource_budget import (
    validate_resource_budget,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_TEMPLATE = (
    REPOSITORY_ROOT / "config" / "v63_server_foundation_manifest.template.json"
)
DIRECTORY_MAPPING = (
    REPOSITORY_ROOT / "config" / "v63_server_directory_mapping.json"
)
MANAGER_SCRIPT = REPOSITORY_ROOT / "scripts" / "manage_v63_foundation.ps1"


class FoundationDistributionTests(unittest.TestCase):
    def test_checked_in_manifests_encode_the_frozen_no_order_budget(self) -> None:
        payload = json.loads(MANIFEST_TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["schemaVersion"],
            "alphapilot_v63_server_manifest_v1",
        )
        self.assertEqual(payload["mode"], "shadow_no_order")
        self.assertEqual(
            {entry["role"] for entry in payload["roles"]},
            {role.value for role in FOUNDATION_ROLES},
        )
        self.assertEqual(sum(entry["cpu"] for entry in payload["roles"]), 4.0)
        self.assertEqual(
            sum(entry["memoryMb"] for entry in payload["roles"])
            + payload["hostReserveMemoryMb"],
            8064,
        )

        mapping = json.loads(DIRECTORY_MAPPING.read_text(encoding="utf-8"))
        self.assertEqual(
            mapping["schemaVersion"],
            "alphapilot_v63_server_directory_mapping_v1",
        )
        self.assertEqual(mapping["localWorkspaceRoot"], r"D:\Codex-Workspace")
        self.assertEqual(mapping["localRuntimeRoot"], r"D:\Codex-Workspace\runtime\v63")
        self.assertEqual(mapping["serverRuntimeRoot"], "/var/lib/alphapilot/v63")
        self.assertEqual(
            set(mapping["runtimeDirectories"]),
            {
                "config",
                "leases",
                "roles",
                "checkpoints",
                "backups",
                "logs",
                "receipts",
                "evidence",
            },
        )

    def test_powershell_validate_materializes_exact_runtime_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_root = Path(directory) / "runtime"
            commit = "b" * 40
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(MANAGER_SCRIPT),
                    "-Action",
                    "Validate",
                    "-PythonExecutable",
                    sys.executable,
                    "-RepositoryRoot",
                    str(REPOSITORY_ROOT),
                    "-StateRoot",
                    str(state_root),
                    "-RepositoryCommit",
                    commit,
                ],
                cwd=REPOSITORY_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertTrue(output["passed"])
            self.assertEqual(output["mode"], "shadow_no_order")
            self.assertEqual(output["roleCount"], 6)
            self.assertFalse(output["orderCapabilityEnabled"])
            self.assertEqual(output["resourceBudget"]["totalCpu"], 4.0)
            self.assertEqual(output["resourceBudget"]["totalMemoryMb"], 8064)

            materialized = FoundationManifest.load(
                state_root / "config" / "v63_server_foundation_manifest.json"
            )
            self.assertEqual(materialized.repositoryCommit, commit)
            self.assertEqual(
                materialized.repositoryTag,
                "v13.27.1.63-server-foundation-console",
            )
            self.assertEqual(materialized.stateRoot, state_root.resolve())
            self.assertTrue(validate_resource_budget(materialized).passed)


if __name__ == "__main__":
    unittest.main()
