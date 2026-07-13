from __future__ import annotations

import unittest
from unittest.mock import Mock

from alphapilot_control_console.demo_startup_arm import arm_okx_demo_runtime_on_startup


class DemoStartupArmTests(unittest.TestCase):
    def test_does_not_arm_without_launcher_confirmation(self) -> None:
        action_runner = Mock()

        result = arm_okx_demo_runtime_on_startup(
            environ={
                "ALPHAPILOT_OKX_DEMO_ENABLED": "1",
                "ALPHAPILOT_OKX_DEMO_ORDER_ENABLED": "1",
                "ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED": "1",
            },
            action_runner=action_runner,
        )

        action_runner.assert_not_called()
        self.assertEqual(result["status"], "not_requested")
        self.assertEqual(result["blocker"], "launcher_confirmation_missing")

    def test_does_not_arm_when_any_demo_gate_is_disabled(self) -> None:
        action_runner = Mock()
        base = {
            "ALPHAPILOT_OKX_DEMO_LAUNCHER_CONFIRMED": "1",
            "ALPHAPILOT_OKX_DEMO_ENABLED": "1",
            "ALPHAPILOT_OKX_DEMO_ORDER_ENABLED": "1",
            "ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED": "1",
        }

        for variable in (
            "ALPHAPILOT_OKX_DEMO_ENABLED",
            "ALPHAPILOT_OKX_DEMO_ORDER_ENABLED",
            "ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED",
        ):
            with self.subTest(variable=variable):
                environ = dict(base)
                environ[variable] = "0"
                result = arm_okx_demo_runtime_on_startup(
                    environ=environ,
                    action_runner=action_runner,
                )
                self.assertEqual(result["status"], "not_requested")
                self.assertEqual(result["blocker"], "demo_gate_disabled")

        action_runner.assert_not_called()

    def test_arms_okx_demo_once_after_explicit_launcher_confirmation(self) -> None:
        action_runner = Mock(return_value={"ok": True, "state": "running"})

        result = arm_okx_demo_runtime_on_startup(
            environ={
                "ALPHAPILOT_OKX_DEMO_LAUNCHER_CONFIRMED": "1",
                "ALPHAPILOT_OKX_DEMO_ENABLED": "1",
                "ALPHAPILOT_OKX_DEMO_ORDER_ENABLED": "1",
                "ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED": "1",
            },
            action_runner=action_runner,
        )

        action_runner.assert_called_once_with({
            "environment": "okx_demo",
            "action": "start",
            "source": "confirmed_demo_launcher_startup",
        })
        self.assertEqual(result["status"], "requested")
        self.assertEqual(result["result"], {"ok": True, "state": "running"})

    def test_fails_closed_when_arm_action_raises(self) -> None:
        action_runner = Mock(side_effect=RuntimeError("private detail"))

        result = arm_okx_demo_runtime_on_startup(
            environ={
                "ALPHAPILOT_OKX_DEMO_LAUNCHER_CONFIRMED": "1",
                "ALPHAPILOT_OKX_DEMO_ENABLED": "1",
                "ALPHAPILOT_OKX_DEMO_ORDER_ENABLED": "1",
                "ALPHAPILOT_OKX_DEMO_AUTOMATION_ENABLED": "1",
            },
            action_runner=action_runner,
        )

        self.assertEqual(result, {
            "status": "blocked",
            "blocker": "startup_arm_failed",
        })


if __name__ == "__main__":
    unittest.main()
