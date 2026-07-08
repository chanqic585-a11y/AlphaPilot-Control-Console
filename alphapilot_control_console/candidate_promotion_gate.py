from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import SAFETY_BOUNDARY
from .research_action_executor import build_research_action_executor
from .simulation_review import build_simulation_review
from .state_store import now_iso
from .weakness_action_board import build_weakness_action_board


CONTROL_CONSOLE_VERSION = "V13.8"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8"
MIN_SANDBOX_REVIEW_SAMPLES = 30
MIN_TESTNET_READINESS_SAMPLES = 100
MIN_PROMOTION_PROFIT_FACTOR = 1.15
MIN_PROMOTION_HEALTH_SCORE = 65.0
MAX_REVIEW_DRAWDOWN_R = 8.0
MAX_ALLOWED_UNRESOLVED_DANGER_ACTIONS = 0


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed else fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _action_key(row: dict[str, Any]) -> str:
    return str(row.get("taskId") or row.get("strategyId") or "").strip()


def _group_actions_by_strategy(actions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in actions:
        if not isinstance(row, dict):
            continue
        key = _action_key(row)
        if key:
            result[key].append(row)
    return result


def _gate_row(strategy: dict[str, Any], action_rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = strategy.get("metrics") if isinstance(strategy.get("metrics"), dict) else {}
    sample_gate = strategy.get("sampleGate") if isinstance(strategy.get("sampleGate"), dict) else {}
    closed_samples = _safe_int(metrics.get("closedSamples"), _safe_int(sample_gate.get("closedSamples")))
    profit_factor = _safe_float(metrics.get("profitFactor"), -1.0)
    max_drawdown_r = _safe_float(metrics.get("maxDrawdownR"), 999.0)
    health_score = _safe_float(metrics.get("healthScore"))
    risk_warnings = _safe_int(metrics.get("riskWarningCount"))
    invalidated = _safe_int(metrics.get("invalidatedCount"))
    unresolved_actions = [
        row
        for row in action_rows
        if str(row.get("taskStatus") or "todo") not in {"resolved", "archived"}
    ]
    danger_actions = [row for row in unresolved_actions if row.get("priorityTone") == "danger"]
    missing: list[str] = []
    passed: list[str] = []

    if closed_samples >= MIN_SANDBOX_REVIEW_SAMPLES:
        passed.append(f"闭合样本 {closed_samples} >= {MIN_SANDBOX_REVIEW_SAMPLES}")
    else:
        missing.append(f"闭合样本不足：{closed_samples}/{MIN_SANDBOX_REVIEW_SAMPLES}")

    if profit_factor >= MIN_PROMOTION_PROFIT_FACTOR:
        passed.append(f"PF {profit_factor:.2f} >= {MIN_PROMOTION_PROFIT_FACTOR:.2f}")
    else:
        missing.append("PF 不足或缺失")

    if max_drawdown_r <= MAX_REVIEW_DRAWDOWN_R:
        passed.append(f"回撤 {max_drawdown_r:.2f}R <= {MAX_REVIEW_DRAWDOWN_R:.2f}R")
    else:
        missing.append(f"回撤过高或缺失：{max_drawdown_r:.2f}R")

    if health_score >= MIN_PROMOTION_HEALTH_SCORE:
        passed.append(f"健康分 {health_score:.0f} >= {MIN_PROMOTION_HEALTH_SCORE:.0f}")
    else:
        missing.append(f"健康分不足：{health_score:.0f}/{MIN_PROMOTION_HEALTH_SCORE:.0f}")

    if risk_warnings <= 0 and invalidated <= 0:
        passed.append("无待复核风险/失效记录")
    else:
        missing.append(f"风险/失效待复核：risk={risk_warnings}, invalidated={invalidated}")

    if len(danger_actions) <= MAX_ALLOWED_UNRESOLVED_DANGER_ACTIONS:
        passed.append("无未解决高优先级弱点")
    else:
        missing.append(f"未解决高优先级弱点 {len(danger_actions)} 条")

    can_sandbox_review = not missing and closed_samples >= MIN_SANDBOX_REVIEW_SAMPLES
    can_testnet_readiness = (
        can_sandbox_review
        and closed_samples >= MIN_TESTNET_READINESS_SAMPLES
        and not unresolved_actions
    )
    if can_testnet_readiness:
        tier = "testnet_readiness_candidate"
        label = "Testnet 就绪候选"
        tone = "warn"
        next_action = "可以进入 testnet 设计复核，但仍不得接入密钥或创建订单。"
    elif can_sandbox_review:
        tier = "sandbox_review_candidate"
        label = "本地复核候选"
        tone = "ok"
        next_action = "进入本地复核候选，继续补足 100 个闭合样本和所有弱点关闭记录。"
    else:
        tier = "collecting_evidence"
        label = "继续补证据"
        tone = "warn" if closed_samples else "danger"
        next_action = "继续跑本地沙盒和研究行动执行器，先处理缺口。"

    return {
        "strategyId": strategy.get("strategyId"),
        "taskId": strategy.get("taskId"),
        "strategyName": strategy.get("strategyName"),
        "timeframe": strategy.get("timeframe"),
        "promotionTier": tier,
        "promotionLabel": label,
        "tone": tone,
        "closedSamples": closed_samples,
        "profitFactor": None if profit_factor < 0 else profit_factor,
        "maxDrawdownR": None if max_drawdown_r >= 999 else max_drawdown_r,
        "healthScore": health_score,
        "unresolvedActionCount": len(unresolved_actions),
        "dangerActionCount": len(danger_actions),
        "passedChecks": passed,
        "missingChecks": missing,
        "nextAction": next_action,
        "canEnterSandboxReview": can_sandbox_review,
        "canEnterTestnetReadiness": can_testnet_readiness,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyNote": "晋级结论只表示研究层级，不是交易许可。",
    }


def build_candidate_promotion_gate_v2() -> dict[str, Any]:
    review = build_simulation_review()
    weakness = build_weakness_action_board()
    executor = build_research_action_executor(apply_updates=False)
    queue = review.get("queue") if isinstance(review.get("queue"), list) else []
    actions = weakness.get("actions") if isinstance(weakness.get("actions"), list) else []
    grouped_actions = _group_actions_by_strategy(actions)
    rows = [
        _gate_row(
            strategy,
            grouped_actions.get(str(strategy.get("taskId") or ""), [])
            or grouped_actions.get(str(strategy.get("strategyId") or ""), []),
        )
        for strategy in queue
        if isinstance(strategy, dict)
    ]
    rows.sort(key=lambda row: (
        row.get("promotionTier") != "testnet_readiness_candidate",
        row.get("promotionTier") != "sandbox_review_candidate",
        -_safe_int(row.get("closedSamples")),
        -_safe_float(row.get("profitFactor"), -1.0),
    ))
    sandbox_count = sum(1 for row in rows if row.get("canEnterSandboxReview"))
    testnet_count = sum(1 for row in rows if row.get("canEnterTestnetReadiness"))
    blocked_count = len(rows) - sandbox_count
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "strategyCount": len(rows),
            "sandboxReviewCandidateCount": sandbox_count,
            "testnetReadinessCandidateCount": testnet_count,
            "blockedCandidateCount": blocked_count,
            "unresolvedWeaknessActionCount": sum(_safe_int(row.get("unresolvedActionCount")) for row in rows),
            "executorActionCount": executor.get("summary", {}).get("actionCount") if isinstance(executor.get("summary"), dict) else 0,
            "dryRunApproved": False,
            "liveTradingApproved": False,
            "nextAction": (
                "先把本地复核候选补到 100 个闭合样本，并关闭高优先级弱点。"
                if sandbox_count
                else "当前没有策略达到本地复核候选门槛，继续收集证据。"
            ),
        },
        "thresholds": {
            "minSandboxReviewSamples": MIN_SANDBOX_REVIEW_SAMPLES,
            "minTestnetReadinessSamples": MIN_TESTNET_READINESS_SAMPLES,
            "minProfitFactor": MIN_PROMOTION_PROFIT_FACTOR,
            "minHealthScore": MIN_PROMOTION_HEALTH_SCORE,
            "maxDrawdownR": MAX_REVIEW_DRAWDOWN_R,
            "maxUnresolvedDangerActions": MAX_ALLOWED_UNRESOLVED_DANGER_ACTIONS,
        },
        "rows": rows,
        "dryRunApproved": False,
        "liveTradingApproved": False,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Candidate promotion gate is a research-level gate only. It never creates orders.",
    }
