from __future__ import annotations

import unittest
from pathlib import Path

from alphapilot_control_console.local_demo_launcher import LocalDemoLauncher


ROOT = Path(__file__).resolve().parents[1]


class _FakeProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None

    def poll(self) -> int | None:
        return self.returncode


class LocalDemoLauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []
        self.processes: list[_FakeProcess] = []

        def fake_popen(command: list[str], **kwargs: object) -> _FakeProcess:
            process = _FakeProcess()
            self.calls.append((command, kwargs))
            self.processes.append(process)
            return process

        self.launcher = LocalDemoLauncher(repo_root=ROOT, popen_factory=fake_popen)

    def test_loopback_request_opens_fixed_visible_launcher(self) -> None:
        result = self.launcher.open("127.0.0.1", current_pid=4321, port=8766)

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "launcher_opened")
        self.assertEqual(len(self.calls), 1)
        command, kwargs = self.calls[0]
        command_text = " ".join(map(str, command))
        self.assertIn("start_okx_demo_console.ps1", command_text)
        self.assertIn("-NoExit", command)
        self.assertIn("-EnableOrder", command)
        self.assertIn("-EnableAutomation", command)
        self.assertIn("-EnrollCredentialVault", command)
        self.assertIn("-ReplaceExistingConsole", command)
        self.assertEqual(command[command.index("-ExpectedConsoleProcessId") + 1], "4321")
        self.assertEqual(command[command.index("-Port") + 1], "8766")
        self.assertNotIn("apikey", command_text.lower())
        self.assertEqual(Path(str(kwargs["cwd"])), ROOT)
        self.assertTrue(kwargs["close_fds"])

    def test_ipv6_loopback_is_accepted(self) -> None:
        result = self.launcher.open("::1", current_pid=9876, port=8766)

        self.assertTrue(result["ok"])
        self.assertEqual(len(self.calls), 1)

    def test_non_loopback_request_is_rejected_without_starting_process(self) -> None:
        result = self.launcher.open("192.168.1.20", current_pid=4321, port=8766)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "local_host_required")
        self.assertEqual(self.calls, [])

    def test_invalid_client_address_is_rejected_without_starting_process(self) -> None:
        result = self.launcher.open("not-an-ip", current_pid=4321, port=8766)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "local_host_required")
        self.assertEqual(self.calls, [])

    def test_second_click_does_not_open_duplicate_launcher(self) -> None:
        first = self.launcher.open("127.0.0.1", current_pid=4321, port=8766)
        second = self.launcher.open("127.0.0.1", current_pid=4321, port=8766)

        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertEqual(second["error"], "launcher_already_open")
        self.assertEqual(len(self.calls), 1)

    def test_finished_launcher_can_be_opened_again(self) -> None:
        first = self.launcher.open("127.0.0.1", current_pid=4321, port=8766)
        self.processes[0].returncode = 2
        second = self.launcher.open("127.0.0.1", current_pid=4321, port=8766)

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(len(self.calls), 2)

    def test_mobile_binding_is_preserved_by_fixed_switch(self) -> None:
        result = self.launcher.open("127.0.0.1", current_pid=4321, port=8766, mobile=True)

        self.assertTrue(result["ok"])
        command, _ = self.calls[0]
        self.assertIn("-Mobile", command)

    def test_automatic_prompt_opens_once_for_same_pid_and_failure_class(self) -> None:
        first = self.launcher.open_once_for_failure(
            "127.0.0.1",
            current_pid=4321,
            port=8766,
            failure_class="credential_missing",
        )
        second = self.launcher.open_once_for_failure(
            "127.0.0.1",
            current_pid=4321,
            port=8766,
            failure_class="credential_missing",
        )

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(second["status"], "prompt_suppressed")
        self.assertEqual(len(self.calls), 1)

    def test_new_pid_may_open_a_new_automatic_prompt_after_previous_exits(self) -> None:
        self.launcher.open_once_for_failure(
            "127.0.0.1",
            current_pid=4321,
            port=8766,
            failure_class="credential_missing",
        )
        self.processes[0].returncode = 2

        result = self.launcher.open_once_for_failure(
            "127.0.0.1",
            current_pid=9876,
            port=8766,
            failure_class="credential_missing",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(len(self.calls), 2)


if __name__ == "__main__":
    unittest.main()
