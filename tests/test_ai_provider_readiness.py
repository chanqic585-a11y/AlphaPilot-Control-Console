from __future__ import annotations

import json
import unittest
from pathlib import Path

from alphapilot_control_console.ai_orchestration.errors import AIWorkerIsolationError
from alphapilot_control_console.ai_orchestration.provider_readiness import (
    CREDENTIAL_ENVIRONMENT_VARIABLES,
    build_ai_worker_identity,
    build_provider_readiness_report,
    fixed_provider_smoke_input_hash,
)


class AIProviderReadinessTests(unittest.TestCase):
    def test_no_credentials_stops_at_required_without_exposing_values(self) -> None:
        report = build_provider_readiness_report(
            repository_root=Path(__file__).parents[1],
            environ={},
        )

        self.assertEqual(report["status"], "provider_credentials_required")
        self.assertEqual(
            report["requiredEnvironmentVariables"],
            ["OPENAI_API_KEY", "GEMINI_API_KEY"],
        )
        rendered = json.dumps(report, sort_keys=True)
        self.assertNotIn("api-key-value", rendered)
        self.assertNotIn("secret-value", rendered)

    def test_partial_and_complete_credential_states_are_distinct(self) -> None:
        root = Path(__file__).parents[1]
        partial = build_provider_readiness_report(
            repository_root=root,
            environ={"OPENAI_API_KEY": "api-key-value"},
        )
        complete = build_provider_readiness_report(
            repository_root=root,
            environ={
                "OPENAI_API_KEY": "api-key-value",
                "GEMINI_API_KEY": "secret-value",
            },
        )

        self.assertEqual(partial["status"], "provider_credentials_incomplete")
        self.assertEqual(complete["status"], "provider_credentials_ready")
        self.assertNotIn("api-key-value", json.dumps(complete, sort_keys=True))
        self.assertNotIn("secret-value", json.dumps(complete, sort_keys=True))

    def test_worker_identity_rejects_exchange_private_credentials(self) -> None:
        with self.assertRaises(AIWorkerIsolationError):
            build_ai_worker_identity(environ={"OKX_API_KEY": "must-never-enter-worker"})

        with self.assertRaises(AIWorkerIsolationError):
            build_ai_worker_identity(
                environ={"ALPHAPILOT_BYBIT_PRIVATE_CREDENTIAL": "must-never-enter-worker"}
            )

    def test_worker_identity_has_no_execution_authority(self) -> None:
        identity = build_ai_worker_identity(environ={})

        self.assertEqual(identity["workerId"], "alphapilot-ai-worker-v62.4")
        self.assertFalse(identity["executionAuthority"])
        self.assertFalse(identity["exchangePrivateCredentialsPresent"])
        self.assertTrue(identity["identityHash"].startswith("sha256:"))

    def test_smoke_input_hash_is_fixed_after_local_redaction(self) -> None:
        self.assertEqual(
            fixed_provider_smoke_input_hash(),
            "sha256:9868eccb0254a18d5a90bd2b6d5c6138b105395dbaf5133871273a5c2ebc96df",
        )

    def test_only_two_provider_credentials_are_required(self) -> None:
        self.assertEqual(
            CREDENTIAL_ENVIRONMENT_VARIABLES,
            ("OPENAI_API_KEY", "GEMINI_API_KEY"),
        )


if __name__ == "__main__":
    unittest.main()
