from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from alphapilot_control_console.server_foundation.contracts import FOUNDATION_ROLES
from alphapilot_control_console.server_foundation.evidence import (
    build_foundation_evidence,
    write_foundation_evidence,
)


MANIFEST_HASH = "a" * 64
CONFIG_HASH = "b" * 64
DATABASE_HASH = "c" * 64


def _manifest() -> dict[str, object]:
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
        "deploymentId": "v63-evidence-test",
        "environment": "local_v63_shadow",
        "mode": "shadow_no_order",
        "repositoryCommit": "d" * 40,
        "repositoryTag": "v13.27.1.63-server-foundation-console",
        "configVersion": "v63-foundation-config-v1",
        "manifestHash": MANIFEST_HASH,
        "configHash": CONFIG_HASH,
        "hostReserveMemoryMb": 1536,
        "maxConcurrentBatchRoles": 2,
        "orderCapabilityEnabled": False,
        "roles": [
            {
                "role": role.value,
                "enabled": True,
                "cpu": budgets[role.value][0],
                "memoryMb": budgets[role.value][1],
                "port": 8863 + index,
            }
            for index, role in enumerate(FOUNDATION_ROLES)
        ],
    }


def _health(*, resumed: bool) -> dict[str, object]:
    roles = []
    for index, role in enumerate(FOUNDATION_ROLES):
        initial_cycle = 40 + index
        fencing_token = 4 if resumed else 3
        roles.append(
            {
                "role": role.value,
                "healthy": True,
                "status": "healthy_shadow_no_order",
                "manifestHash": MANIFEST_HASH,
                "configHash": CONFIG_HASH,
                "fencingToken": fencing_token,
                "cycleCount": initial_cycle + (50 if resumed else 0),
                "resumedFromCheckpoint": resumed,
                "resumedCheckpointFencingToken": 3 if resumed else None,
                "checkpointResumeDisposition": (
                    "resumed_same_identity"
                    if resumed
                    else "started_fresh_new_identity"
                ),
                "reconciliation": {
                    "passed": True,
                    "reasonCodes": [],
                },
                "orderCapabilityEnabled": False,
                "demoArmAllowed": False,
                "liveArmAllowed": False,
                "withdrawAllowed": False,
            }
        )
    return {
        "schemaVersion": "alphapilot_v63_supervisor_health_v1",
        "healthy": True,
        "healthyRoleCount": 6,
        "expectedRoleCount": 6,
        "manifestHash": MANIFEST_HASH,
        "configHash": CONFIG_HASH,
        "orderCapabilityEnabled": False,
        "roles": roles,
    }


def _backup_receipt() -> dict[str, object]:
    return {
        "schemaVersion": "alphapilot_v63_sqlite_backup_receipt_v1",
        "operation": "online_backup",
        "sha256": DATABASE_HASH,
        "integrityPassed": True,
        "integrityRows": ["ok"],
        "userVersion": 0,
        "journalMode": "wal",
        "tableCounts": {
            "Events": 2994,
            "RuntimeLeases": 0,
            "Sequences": 6,
        },
    }


def _restore_receipt() -> dict[str, object]:
    return {
        "schemaVersion": "alphapilot_v63_sqlite_restore_receipt_v1",
        "operation": "guarded_restore",
        "sha256": DATABASE_HASH,
        "integrityPassed": True,
        "integrityRows": ["ok"],
        "userVersion": 0,
        "journalMode": "wal",
        "tableCounts": {
            "Events": 2994,
            "RuntimeLeases": 0,
            "Sequences": 6,
        },
        "guard": {
            "allRolesStopped": True,
            "demoArmed": False,
            "liveArmed": False,
            "activeLeaseCount": 0,
        },
    }


def _track_b() -> dict[str, object]:
    return {
        "schemaVersion": "alphapilot_v63_track_b_preregistration_v1",
        "campaignId": "v63-fresh-mechanism-campaign-20260724",
        "status": "preregistered_dry_preparation_only",
        "formalRunCount": 0,
        "lockedOosReadCount": 0,
        "resultReadCount": 0,
        "safety": {
            "armAllowed": False,
            "liveAllowed": False,
            "orderCapabilityEnabled": False,
            "releaseApprovalAllowed": False,
            "withdrawAllowed": False,
        },
    }


def _track_c() -> dict[str, object]:
    return {
        "schemaVersion": "alphapilot_v63_track_c_status_matrix_v1",
        "overallStatus": "completed_with_blockers",
        "counts": {
            "passed": 3,
            "blocked": 2,
            "not_run": 1,
        },
        "checks": {
            "deployment_scripts": {"status": "passed"},
            "factor_bench": {"status": "passed"},
            "security_findings": {"status": "passed"},
            "observer": {"status": "blocked"},
            "qlib": {"status": "blocked"},
            "coverage": {"status": "not_run"},
        },
        "orderCapabilityEnabled": False,
        "demoArmAllowed": False,
        "liveArmAllowed": False,
        "withdrawAllowed": False,
    }


def _parallel_manifest() -> dict[str, object]:
    return {
        "schemaVersion": "alphapilot_v63_parallel_track_manifest_v1",
        "campaignId": "v63-fresh-mechanism-campaign-20260724",
        "artifactCount": 3,
        "manifestHash": "v63_parallel_track_manifest_" + "e" * 64,
        "safety": {
            "demoArmAllowed": False,
            "liveArmAllowed": False,
            "orderCapabilityEnabled": False,
            "withdrawAllowed": False,
        },
    }


def _build() -> dict[str, object]:
    return build_foundation_evidence(
        manifest=_manifest(),
        initial_health=_health(resumed=False),
        resumed_health=_health(resumed=True),
        backup_receipt=_backup_receipt(),
        restore_receipt=_restore_receipt(),
        track_b=_track_b(),
        track_c=_track_c(),
        parallel_track_manifest=_parallel_manifest(),
        generated_at="2026-07-24T01:00:00+00:00",
    )


class FoundationEvidenceTests(unittest.TestCase):
    def test_builds_and_atomically_writes_truthful_foundation_evidence(self) -> None:
        evidence = _build()

        self.assertEqual(
            evidence["status"],
            "foundation_passed_with_research_blockers",
        )
        self.assertEqual(evidence["runtime"]["healthyRoleCount"], 6)
        self.assertTrue(evidence["checkpointResume"]["sameIdentityResumeVerified"])
        self.assertTrue(evidence["sqlite"]["backupRestoreVerified"])
        self.assertEqual(evidence["trackB"]["formalRunCount"], 0)
        self.assertEqual(
            evidence["trackC"]["overallStatus"],
            "completed_with_blockers",
        )
        self.assertFalse(evidence["safety"]["ordersAllowed"])
        self.assertFalse(evidence["safety"]["demoArmAllowed"])
        self.assertFalse(evidence["safety"]["liveArmAllowed"])
        self.assertFalse(evidence["safety"]["withdrawAllowed"])

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence"
            receipt = write_foundation_evidence(output, evidence)

            self.assertEqual(receipt["artifactCount"], 2)
            evidence_path = output / "v63_foundation_evidence.json"
            closeout_path = output / "v63_foundation_closeout.md"
            manifest_path = output / "artifact_manifest.json"
            self.assertTrue(evidence_path.is_file())
            self.assertTrue(closeout_path.is_file())
            self.assertTrue(manifest_path.is_file())
            self.assertFalse(any(output.glob("*.tmp")))

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifacts = {row["path"]: row for row in manifest["artifacts"]}
            self.assertEqual(
                artifacts[evidence_path.name]["sha256"],
                hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                artifacts[closeout_path.name]["sha256"],
                hashlib.sha256(closeout_path.read_bytes()).hexdigest(),
            )

    def test_rejects_unsafe_or_incomplete_six_role_health(self) -> None:
        unsafe_health = _health(resumed=False)
        unsafe_health["roles"][0]["orderCapabilityEnabled"] = True

        with self.assertRaisesRegex(
            ValueError,
            "foundation_health_unsafe:control:orderCapabilityEnabled",
        ):
            build_foundation_evidence(
                manifest=_manifest(),
                initial_health=unsafe_health,
                resumed_health=_health(resumed=True),
                backup_receipt=_backup_receipt(),
                restore_receipt=_restore_receipt(),
                track_b=_track_b(),
                track_c=_track_c(),
                parallel_track_manifest=_parallel_manifest(),
            )

        missing_role_health = _health(resumed=False)
        missing_role_health["roles"] = missing_role_health["roles"][:-1]
        with self.assertRaisesRegex(ValueError, "foundation_health_roles_incomplete"):
            build_foundation_evidence(
                manifest=_manifest(),
                initial_health=missing_role_health,
                resumed_health=_health(resumed=True),
                backup_receipt=_backup_receipt(),
                restore_receipt=_restore_receipt(),
                track_b=_track_b(),
                track_c=_track_c(),
                parallel_track_manifest=_parallel_manifest(),
            )

    def test_rejects_false_resume_or_backup_restore_mismatch(self) -> None:
        false_resume = _health(resumed=True)
        false_resume["roles"][0]["resumedFromCheckpoint"] = False
        with self.assertRaisesRegex(
            ValueError,
            "foundation_resume_not_verified:control",
        ):
            build_foundation_evidence(
                manifest=_manifest(),
                initial_health=_health(resumed=False),
                resumed_health=false_resume,
                backup_receipt=_backup_receipt(),
                restore_receipt=_restore_receipt(),
                track_b=_track_b(),
                track_c=_track_c(),
                parallel_track_manifest=_parallel_manifest(),
            )

        mismatched_restore = deepcopy(_restore_receipt())
        mismatched_restore["sha256"] = "f" * 64
        with self.assertRaisesRegex(
            ValueError,
            "sqlite_backup_restore_hash_mismatch",
        ):
            build_foundation_evidence(
                manifest=_manifest(),
                initial_health=_health(resumed=False),
                resumed_health=_health(resumed=True),
                backup_receipt=_backup_receipt(),
                restore_receipt=mismatched_restore,
                track_b=_track_b(),
                track_c=_track_c(),
                parallel_track_manifest=_parallel_manifest(),
            )


if __name__ == "__main__":
    unittest.main()
