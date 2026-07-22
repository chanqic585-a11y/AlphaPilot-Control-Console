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

    def test_cmd_wrapper_does_not_override_the_console_venv_python(self) -> None:
        self.assertNotIn("ALPHAPILOT_PY", self.wrapper)
        self.assertNotIn("-PythonPath", self.wrapper)
        self.assertNotIn("codex-primary-runtime\\dependencies\\python", self.wrapper)

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

    def test_first_start_uses_console_venv_with_pinned_websocket_runtime(self) -> None:
        self.assertIn('.venv\\Scripts\\python.exe', self.script)
        self.assertIn('import websocket', self.script)
        self.assertIn("websocket.__version__", self.script)
        self.assertNotIn("codex-primary-runtime\\dependencies\\python", self.script)

    def test_repository_default_is_resolved_after_script_parameter_binding(self) -> None:
        self.assertIn('[string]$RepositoryPath = ""', self.script)
        self.assertIn('if ([string]::IsNullOrWhiteSpace($RepositoryPath))', self.script)
        self.assertIn('$RepositoryPath = Split-Path -Parent $PSScriptRoot', self.script)

    def test_browser_open_uses_windows_shell_with_a_url_fallback(self) -> None:
        self.assertIn('Start-Process -FilePath "explorer.exe"', self.script)
        self.assertIn('Start-Process -FilePath $ConsoleUrl', self.script)


if __name__ == "__main__":
    unittest.main()
