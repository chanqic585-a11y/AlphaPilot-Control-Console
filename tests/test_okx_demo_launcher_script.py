from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OkxDemoLauncherScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = (ROOT / "scripts" / "start_okx_demo_console.ps1").read_text(encoding="utf-8")

    def test_replacement_mode_requires_exact_expected_process(self) -> None:
        self.assertIn("[switch]$ReplaceExistingConsole", self.script)
        self.assertIn("[int]$ExpectedConsoleProcessId", self.script)
        self.assertIn("Get-NetTCPConnection", self.script)
        self.assertIn("OwningProcess", self.script)
        self.assertIn("alphapilot_control_console.http_app", self.script)
        self.assertIn("Stop-Process -Id $listenerProcessId", self.script)
        self.assertIn("if ($listenerProcessId -ne $ExpectedConsoleProcessId)", self.script)
        self.assertNotIn("$PID =", self.script)

    def test_credentials_and_confirmation_happen_before_process_stop(self) -> None:
        self.assertIn("ENABLE_OKX_DEMO_AUTOMATION", self.script)
        api_prompt = self.script.index('$apiKey = Read-SecretText')
        secret_prompt = self.script.index('$secretKey = Read-SecretText')
        passphrase_prompt = self.script.index('$passphrase = Read-SecretText')
        confirmation = self.script.index('ENABLE_OKX_DEMO_AUTOMATION')
        process_stop = self.script.index('Stop-Process -Id $listenerProcessId')
        self.assertLess(api_prompt, process_stop)
        self.assertLess(secret_prompt, process_stop)
        self.assertLess(passphrase_prompt, process_stop)
        self.assertLess(confirmation, process_stop)

    def test_raw_credentials_are_not_hardcoded_and_are_cleared(self) -> None:
        self.assertNotIn('apiKey = "', self.script)
        self.assertNotIn('secretKey = "', self.script)
        self.assertNotIn('passphrase = "', self.script)
        for variable in (
            "ALPHAPILOT_OKX_DEMO_API_KEY",
            "ALPHAPILOT_OKX_DEMO_SECRET_KEY",
            "ALPHAPILOT_OKX_DEMO_PASSPHRASE",
        ):
            self.assertIn(f"Remove-Item Env:\\{variable}", self.script)

    def test_replacement_waits_for_port_release(self) -> None:
        self.assertIn("port did not become available", self.script.lower())
        self.assertIn("Start-Sleep -Milliseconds 250", self.script)

    def test_replacement_continues_when_verified_listener_already_exited(self) -> None:
        self.assertIn("if ($null -ne $listener)", self.script)
        self.assertNotIn('throw "No listener exists on the requested AlphaPilot port."', self.script)

    def test_launcher_requires_the_workspace_virtual_environment(self) -> None:
        self.assertIn('.venv\\Scripts\\python.exe', self.script)
        self.assertIn('scripts\\setup_console_runtime.ps1', self.script)
        self.assertIn('import websocket', self.script)
        self.assertNotIn('$python = "python"', self.script)


if __name__ == "__main__":
    unittest.main()
