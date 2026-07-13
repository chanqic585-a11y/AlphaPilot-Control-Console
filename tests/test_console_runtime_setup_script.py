from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ConsoleRuntimeSetupScriptTests(unittest.TestCase):
    def test_setup_script_creates_venv_and_installs_pinned_requirements(self) -> None:
        script = (ROOT / "scripts" / "setup_console_runtime.ps1").read_text(encoding="utf-8")

        self.assertIn(".venv", script)
        self.assertIn("-m venv", script)
        self.assertIn("-m pip install --requirement", script)
        self.assertIn("import websocket", script)
        self.assertIn("websocket.__version__", script)

    def test_requirements_pin_the_websocket_client_version(self) -> None:
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

        self.assertEqual(requirements, "websocket-client==1.8.0\n")
