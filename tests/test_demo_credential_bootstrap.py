from __future__ import annotations

import unittest

from alphapilot_control_console.demo_credential_bootstrap import (
    bootstrap_demo_credentials,
    demo_prompt_failure_class,
)
from alphapilot_control_console.windows_demo_credential_vault import (
    DemoCredentialBundle,
    DemoCredentialVaultError,
)


class FakeVault:
    def __init__(self, bundle: DemoCredentialBundle | None = None, error: str | None = None) -> None:
        self.bundle = bundle
        self.error = error
        self.load_count = 0
        self.delete_count = 0

    def load(self) -> DemoCredentialBundle | None:
        self.load_count += 1
        if self.error:
            raise DemoCredentialVaultError(self.error)
        return self.bundle

    def delete(self) -> bool:
        self.delete_count += 1
        return True

    def metadata(self) -> dict[str, object]:
        return {
            "supported": True,
            "stored": self.bundle is not None,
            "status": "stored" if self.bundle else "missing",
            "targetLabel": "AlphaPilot OKX Demo",
            "persistence": "local_machine",
        }


class DemoCredentialBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = DemoCredentialBundle("api-value", "secret-value", "pass-value")
        self.events: list[tuple[str, dict[str, object]]] = []

    def audit(self, event: str, payload: dict[str, object]) -> dict[str, object]:
        self.events.append((event, payload))
        return {}

    def test_valid_vault_populates_current_process_gates_without_arming_directly(self) -> None:
        environment: dict[str, str] = {}
        vault = FakeVault(self.bundle)

        result = bootstrap_demo_credentials(
            environment=environment,
            vault=vault,
            validator=lambda bundle: {"ok": bundle == self.bundle, "category": "validated"},
            audit_writer=self.audit,
            process_id=4567,
        )

        self.assertEqual(result["status"], "loaded")
        self.assertFalse(result["promptRequired"])
        self.assertEqual(environment["ALPHAPILOT_OKX_DEMO_API_KEY"], self.bundle.apiKey)
        self.assertEqual(environment["ALPHAPILOT_OKX_DEMO_SECRET_KEY"], self.bundle.secretKey)
        self.assertEqual(environment["ALPHAPILOT_OKX_DEMO_PASSPHRASE"], self.bundle.passphrase)
        for gate in (
            "ALPHAPILOT_OKX_DEMO_ENABLED",
            "ALPHAPILOT_OKX_DEMO_ORDER_ENABLED",
            "ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED",
            "ALPHAPILOT_OKX_DEMO_LAUNCHER_CONFIRMED",
        ):
            self.assertEqual(environment[gate], "1")
        self.assertEqual(environment["ALPHAPILOT_OKX_DEMO_CANCEL_ENABLED"], "0")
        self.assertEqual(self.events[-1][0], "demo_vault_loaded")
        self.assertNotIn("arm", repr(result).lower())

    def test_existing_complete_process_environment_takes_precedence(self) -> None:
        environment = {
            "ALPHAPILOT_OKX_DEMO_API_KEY": "process-api",
            "ALPHAPILOT_OKX_DEMO_SECRET_KEY": "process-secret",
            "ALPHAPILOT_OKX_DEMO_PASSPHRASE": "process-pass",
        }
        vault = FakeVault(self.bundle)

        result = bootstrap_demo_credentials(
            environment=environment,
            vault=vault,
            validator=lambda _bundle: self.fail("vault validator must not run"),
            audit_writer=self.audit,
        )

        self.assertEqual(result["status"], "process_environment")
        self.assertEqual(vault.load_count, 0)
        self.assertEqual(environment["ALPHAPILOT_OKX_DEMO_API_KEY"], "process-api")

    def test_missing_vault_stays_fail_closed_and_requests_one_prompt(self) -> None:
        environment: dict[str, str] = {}
        vault = FakeVault()

        result = bootstrap_demo_credentials(
            environment=environment,
            vault=vault,
            validator=lambda _bundle: self.fail("validator must not run"),
            audit_writer=self.audit,
        )

        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["category"], "credential_missing")
        self.assertTrue(result["promptRequired"])
        self.assertNotIn("ALPHAPILOT_OKX_DEMO_ENABLED", environment)

    def test_rejected_vault_is_preserved_and_never_populates_environment(self) -> None:
        environment: dict[str, str] = {}
        vault = FakeVault(self.bundle)

        result = bootstrap_demo_credentials(
            environment=environment,
            vault=vault,
            validator=lambda _bundle: {"ok": False, "category": "demo_validation_rejected"},
            audit_writer=self.audit,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["category"], "demo_validation_rejected")
        self.assertTrue(result["promptRequired"])
        self.assertEqual(vault.delete_count, 0)
        self.assertNotIn("ALPHAPILOT_OKX_DEMO_API_KEY", environment)

    def test_vault_adapter_error_is_redacted_and_fail_closed(self) -> None:
        result = bootstrap_demo_credentials(
            environment={},
            vault=FakeVault(error="vault_read_failed"),
            validator=lambda _bundle: self.fail("validator must not run"),
            audit_writer=self.audit,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["category"], "vault_read_failed")
        self.assertTrue(result["promptRequired"])

    def test_prompt_requires_desired_disarmed_demo_with_release(self) -> None:
        bootstrap = {"promptRequired": True, "category": "credential_missing"}
        ready_runtime = {
            "environments": {
                "okx_demo": {
                    "desiredEnabled": True,
                    "armedForCurrentProcess": False,
                    "releaseCount": 10,
                }
            }
        }

        self.assertEqual(
            demo_prompt_failure_class(bootstrap, ready_runtime),
            "credential_missing",
        )
        for changed in (
            {"desiredEnabled": False},
            {"armedForCurrentProcess": True},
            {"releaseCount": 0},
        ):
            runtime = {"environments": {"okx_demo": {**ready_runtime["environments"]["okx_demo"], **changed}}}
            self.assertIsNone(demo_prompt_failure_class(bootstrap, runtime))


if __name__ == "__main__":
    unittest.main()
