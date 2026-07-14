from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LocalConsoleLauncherScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.wrapper = (ROOT / "Start-Control-Console.cmd").read_text(encoding="utf-8")
        script_path = ROOT / "scripts" / "start_local_console.ps1"
        cls.script = script_path.read_text(encoding="utf-8") if script_path.exists() else ""

    def test_cmd_wrapper_delegates_to_testable_powershell_launcher(self) -> None:
        self.assertIn("scripts\\start_local_console.ps1", self.wrapper)
        self.assertIn("%*", self.wrapper)
        self.assertNotIn("Stop-Process", self.wrapper)
        self.assertNotIn("Invoke-RestMethod", self.wrapper)

    def test_healthy_existing_console_is_reused_without_restart(self) -> None:
        self.assertIn("function Get-ConsoleHealth", self.script)
        self.assertIn("Control Console is already running", self.script)
        health_probe = self.script.index("$existingHealth = Get-ConsoleHealth")
        process_stop = self.script.index("Stop-Process -Id $listenerProcessId")
        process_start = self.script.index("Start-Process -FilePath $PythonPath")
        self.assertLess(health_probe, process_stop)
        self.assertLess(health_probe, process_start)

    def test_unhealthy_listener_must_be_verified_before_it_is_stopped(self) -> None:
        self.assertIn("Get-NetTCPConnection", self.script)
        self.assertIn("OwningProcess", self.script)
        self.assertIn("alphapilot_control_console.http_app", self.script)
        self.assertIn("another process owns port", self.script.lower())

    def test_first_start_polls_health_until_a_bounded_deadline(self) -> None:
        self.assertIn("$StartupTimeoutSeconds", self.script)
        self.assertIn("while ([DateTime]::UtcNow -lt $deadline)", self.script)
        self.assertIn("Start-Sleep -Milliseconds 500", self.script)
        self.assertIn("did not become healthy", self.script.lower())


if __name__ == "__main__":
    unittest.main()
