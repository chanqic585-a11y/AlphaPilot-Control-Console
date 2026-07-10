from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import alphapilot_control_console.evolution_demo_service as service


class EvolutionDemoServiceTests(unittest.TestCase):
    def test_default_status_is_blocked_without_release_or_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            service, "STORE_PATH", Path(directory) / "demo.sqlite"
        ), patch.object(service, "_contract_paths", return_value=[]), patch.dict(os.environ, {}, clear=True):
            status = service.build_evolution_demo_status()

        self.assertFalse(status["summary"]["ready"])
        self.assertIn("no_eligible_demo_release", status["blockers"])
        self.assertIn("okx_demo_credentials_missing", status["blockers"])
        self.assertFalse(status["safetyBoundary"]["liveExecutionAllowed"])
        self.assertFalse(status["safetyBoundary"]["withdrawAllowed"])


if __name__ == "__main__":
    unittest.main()
