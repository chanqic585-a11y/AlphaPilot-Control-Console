from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from alphapilot_control_console.unified_auto_execution_adapters import (
    OkxDemoAutoExecutionAdapter,
)
from alphapilot_control_console.unified_auto_execution_controller import ReleaseSchedule


FINAL_RELEASE_ID = "approved-top200-release"


def _runtime(*, armed: bool) -> dict:
    components = [
        {
            "demoReleaseId": FINAL_RELEASE_ID,
            "strategyCandidateId": "component-1h",
            "strategy": {"marketDefinition": {"timeframe": "1h"}},
        },
        {
            "demoReleaseId": FINAL_RELEASE_ID,
            "strategyCandidateId": "component-1d-a",
            "strategy": {"marketDefinition": {"timeframe": "1d"}},
        },
        {
            "demoReleaseId": FINAL_RELEASE_ID,
            "strategyCandidateId": "component-1d-b",
            "strategy": {"marketDefinition": {"timeframe": "1d"}},
        },
    ]
    return {
        "approved": True,
        "armed": armed,
        "executionEnabled": armed,
        "notKilled": True,
        "blockers": [] if armed else ["exact_demo_arm_required"],
        "componentContracts": components,
        "schedules": [
            {
                "releaseId": FINAL_RELEASE_ID,
                "strategyId": "portfolio:1h",
                "timeframe": "1h",
            },
            {
                "releaseId": FINAL_RELEASE_ID,
                "strategyId": "portfolio:1d",
                "timeframe": "1d",
            },
        ],
    }


def test_adapter_lists_only_approved_portfolio_timeframe_schedules() -> None:
    with patch(
        "alphapilot_control_console.unified_auto_execution_adapters.load_approved_top200_demo_runtime",
        return_value=_runtime(armed=False),
    ):
        schedules = OkxDemoAutoExecutionAdapter().list_releases()

    assert [(row.releaseId, row.strategyId, row.timeframe) for row in schedules] == [
        (FINAL_RELEASE_ID, "portfolio:1h", "1h"),
        (FINAL_RELEASE_ID, "portfolio:1d", "1d"),
    ]


def test_adapter_refuses_batch_before_exact_arm() -> None:
    release = ReleaseSchedule(FINAL_RELEASE_ID, "portfolio:1h", "1h")
    close_event = SimpleNamespace(timeframe="1h")
    with patch(
        "alphapilot_control_console.unified_auto_execution_adapters.load_approved_top200_demo_runtime",
        return_value=_runtime(armed=False),
    ), patch(
        "alphapilot_control_console.unified_auto_execution_adapters.run_evolution_demo_batch_cycle"
    ) as batch:
        result = OkxDemoAutoExecutionAdapter().run_batch(
            [release], {}, close_event=close_event
        )

    assert result["ok"] is False
    assert result["blockers"] == ["exact_demo_arm_required"]
    batch.assert_not_called()


def test_adapter_routes_only_components_for_confirmed_close_timeframe() -> None:
    release = ReleaseSchedule(FINAL_RELEASE_ID, "portfolio:1d", "1d")
    close_event = SimpleNamespace(timeframe="1d")
    runtime = _runtime(armed=True)
    with patch(
        "alphapilot_control_console.unified_auto_execution_adapters.load_approved_top200_demo_runtime",
        return_value=runtime,
    ), patch(
        "alphapilot_control_console.unified_auto_execution_adapters.run_evolution_demo_batch_cycle",
        return_value={"ok": True, "signals": [], "results": []},
    ) as batch:
        result = OkxDemoAutoExecutionAdapter().run_batch(
            [release], {}, close_event=close_event
        )

    assert result["ok"] is True
    call = batch.call_args
    assert call.args[0] == [FINAL_RELEASE_ID]
    assert call.kwargs["close_event"] is close_event
    assert {
        row["strategyCandidateId"] for row in call.kwargs["contracts_override"]
    } == {"component-1d-a", "component-1d-b"}


def test_adapter_reconciles_only_the_approved_portfolio_components() -> None:
    runtime = _runtime(armed=True)
    with patch(
        "alphapilot_control_console.unified_auto_execution_adapters.load_approved_top200_demo_runtime",
        return_value=runtime,
    ), patch(
        "alphapilot_control_console.unified_auto_execution_adapters.reconcile_evolution_demo_runtime",
        return_value={"ok": True},
    ) as reconcile:
        result = OkxDemoAutoExecutionAdapter().reconcile()

    assert result["ok"] is True
    reconcile.assert_called_once_with(
        contracts_override=runtime["componentContracts"],
    )
