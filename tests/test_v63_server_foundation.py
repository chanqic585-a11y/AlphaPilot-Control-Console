from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alphapilot_control_console.server_foundation.checkpoint import (
    CheckpointIdentityMismatch,
    FoundationCheckpointStore,
)
from alphapilot_control_console.server_foundation.contracts import (
    FOUNDATION_ROLES,
    FoundationRole,
    RuntimeMode,
)
from alphapilot_control_console.server_foundation.identity import (
    build_runtime_identity,
)
from alphapilot_control_console.server_foundation.lease import (
    FoundationLeaseStore,
)
from alphapilot_control_console.server_foundation.manifest import (
    FoundationManifest,
)
from alphapilot_control_console.server_foundation.reconciliation import (
    StartupReconciliationBlocked,
    StartupState,
    assert_startup_reconciled,
)
from alphapilot_control_console.server_foundation.resource_budget import (
    validate_resource_budget,
)
from alphapilot_control_console.server_foundation.secret_isolation import (
    SecretIsolationViolation,
    sanitized_environment_for_role,
)
from alphapilot_control_console.server_foundation.shadow import (
    NoOrderShadowPolicy,
)
from alphapilot_control_console.server_foundation.sqlite_backup import (
    RestoreGuard,
    create_online_backup,
    restore_online_backup,
)
from alphapilot_control_console.server_foundation.worker import (
    FoundationWorker,
)


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 24, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value


def _manifest_payload(root: Path) -> dict[str, object]:
    return {
        "schemaVersion": "alphapilot_v63_server_manifest_v1",
        "deploymentId": "v63-local-foundation-test",
        "environment": "local_v63",
        "mode": "shadow_no_order",
        "stateRoot": str(root / "state"),
        "repositoryCommit": "a" * 40,
        "repositoryTag": "v13.27.1.63-server-foundation-console",
        "configVersion": "v63-foundation-config-v1",
        "roles": [
            {
                "role": role.value,
                "enabled": True,
                "cpu": {
                    "control": 0.25,
                    "market": 0.75,
                    "demo": 0.50,
                    "research": 1.25,
                    "ai": 0.75,
                    "factor": 0.50,
                }[role.value],
                "memoryMb": {
                    "control": 512,
                    "market": 1024,
                    "demo": 768,
                    "research": 2048,
                    "ai": 1280,
                    "factor": 896,
                }[role.value],
                "port": 8863 if role is FoundationRole.CONTROL else None,
            }
            for role in FOUNDATION_ROLES
        ],
        "hostReserveMemoryMb": 1536,
        "maxConcurrentBatchRoles": 2,
    }


class FoundationContractsTests(unittest.TestCase):
    def test_manifest_requires_exact_six_roles_and_no_order_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "manifest.json"
            manifest_path.write_text(
                json.dumps(_manifest_payload(Path(directory))),
                encoding="utf-8",
            )

            manifest = FoundationManifest.load(manifest_path)

            self.assertEqual(set(manifest.roles), set(FOUNDATION_ROLES))
            self.assertEqual(manifest.mode, RuntimeMode.SHADOW_NO_ORDER)
            self.assertFalse(manifest.orderCapabilityEnabled)
            self.assertEqual(len(manifest.manifestHash), 64)
            self.assertTrue(validate_resource_budget(manifest).passed)

    def test_resource_budget_rejects_oversubscription(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = _manifest_payload(Path(directory))
            payload["roles"][0]["cpu"] = 3.5  # type: ignore[index]
            manifest_path = Path(directory) / "manifest.json"
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "resource_budget_exceeded"):
                FoundationManifest.load(manifest_path)


class FoundationLeaseTests(unittest.TestCase):
    def test_scope_is_environment_plus_role_and_fencing_is_monotonic(self) -> None:
        clock = MutableClock()
        with tempfile.TemporaryDirectory() as directory:
            store = FoundationLeaseStore(
                Path(directory) / "leases.sqlite",
                now_factory=clock,
            )
            try:
                control = store.acquire(
                    environment="local_v63",
                    role=FoundationRole.CONTROL,
                    owner_id="control-one",
                    ttl_seconds=30,
                )
                market = store.acquire(
                    environment="local_v63",
                    role=FoundationRole.MARKET,
                    owner_id="market-one",
                    ttl_seconds=30,
                )
                self.assertEqual(control.fencingToken, 1)
                self.assertEqual(market.fencingToken, 1)

                with self.assertRaises(PermissionError):
                    store.acquire(
                        environment="local_v63",
                        role=FoundationRole.CONTROL,
                        owner_id="control-two",
                        ttl_seconds=30,
                    )

                clock.value += timedelta(seconds=31)
                replacement = store.acquire(
                    environment="local_v63",
                    role=FoundationRole.CONTROL,
                    owner_id="control-two",
                    ttl_seconds=30,
                )
                self.assertEqual(replacement.fencingToken, 2)
                with self.assertRaises(PermissionError):
                    store.assert_authority(control)
                store.assert_authority(replacement)
                self.assertNotIn(replacement.token, json.dumps(store.projection()))
            finally:
                store.close()


class FoundationSafetyTests(unittest.TestCase):
    def test_startup_reconciliation_fails_closed(self) -> None:
        safe = StartupState(
            demoArmed=False,
            liveArmed=False,
            openOrderCount=0,
            unknownOrderCount=0,
            openPositionCount=0,
            withdrawEnabled=False,
        )
        self.assertTrue(assert_startup_reconciled(safe).passed)

        with self.assertRaisesRegex(
            StartupReconciliationBlocked,
            "openOrderCount_nonzero",
        ):
            assert_startup_reconciled(
                StartupState(
                    demoArmed=False,
                    liveArmed=False,
                    openOrderCount=1,
                    unknownOrderCount=0,
                    openPositionCount=0,
                    withdrawEnabled=False,
                )
            )

    def test_only_ai_role_may_receive_provider_keys(self) -> None:
        source = {
            "PATH": os.environ.get("PATH", ""),
            "DEEPSEEK_API_KEY": "deepseek-secret",
            "GEMINI_API_KEY": "gemini-secret",
            "OKX_API_KEY": "exchange-secret",
        }
        ai_environment = sanitized_environment_for_role(
            FoundationRole.AI,
            source,
        )
        self.assertIn("DEEPSEEK_API_KEY", ai_environment)
        self.assertIn("GEMINI_API_KEY", ai_environment)
        self.assertNotIn("OKX_API_KEY", ai_environment)

        with self.assertRaises(SecretIsolationViolation):
            sanitized_environment_for_role(
                FoundationRole.DEMO,
                {"OKX_API_KEY": "exchange-secret"},
                reject_disallowed=True,
            )

    def test_shadow_policy_never_authorizes_orders_or_arm(self) -> None:
        policy = NoOrderShadowPolicy()
        self.assertFalse(policy.orderAllowed)
        self.assertFalse(policy.demoArmAllowed)
        self.assertFalse(policy.liveArmAllowed)
        self.assertFalse(policy.withdrawAllowed)
        with self.assertRaisesRegex(PermissionError, "shadow_no_order"):
            policy.assert_order_allowed()


class FoundationPersistenceTests(unittest.TestCase):
    def test_online_backup_and_guarded_restore_are_integrity_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "source.sqlite"
            backup_path = root / "backups" / "source.sqlite"
            restore_path = root / "restored.sqlite"
            connection = sqlite3.connect(source_path)
            try:
                connection.execute("CREATE TABLE Example(id INTEGER PRIMARY KEY)")
                connection.execute("INSERT INTO Example DEFAULT VALUES")
                connection.commit()
            finally:
                connection.close()

            receipt = create_online_backup(source_path, backup_path)
            self.assertTrue(receipt["integrityPassed"])
            self.assertEqual(receipt["tableCounts"]["Example"], 1)

            restore_receipt = restore_online_backup(
                backup_path,
                restore_path,
                guard=RestoreGuard(
                    allRolesStopped=True,
                    demoArmed=False,
                    liveArmed=False,
                    activeLeaseCount=0,
                ),
            )
            self.assertTrue(restore_receipt["integrityPassed"])
            restored = sqlite3.connect(restore_path)
            try:
                self.assertEqual(
                    restored.execute("SELECT COUNT(*) FROM Example").fetchone()[0],
                    1,
                )
            finally:
                restored.close()

            with self.assertRaises(PermissionError):
                restore_online_backup(
                    backup_path,
                    root / "blocked.sqlite",
                    guard=RestoreGuard(
                        allRolesStopped=False,
                        demoArmed=False,
                        liveArmed=False,
                        activeLeaseCount=1,
                    ),
                )

    def test_checkpoint_resume_rejects_identity_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = FoundationCheckpointStore(Path(directory))
            checkpoint = store.write(
                role=FoundationRole.RESEARCH,
                manifest_hash="a" * 64,
                config_hash="b" * 64,
                fencing_token=3,
                progress={"candidateIndex": 4},
            )
            loaded = store.load(
                role=FoundationRole.RESEARCH,
                expected_manifest_hash="a" * 64,
                expected_config_hash="b" * 64,
                expected_fencing_token=3,
            )
            self.assertEqual(loaded["checkpointHash"], checkpoint["checkpointHash"])

            with self.assertRaises(CheckpointIdentityMismatch):
                store.load(
                    role=FoundationRole.RESEARCH,
                    expected_manifest_hash="c" * 64,
                    expected_config_hash="b" * 64,
                    expected_fencing_token=3,
                )

    def test_checkpoint_resume_accepts_prior_fencing_token_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = FoundationCheckpointStore(Path(directory))
            store.write(
                role=FoundationRole.RESEARCH,
                manifest_hash="a" * 64,
                config_hash="b" * 64,
                fencing_token=3,
                progress={"candidateIndex": 4},
            )

            resumed = store.load_for_resume(
                role=FoundationRole.RESEARCH,
                expected_manifest_hash="a" * 64,
                expected_config_hash="b" * 64,
                current_fencing_token=4,
            )

            self.assertEqual(resumed["progress"]["candidateIndex"], 4)
            self.assertEqual(resumed["fencingToken"], 3)
            with self.assertRaises(CheckpointIdentityMismatch):
                store.load_for_resume(
                    role=FoundationRole.RESEARCH,
                    expected_manifest_hash="a" * 64,
                    expected_config_hash="b" * 64,
                    current_fencing_token=3,
                )


class FoundationWorkerTests(unittest.TestCase):
    def test_worker_run_once_writes_identity_health_and_checkpoint(self) -> None:
        clock = MutableClock()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(_manifest_payload(root)),
                encoding="utf-8",
            )
            manifest = FoundationManifest.load(manifest_path)
            lease_store = FoundationLeaseStore(
                root / "leases.sqlite",
                now_factory=clock,
            )
            try:
                worker = FoundationWorker(
                    manifest=manifest,
                    role=FoundationRole.FACTOR,
                    lease_store=lease_store,
                    now_factory=clock,
                    process_id=1234,
                )
                result = worker.run_once(
                    StartupState(
                        demoArmed=False,
                        liveArmed=False,
                        openOrderCount=0,
                        unknownOrderCount=0,
                        openPositionCount=0,
                        withdrawEnabled=False,
                    )
                )
                identity = build_runtime_identity(
                    manifest=manifest,
                    role=FoundationRole.FACTOR,
                    process_id=1234,
                    started_at=result["startedAt"],
                    lease_id=result["leaseId"],
                    fencing_token=result["fencingToken"],
                )
                self.assertEqual(result["identityHash"], identity.identityHash)
                self.assertEqual(result["status"], "healthy_shadow_no_order")
                self.assertTrue(Path(result["healthPath"]).is_file())
                self.assertTrue(Path(result["checkpointPath"]).is_file())
                self.assertFalse(result["orderCapabilityEnabled"])
            finally:
                worker.close()
                lease_store.close()

    def test_worker_resumes_cycle_count_after_new_fenced_lease(self) -> None:
        clock = MutableClock()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(_manifest_payload(root)),
                encoding="utf-8",
            )
            manifest = FoundationManifest.load(manifest_path)
            lease_store = FoundationLeaseStore(
                root / "leases.sqlite",
                now_factory=clock,
            )
            startup_state = StartupState(
                demoArmed=False,
                liveArmed=False,
                openOrderCount=0,
                unknownOrderCount=0,
                openPositionCount=0,
                withdrawEnabled=False,
            )
            first = FoundationWorker(
                manifest=manifest,
                role=FoundationRole.RESEARCH,
                lease_store=lease_store,
                now_factory=clock,
                process_id=1234,
            )
            try:
                first_health = first.run_once(startup_state)
                self.assertEqual(first_health["cycleCount"], 1)
                self.assertEqual(first_health["fencingToken"], 1)
            finally:
                first.close()

            second = FoundationWorker(
                manifest=manifest,
                role=FoundationRole.RESEARCH,
                lease_store=lease_store,
                now_factory=clock,
                process_id=5678,
            )
            try:
                second_health = second.run_once(startup_state)
                self.assertEqual(second_health["cycleCount"], 2)
                self.assertEqual(second_health["fencingToken"], 2)
                self.assertTrue(second_health["resumedFromCheckpoint"])
                self.assertEqual(
                    second_health["resumedCheckpointFencingToken"],
                    1,
                )
            finally:
                second.close()
                lease_store.close()


if __name__ == "__main__":
    unittest.main()
