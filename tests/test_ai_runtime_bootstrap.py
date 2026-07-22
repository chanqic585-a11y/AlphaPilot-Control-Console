from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.ai_orchestration.batch_service import (
    AIBatchOrchestrationService,
)
from alphapilot_control_console.ai_orchestration.bootstrap import build_ai_runtime
from alphapilot_control_console.ai_orchestration.service import AIOrchestrationService


class AIRuntimeBootstrapTests(unittest.TestCase):
    def test_repository_composition_root_builds_both_services_and_closes_ledgers(self) -> None:
        repository_root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as directory:
            runtime = build_ai_runtime(
                repository_root=repository_root,
                data_root=Path(directory),
            )
            self.assertIsInstance(runtime.service, AIOrchestrationService)
            self.assertIsInstance(runtime.batch_service, AIBatchOrchestrationService)
            self.assertTrue(runtime.model_registry_hash.startswith("sha256:"))
            self.assertTrue(runtime.prompt_registry_hash.startswith("sha256:"))
            runtime.close()


if __name__ == "__main__":
    unittest.main()
