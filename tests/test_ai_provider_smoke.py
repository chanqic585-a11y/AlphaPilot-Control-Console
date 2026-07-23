from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock
from pathlib import Path

from alphapilot_control_console.ai_orchestration import provider_smoke as provider_smoke_module
from alphapilot_control_console.ai_orchestration.audit import AIAuditLedger
from alphapilot_control_console.ai_orchestration.errors import ProviderResponseError
from alphapilot_control_console.ai_orchestration.model_registry import AIModelRegistry
from alphapilot_control_console.ai_orchestration.prompt_registry import PromptRegistry
from alphapilot_control_console.ai_orchestration.provider_adapters.mock_adapter import (
    MockProviderAdapter,
)
from alphapilot_control_console.ai_orchestration.provider_smoke import (
    execute_provider_smoke_sequence,
)
from alphapilot_control_console.ai_orchestration.service import AIOrchestrationService


class _FailingProviderAdapter:
    provider = "deepseek"

    def generate(self, identity, request):
        raise ProviderResponseError(
            "forced provider failure containing process-secret-value"
        )


class AIProviderSmokeTests(unittest.TestCase):
    def test_sequence_runs_provider_only_smokes_before_dual_review(self) -> None:
        root = Path(__file__).parents[1]
        registry = AIModelRegistry.from_path(root / "config" / "ai_model_registry.json")
        prompts = PromptRegistry.from_path(root / "config" / "ai_prompt_registry.json")
        output = {
            "evidenceStatus": "synthetic_fixture_only",
            "executionIntent": "none",
            "summary": "Synthetic provider boundary is valid.",
            "sourceArtifactHashes": ["fixture:provider-smoke-v62-4"],
        }
        deepseek = MockProviderAdapter(provider="deepseek", output=output)
        gemini = MockProviderAdapter(provider="gemini", output=output)
        with tempfile.TemporaryDirectory() as directory:
            ledger = AIAuditLedger(Path(directory) / "audit.sqlite")
            service = AIOrchestrationService(
                model_registry=registry,
                prompt_registry=prompts,
                adapters={"deepseek": deepseek, "gemini": gemini},
                audit_ledger=ledger,
            )
            try:
                report = execute_provider_smoke_sequence(service)
            finally:
                ledger.close()

        self.assertEqual(report["status"], "provider_smoke_passed")
        self.assertEqual(
            [item["taskType"] for item in report["checks"]],
            ["provider_smoke_deepseek", "provider_smoke_gemini", "provider_smoke_dual"],
        )
        self.assertEqual(len(deepseek.requests), 2)
        self.assertEqual(len(gemini.requests), 2)
        self.assertNotIn("Synthetic provider boundary is valid", repr(report))
        self.assertTrue(all(item["responseHashes"] for item in report["checks"]))

    def test_sequence_never_grants_execution_authority(self) -> None:
        root = Path(__file__).parents[1]
        output = {
            "evidenceStatus": "synthetic_fixture_only",
            "executionIntent": "none",
            "summary": "Validated.",
            "sourceArtifactHashes": ["fixture:provider-smoke-v62-4"],
        }
        deepseek = MockProviderAdapter(provider="deepseek", output=output)
        gemini = MockProviderAdapter(provider="gemini", output=output)
        with tempfile.TemporaryDirectory() as directory:
            ledger = AIAuditLedger(Path(directory) / "audit.sqlite")
            service = AIOrchestrationService(
                model_registry=AIModelRegistry.from_path(
                    root / "config" / "ai_model_registry.json"
                ),
                prompt_registry=PromptRegistry.from_path(
                    root / "config" / "ai_prompt_registry.json"
                ),
                adapters={"deepseek": deepseek, "gemini": gemini},
                audit_ledger=ledger,
            )
            try:
                report = execute_provider_smoke_sequence(service)
            finally:
                ledger.close()

        self.assertFalse(report["executionAuthorized"])
        self.assertFalse(report["runtimeArmed"])
        self.assertFalse(report["withdrawEnabled"])

    def test_sequence_records_redacted_provider_errors_and_continues(self) -> None:
        root = Path(__file__).parents[1]
        output = {
            "evidenceStatus": "synthetic_fixture_only",
            "executionIntent": "none",
            "summary": "Validated.",
            "sourceArtifactHashes": ["fixture:provider-smoke-v62-4"],
        }
        gemini = MockProviderAdapter(provider="gemini", output=output)
        with tempfile.TemporaryDirectory() as directory:
            ledger = AIAuditLedger(Path(directory) / "audit.sqlite")
            service = AIOrchestrationService(
                model_registry=AIModelRegistry.from_path(
                    root / "config" / "ai_model_registry.json"
                ),
                prompt_registry=PromptRegistry.from_path(
                    root / "config" / "ai_prompt_registry.json"
                ),
                adapters={
                    "deepseek": _FailingProviderAdapter(),
                    "gemini": gemini,
                },
                audit_ledger=ledger,
            )
            try:
                with mock.patch.dict(
                    "os.environ",
                    {"DEEPSEEK_API_KEY": "process-secret-value"},
                    clear=False,
                ):
                    report = execute_provider_smoke_sequence(service)
            finally:
                ledger.close()

        self.assertEqual(report["status"], "provider_smoke_failed")
        self.assertEqual(
            [item["status"] for item in report["checks"]],
            ["provider_error", "accepted", "provider_error"],
        )
        self.assertEqual(len(gemini.requests), 1)
        self.assertNotIn("process-secret-value", str(report))
        self.assertIn("[REDACTED]", str(report))
        self.assertTrue(all(item["executionAuthorized"] is False for item in report["checks"]))

    def test_cli_emits_redacted_json_instead_of_traceback(self) -> None:
        root = Path(__file__).parents[1]
        rendered = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(
                "os.environ",
                {"GEMINI_API_KEY": "process-secret-value"},
                clear=False,
            ):
                with mock.patch.object(
                    provider_smoke_module,
                    "run_provider_smoke",
                    side_effect=RuntimeError(
                        "runtime failure containing process-secret-value"
                    ),
                ):
                    with redirect_stdout(rendered):
                        exit_code = provider_smoke_module.main(
                            [
                                "--repository-root",
                                str(root),
                                "--data-root",
                                directory,
                            ]
                        )

        report = json.loads(rendered.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(report["status"], "provider_smoke_failed")
        self.assertEqual(report["failureStage"], "runtime")
        self.assertNotIn("process-secret-value", rendered.getvalue())
        self.assertIn("[REDACTED]", rendered.getvalue())


if __name__ == "__main__":
    unittest.main()
