from __future__ import annotations

from typing import Any

from .candidate_promotion_gate import build_candidate_promotion_gate_v2
from .config import SAFETY_BOUNDARY
from .sandbox_auto_runner import get_local_sandbox_auto_runner_status
from .simulation_bridge import build_simulation_bridge
from .simulation_review import build_simulation_review
from .state_store import list_local_sandbox_daily_reports, list_research_action_execution_runs, now_iso
from .weakness_action_board import build_weakness_action_board


CONTROL_CONSOLE_VERSION = "V13.8"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8"


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed else fallback


def _top_action(weakness: dict[str, Any]) -> dict[str, Any]:
    actions = weakness.get("actions") if isinstance(weakness.get("actions"), list) else []
    active = [
        row
        for row in actions
        if isinstance(row, dict) and str(row.get("taskStatus") or "todo") not in {"resolved", "archived"}
    ]
    return active[0] if active else {}


def build_simulation_command_center() -> dict[str, Any]:
    bridge = build_simulation_bridge()
    review = build_simulation_review()
    promotion = build_candidate_promotion_gate_v2()
    weakness = build_weakness_action_board()
    runner_payload = get_local_sandbox_auto_runner_status()
    runner = runner_payload.get("autoRunner") if isinstance(runner_payload.get("autoRunner"), dict) else {}
    daily_reports = list_local_sandbox_daily_reports(1)
    latest_daily = daily_reports[0] if daily_reports and isinstance(daily_reports[0], dict) else {}
    latest_execution_runs = list_research_action_execution_runs(3)
    bridge_summary = bridge.get("summary") if isinstance(bridge.get("summary"), dict) else {}
    review_summary = review.get("summary") if isinstance(review.get("summary"), dict) else {}
    promotion_summary = promotion.get("summary") if isinstance(promotion.get("summary"), dict) else {}
    weakness_summary = weakness.get("summary") if isinstance(weakness.get("summary"), dict) else {}
    top_action = _top_action(weakness)

    runner_enabled = bool(runner.get("enabled"))
    strategy_count = _safe_int(bridge_summary.get("strategyCount"))
    closed_samples = _safe_int(bridge_summary.get("totalClosedSampleCount"))
    sandbox_candidates = _safe_int(promotion_summary.get("sandboxReviewCandidateCount"))
    blocked_actions = _safe_int(weakness_summary.get("blockedUpgradeCount"))
    command_stage = "running" if runner_enabled else "ready" if strategy_count else "waiting"
    next_actions: list[str] = []
    if not runner_enabled and strategy_count:
        next_actions.append("开启本地沙盒自动运行，持续累计闭合样本。")
    if closed_samples < 30:
        next_actions.append("先把至少一条策略补到 30 个闭合样本。")
    if top_action:
        next_actions.append(f"优先处理弱点：{top_action.get('strategyName')} / {top_action.get('weaknessLabel')}")
    if sandbox_candidates:
        next_actions.append("对本地复核候选继续补到 100 个闭合样本，再进入 testnet 设计复核。")
    if not next_actions:
        next_actions.append("保持沙盒运行并定期复核弱点行动，不进入交易执行。")

    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "commandStage": command_stage,
            "commandStageLabel": {
                "running": "本地沙盒运行中",
                "ready": "本地沙盒可启动",
                "waiting": "等待策略目录",
            }.get(command_stage, command_stage),
            "strategyCount": strategy_count,
            "totalClosedSampleCount": closed_samples,
            "totalVirtualCapital": bridge_summary.get("totalVirtualCapital"),
            "totalVirtualEquity": bridge_summary.get("totalVirtualEquity"),
            "reviewReadyStrategies": review_summary.get("reviewReadyStrategies"),
            "sandboxReviewCandidateCount": sandbox_candidates,
            "testnetReadinessCandidateCount": promotion_summary.get("testnetReadinessCandidateCount"),
            "blockedWeaknessActionCount": blocked_actions,
            "autoRunnerEnabled": runner_enabled,
            "autoRunnerIntervalMinutes": runner.get("intervalMinutes"),
            "todayRunCount": runner.get("todayRunCount"),
            "maxRunsPerDay": runner.get("maxRunsPerDay"),
            "latestDailyReportId": latest_daily.get("reportId"),
            "latestExecutionRunId": latest_execution_runs[0].get("runId") if latest_execution_runs else None,
            "dryRunApproved": False,
            "liveTradingApproved": False,
            "nextActions": next_actions,
        },
        "topWeaknessAction": top_action,
        "latestDailyReport": latest_daily,
        "latestResearchExecutionRuns": latest_execution_runs,
        "promotionPreview": promotion.get("rows", [])[:8],
        "runner": runner,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Simulation command center controls local research observation only; it cannot place or route orders.",
    }
