from __future__ import annotations

import unittest

from alphapilot_control_console.demo_credential_enrollment import (
    enroll_demo_credentials,
    validate_demo_credentials,
)
from alphapilot_control_console.exchange_connectors.okx_demo_client import OkxDemoError
from alphapilot_control_console.windows_demo_credential_vault import DemoCredentialBundle


class FakeDemoClient:
    def __init__(self, response: dict[str, object] | None = None, error: Exception | None = None) -> None:
        self.response = response or {"code": "0", "data": [{}]}
        self.error = error
        self.calls: list[str] = []

    def get_account_config(self) -> dict[str, object]:
        self.calls.append("get_account_config")
        if self.error is not None:
            raise self.error
        return self.response


class FakeVault:
    def __init__(self) -> None:
        self.stored: list[DemoCredentialBundle] = []

    def store(self, bundle: DemoCredentialBundle) -> None:
        self.stored.append(bundle)

    def metadata(self) -> dict[str, object]:
        return {
            "supported": True,
            "stored": bool(self.stored),
            "status": "stored" if self.stored else "missing",
            "targetLabel": "AlphaPilot OKX Demo",
            "persistence": "local_machine",
        }


class DemoCredentialEnrollmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = DemoCredentialBundle("test-api-value", "test-secret-value", "test-pass-value")

    def test_validation_uses_only_demo_account_config(self) -> None:
        client = FakeDemoClient()
        captured_credentials = []

        result = validate_demo_credentials(
            self.bundle,
            client_factory=lambda credentials: captured_credentials.append(credentials) or client,
        )

        self.assertEqual(result, {"ok": True, "category": "validated"})
        self.assertEqual(client.calls, ["get_account_config"])
        self.assertEqual(captured_credentials[0].apiKey, self.bundle.apiKey)

    def test_validation_rejects_exchange_error_without_echoing_payload(self) -> None:
        client = FakeDemoClient(response={"code": "50110", "msg": "IP whitelist rejected"})

        result = validate_demo_credentials(self.bundle, client_factory=lambda _credentials: client)

        self.assertEqual(result, {"ok": False, "category": "demo_validation_rejected"})
        rendered = repr(result)
        self.assertNotIn("50110", rendered)
        self.assertNotIn("whitelist", rendered.lower())

    def test_validation_classifies_network_failure_without_secret_values(self) -> None:
        client = FakeDemoClient(error=OkxDemoError("network detail test-secret-value"))

        result = validate_demo_credentials(self.bundle, client_factory=lambda _credentials: client)

        self.assertEqual(result, {"ok": False, "category": "demo_validation_unavailable"})
        self.assertNotIn(self.bundle.secretKey, repr(result))

    def test_enrollment_validates_before_storing_and_writes_redacted_audit(self) -> None:
        vault = FakeVault()
        events: list[tuple[str, dict[str, object]]] = []
        order: list[str] = []

        result = enroll_demo_credentials(
            environment={
                "ALPHAPILOT_OKX_DEMO_API_KEY": self.bundle.apiKey,
                "ALPHAPILOT_OKX_DEMO_SECRET_KEY": self.bundle.secretKey,
                "ALPHAPILOT_OKX_DEMO_PASSPHRASE": self.bundle.passphrase,
            },
            vault=vault,
            validator=lambda _bundle: order.append("validate") or {"ok": True, "category": "validated"},
            store_hook=lambda _bundle: order.append("store"),
            audit_writer=lambda event, payload: events.append((event, payload)) or {},
            process_id=1234,
        )

        self.assertEqual(order, ["validate", "store"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "stored")
        self.assertEqual(events[0][0], "demo_vault_validation_succeeded")
        self.assertEqual(events[-1][0], "demo_vault_enrollment_succeeded")
        rendered = repr((result, events))
        for secret in (self.bundle.apiKey, self.bundle.secretKey, self.bundle.passphrase):
            self.assertNotIn(secret, rendered)

    def test_enrollment_failure_never_writes_vault(self) -> None:
        vault = FakeVault()
        events: list[tuple[str, dict[str, object]]] = []

        result = enroll_demo_credentials(
            environment={
                "ALPHAPILOT_OKX_DEMO_API_KEY": self.bundle.apiKey,
                "ALPHAPILOT_OKX_DEMO_SECRET_KEY": self.bundle.secretKey,
                "ALPHAPILOT_OKX_DEMO_PASSPHRASE": self.bundle.passphrase,
            },
            vault=vault,
            validator=lambda _bundle: {"ok": False, "category": "demo_validation_rejected"},
            audit_writer=lambda event, payload: events.append((event, payload)) or {},
            process_id=1234,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["category"], "demo_validation_rejected")
        self.assertEqual(vault.stored, [])
        self.assertEqual(events[-1][0], "demo_vault_validation_failed")

    def test_incomplete_environment_is_rejected_without_secret_details(self) -> None:
        vault = FakeVault()

        result = enroll_demo_credentials(
            environment={"ALPHAPILOT_OKX_DEMO_API_KEY": "only-one-value"},
            vault=vault,
            validator=lambda _bundle: self.fail("validator must not run"),
            audit_writer=lambda _event, _payload: {},
        )

        self.assertEqual(
            result,
            {"ok": False, "status": "rejected", "category": "credential_incomplete"},
        )
        self.assertEqual(vault.stored, [])


if __name__ == "__main__":
    unittest.main()
