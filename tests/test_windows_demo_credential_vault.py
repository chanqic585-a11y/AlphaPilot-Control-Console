from __future__ import annotations

import json
import unittest

from alphapilot_control_console.windows_demo_credential_vault import (
    CRED_PERSIST_LOCAL_MACHINE,
    DEMO_CREDENTIAL_TARGET,
    DemoCredentialBundle,
    DemoCredentialVaultError,
    WindowsDemoCredentialVault,
)


class MemoryCredentialBackend:
    def __init__(self) -> None:
        self.records: dict[str, bytes] = {}
        self.writes: list[tuple[str, bytes, int]] = []
        self.deletes: list[str] = []

    def write(self, target_name: str, blob: bytes, persistence: int) -> None:
        self.writes.append((target_name, blob, persistence))
        self.records[target_name] = blob

    def read(self, target_name: str) -> bytes | None:
        return self.records.get(target_name)

    def delete(self, target_name: str) -> bool:
        self.deletes.append(target_name)
        return self.records.pop(target_name, None) is not None


class WindowsDemoCredentialVaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MemoryCredentialBackend()
        self.vault = WindowsDemoCredentialVault(backend=self.backend)
        self.bundle = DemoCredentialBundle(
            apiKey="demo-api-key-value",
            secretKey="demo-secret-key-value",
            passphrase="demo-passphrase-value",
        )

    def test_round_trip_uses_fixed_target_and_local_machine_persistence(self) -> None:
        self.vault.store(self.bundle)

        loaded = self.vault.load()

        self.assertEqual(loaded, self.bundle)
        self.assertEqual(len(self.backend.writes), 1)
        target, blob, persistence = self.backend.writes[0]
        self.assertEqual(target, DEMO_CREDENTIAL_TARGET)
        self.assertEqual(persistence, CRED_PERSIST_LOCAL_MACHINE)
        payload = json.loads(blob.decode("utf-8"))
        self.assertEqual(payload["v"], 1)
        self.assertEqual(payload["apiKey"], self.bundle.apiKey)
        self.assertEqual(payload["secretKey"], self.bundle.secretKey)
        self.assertEqual(payload["passphrase"], self.bundle.passphrase)

    def test_metadata_is_redacted_and_reports_only_local_machine_status(self) -> None:
        missing = self.vault.metadata()
        self.vault.store(self.bundle)
        stored = self.vault.metadata()

        self.assertEqual(
            missing,
            {
                "supported": True,
                "stored": False,
                "status": "missing",
                "targetLabel": "AlphaPilot OKX Demo",
                "persistence": "local_machine",
            },
        )
        self.assertTrue(stored["stored"])
        self.assertEqual(stored["status"], "stored")
        metadata_text = repr(stored)
        for secret in (self.bundle.apiKey, self.bundle.secretKey, self.bundle.passphrase):
            self.assertNotIn(secret, metadata_text)

    def test_bundle_repr_never_contains_secret_values(self) -> None:
        rendered = repr(self.bundle)

        self.assertIn("<redacted>", rendered)
        for secret in (self.bundle.apiKey, self.bundle.secretKey, self.bundle.passphrase):
            self.assertNotIn(secret, rendered)

    def test_delete_is_idempotent_and_uses_only_the_fixed_target(self) -> None:
        self.vault.store(self.bundle)

        self.assertTrue(self.vault.delete())
        self.assertFalse(self.vault.delete())
        self.assertEqual(
            self.backend.deletes,
            [DEMO_CREDENTIAL_TARGET, DEMO_CREDENTIAL_TARGET],
        )

    def test_incomplete_bundle_is_rejected_without_backend_write(self) -> None:
        with self.assertRaises(DemoCredentialVaultError) as captured:
            self.vault.store(DemoCredentialBundle("key", "", "pass"))

        self.assertEqual(captured.exception.category, "credential_incomplete")
        self.assertEqual(self.backend.writes, [])

    def test_malformed_or_wrong_version_record_is_rejected_without_secret_echo(self) -> None:
        for blob in (
            b"not-json",
            json.dumps({"v": 2, "apiKey": "key", "secretKey": "secret", "passphrase": "pass"}).encode(),
        ):
            with self.subTest(blob=blob[:8]):
                self.backend.records[DEMO_CREDENTIAL_TARGET] = blob
                with self.assertRaises(DemoCredentialVaultError) as captured:
                    self.vault.load()
                self.assertEqual(captured.exception.category, "credential_record_invalid")
                self.assertNotIn("secret", str(captured.exception).lower())

    def test_non_windows_without_injected_backend_fails_closed(self) -> None:
        vault = WindowsDemoCredentialVault(platform_name="posix")

        self.assertEqual(
            vault.metadata(),
            {
                "supported": False,
                "stored": False,
                "status": "unsupported",
                "targetLabel": "AlphaPilot OKX Demo",
                "persistence": "local_machine",
            },
        )
        with self.assertRaises(DemoCredentialVaultError) as captured:
            vault.load()
        self.assertEqual(captured.exception.category, "vault_unsupported")


if __name__ == "__main__":
    unittest.main()
