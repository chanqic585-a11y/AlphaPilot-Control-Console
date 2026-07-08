from __future__ import annotations

from .candidate_promotion_gate import build_candidate_promotion_gate_v2
from .config import SAFETY_BOUNDARY
from .research_action_executor import build_research_action_executor
from .simulation_command_center import build_simulation_command_center
from .state_store import now_iso
from .testnet_readiness_pack import build_testnet_readiness_pack


CONTROL_CONSOLE_VERSION = "V13.8.1"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8_1"


def build_research_execution_pipeline(apply_updates: bool = False) -> dict:
    executor = build_research_action_executor(apply_updates=apply_updates)
    promotion = build_candidate_promotion_gate_v2()
    command = build_simulation_command_center()
    testnet = build_testnet_readiness_pack()
    command_summary = command.get("summary", {}) if isinstance(command.get("summary"), dict) else {}
    promotion_summary = promotion.get("summary", {}) if isinstance(promotion.get("summary"), dict) else {}
    testnet_summary = testnet.get("summary", {}) if isinstance(testnet.get("summary"), dict) else {}
    executor_summary = executor.get("summary", {}) if isinstance(executor.get("summary"), dict) else {}
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "applyUpdates": apply_updates,
        "summary": {
            "researchActionCount": executor_summary.get("actionCount", 0),
            "researchUpdatedTaskCount": executor_summary.get("updatedTaskCount", 0),
            "sandboxReviewCandidateCount": promotion_summary.get("sandboxReviewCandidateCount", 0),
            "testnetReadinessCandidateCount": promotion_summary.get("testnetReadinessCandidateCount", 0),
            "simulationStageLabel": command_summary.get("commandStageLabel", "--"),
            "testnetReadinessStageLabel": testnet_summary.get("readinessStageLabel", "--"),
            "testnetBlockerCount": testnet_summary.get("blockerCount", 0),
            "dryRunApproved": False,
            "liveTradingApproved": False,
            "nextAction": (
                command_summary.get("nextActions", ["继续本地研究执行，暂不进入交易执行。"])[0]
                if isinstance(command_summary.get("nextActions"), list)
                else "继续本地研究执行，暂不进入交易执行。"
            ),
        },
        "researchActionExecutor": executor,
        "candidatePromotionGate": promotion,
        "simulationCommandCenter": command,
        "testnetReadinessPack": testnet,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "The full pipeline is research-only. It cannot store API keys, call Trade API, run exchange Dry-run, or create orders.",
    }
