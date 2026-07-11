from __future__ import annotations

import threading
import time
import unittest

from alphapilot_control_console.unified_auto_execution_runner import (
    UnifiedAutoExecutionRunner,
)


class FakeController:
    def __init__(self) -> None:
        self.armed = {"okx_demo": False, "okx_live": False}
        self.heartbeat_calls: list[str] = []
        self.actions: list[tuple[str, str]] = []
        self.heartbeat_event = threading.Event()

    def status(self, environment: str) -> dict:
        return {
            "environment": environment,
            "desiredEnabled": False,
            "armedForCurrentProcess": self.armed[environment],
        }

    def heartbeat(self, environment: str) -> dict:
        self.heartbeat_calls.append(environment)
        self.heartbeat_event.set()
        return {"environment": environment, "status": "waiting"}

    def arm(self, environment: str) -> dict:
        self.armed[environment] = True
        self.actions.append((environment, "arm"))
        return self.status(environment)

    def start(self, environment: str) -> dict:
        self.actions.append((environment, "start"))
        return self.status(environment)

    def pause(self, environment: str, reason: str) -> dict:
        self.actions.append((environment, "pause:" + reason))
        return self.status(environment)

    def stop(self, environment: str, reason: str) -> dict:
        self.actions.append((environment, "stop:" + reason))
        return self.status(environment)

    def emergency_stop(self, environment: str, reason: str) -> dict:
        self.actions.append((environment, "emergency_stop:" + reason))
        return {"ok": True, "runtime": self.status(environment)}


class UnifiedAutoExecutionRunnerTests(unittest.TestCase):
    def test_runner_wakes_immediately_does_not_duplicate_and_stops_cleanly(self) -> None:
        controller = FakeController()
        runner = UnifiedAutoExecutionRunner(controller=controller, interval_seconds=0.02)

        first_thread = runner.start()
        self.assertTrue(controller.heartbeat_event.wait(1))
        second_thread = runner.start()
        runner.stop()

        self.assertIs(first_thread, second_thread)
        self.assertFalse(first_thread.is_alive())
        self.assertIn("okx_demo", controller.heartbeat_calls)
        self.assertIn("okx_live", controller.heartbeat_calls)

    def test_demo_start_arms_without_order_confirmation(self) -> None:
        controller = FakeController()
        runner = UnifiedAutoExecutionRunner(controller=controller)

        result = runner.action("okx_demo", "start", {})

        self.assertTrue(result["ok"])
        self.assertEqual(controller.actions[:2], [("okx_demo", "arm"), ("okx_demo", "start")])

    def test_status_exposes_each_environments_last_heartbeat_result(self) -> None:
        controller = FakeController()
        runner = UnifiedAutoExecutionRunner(controller=controller)

        runner.run_once()
        status = runner.status()

        self.assertEqual(status["environments"]["okx_demo"]["lastHeartbeatResult"]["status"], "waiting")

    def test_live_start_requires_current_process_arm(self) -> None:
        controller = FakeController()
        runner = UnifiedAutoExecutionRunner(controller=controller)

        blocked = runner.action("okx_live", "start", {})
        self.assertFalse(blocked["ok"])
        self.assertIn("live_process_arm_required", blocked["blockers"])

        controller.armed["okx_live"] = True
        ready = runner.action("okx_live", "start", {})
        self.assertTrue(ready["ok"])
        self.assertIn(("okx_live", "start"), controller.actions)

    def test_emergency_stop_routes_only_to_selected_environment(self) -> None:
        controller = FakeController()
        runner = UnifiedAutoExecutionRunner(controller=controller)

        result = runner.action("okx_demo", "emergency_stop", {"reason": "unit_test"})

        self.assertTrue(result["ok"])
        self.assertEqual(controller.actions, [("okx_demo", "emergency_stop:unit_test")])


if __name__ == "__main__":
    unittest.main()
