from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import SAFETY_BOUNDARY, get_quant_engine_path
from .state_store import append_audit, load_state, now_iso, read_exchange_probe_results, write_mobile_status

CONTROL_CONSOLE_VERSION = "V13.7.1"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_7_1"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _bool(data: dict[str, Any], key: str) -> bool:
    return bool(data.get(key))


def _report_summary(report: dict[str, Any], path: Path) -> dict[str, Any]:
    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    return {
        "reportId": report.get("reportId") or path.stem,
        "version": report.get("version"),
        "status": report.get("status"),
        "generatedAt": report.get("generatedAt"),
        "path": str(path),
        "exchangeDryRunApproved": _bool(decision, "exchangeDryRunApproved")
        or _bool(report, "exchangeDryRunApproved"),
        "liveTradingApproved": _bool(decision, "liveTradingApproved") or _bool(report, "liveTradingApproved"),
        "summary": _compact_report_summary(report),
    }


def _compact_report_summary(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("ledgerMetrics"):
        metrics = report["ledgerMetrics"]
        return {
            "kind": "local_paper_ledger",
            "filledSignalCount": metrics.get("filledSignalCount"),
            "winRatePct": metrics.get("winRatePct"),
            "profitFactor": metrics.get("profitFactor"),
            "rewardRiskRatio": metrics.get("rewardRiskRatio"),
            "maxDrawdownPct": metrics.get("maxDrawdownPct"),
        }
    if report.get("bestRawCandidate"):
        candidate = report["bestRawCandidate"]
        metrics = candidate.get("metrics", {})
        return {
            "kind": "alpha_replay",
            "candidateId": candidate.get("candidateId"),
            "tradeCount": metrics.get("tradeCount"),
            "winRatePct": metrics.get("winRatePct"),
            "profitFactor": metrics.get("profitFactor"),
            "rewardRiskRatio": metrics.get("rewardRiskRatio"),
            "rawGatePassed": candidate.get("gate", {}).get("passed"),
        }
    return {"kind": "report"}


def _strategy_from_package(package: dict[str, Any], report: dict[str, Any] | None, path: Path) -> dict[str, Any]:
    ledger_metrics = (report or {}).get("ledgerMetrics", {})
    gate = (report or {}).get("gate", {})
    gate_passed = bool(gate.get("passed") or gate.get("localPaperRefreshCandidateReady"))
    strategy_id = package.get("packageId") or package.get("candidateId") or path.stem
    suggested_status = "local_paper_ready" if gate_passed else "research_only"
    if package.get("exchangeDryRunApproved") or package.get("liveTradingApproved"):
        suggested_status = "disabled"
    return {
        "strategyId": strategy_id,
        "title": package.get("candidateId") or strategy_id,
        "version": package.get("version"),
        "candidateId": package.get("candidateId"),
        "selectedPolicyId": package.get("selectedPolicyId"),
        "sourcePath": str(path),
        "sourceReport": str(path.parent / "v13_5_21_local_paper_refresh_candidate_report.json"),
        "suggestedStatus": suggested_status,
        "selectedSignalCount": package.get("selectedSignalCount"),
        "stopLossPct": package.get("stopLossPct"),
        "targetRMultiple": package.get("targetRMultiple"),
        "maxConcurrentPositions": package.get("maxConcurrentPositions"),
        "riskPerSignalPct": package.get("riskPerSignalPct"),
        "localSimulationOnly": bool(package.get("localSimulationOnly", True)),
        "exchangeDryRunApproved": bool(package.get("exchangeDryRunApproved", False)),
        "liveTradingApproved": bool(package.get("liveTradingApproved", False)),
        "metrics": {
            "filledSignalCount": ledger_metrics.get("filledSignalCount"),
            "winRatePct": ledger_metrics.get("winRatePct"),
            "profitFactor": ledger_metrics.get("profitFactor"),
            "rewardRiskRatio": ledger_metrics.get("rewardRiskRatio"),
            "maxDrawdownPct": ledger_metrics.get("maxDrawdownPct"),
        },
        "gate": gate,
    }


def _strategy_from_alpha191_report(report: dict[str, Any], path: Path) -> dict[str, Any]:
    candidate = report.get("bestRawCandidate") or {}
    metrics = candidate.get("metrics", {})
    decision = report.get("decision") or {}
    return {
        "strategyId": "v13_5_23_alpha191_crypto_subset_observer",
        "title": candidate.get("candidateId") or "V13.5.23 Alpha191 crypto-safe subset observer",
        "version": report.get("version"),
        "candidateId": candidate.get("candidateId"),
        "selectedPolicyId": (report.get("bestExitAwarePolicy") or {}).get("policyId"),
        "sourcePath": str(path),
        "sourceReport": str(path),
        "suggestedStatus": "research_only",
        "selectedSignalCount": (report.get("bestExitAwarePolicy") or {}).get("selectedSignalCount"),
        "stopLossPct": candidate.get("stopLossPct"),
        "targetRMultiple": candidate.get("targetRMultiple"),
        "maxConcurrentPositions": None,
        "riskPerSignalPct": None,
        "localSimulationOnly": True,
        "exchangeDryRunApproved": bool(decision.get("exchangeDryRunApproved", False)),
        "liveTradingApproved": bool(decision.get("liveTradingApproved", False)),
        "metrics": {
            "tradeCount": metrics.get("tradeCount"),
            "winRatePct": metrics.get("winRatePct"),
            "profitFactor": metrics.get("profitFactor"),
            "rewardRiskRatio": metrics.get("rewardRiskRatio"),
            "maxDrawdownPct": metrics.get("maxDrawdownPct"),
        },
        "gate": {
            "rawReplayGatePassed": decision.get("rawReplayGatePassed"),
            "exitAwareGatePassed": decision.get("exitAwareGatePassed"),
            "localPaperGatePassed": decision.get("localPaperGatePassed"),
        },
    }


def scan_quant_engine() -> dict[str, Any]:
    quant_path = get_quant_engine_path()
    reports_dir = quant_path / "reports"
    state = load_state()
    strategies: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []

    if reports_dir.exists():
        for report_path in sorted(reports_dir.glob("v13_5_*_report.json")):
            report = _read_json(report_path)
            if report:
                reports.append(_report_summary(report, report_path))

        package_path = reports_dir / "v13_5_21_local_paper_refresh_candidate_package.json"
        package = _read_json(package_path)
        report = _read_json(reports_dir / "v13_5_21_local_paper_refresh_candidate_report.json")
        if package:
            strategies.append(_strategy_from_package(package, report, package_path))

        alpha191_path = reports_dir / "v13_5_23_alpha191_crypto_subset_replay_report.json"
        alpha191_report = _read_json(alpha191_path)
        if alpha191_report:
            strategies.append(_strategy_from_alpha191_report(alpha191_report, alpha191_path))

    runtime_status = _read_json(reports_dir / "runtime_status.json") if reports_dir.exists() else None
    signal_tape = _read_json(reports_dir / "signal_tape.json") if reports_dir.exists() else None
    paper_observation_ledger = _read_json(reports_dir / "paper_observation_ledger.json") if reports_dir.exists() else None

    state_by_strategy = state.get("strategies", {})
    for strategy in strategies:
        override = state_by_strategy.get(strategy["strategyId"], {})
        strategy["consoleStatus"] = override.get("status") or strategy["suggestedStatus"]
        strategy["consoleNote"] = override.get("note") or ""
        strategy["consoleUpdatedAt"] = override.get("updatedAt")

    payload = {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "quantEnginePath": str(quant_path),
        "quantEngineAvailable": quant_path.exists(),
        "reportsDirAvailable": reports_dir.exists(),
        "generatedAt": now_iso(),
        "safetyBoundary": SAFETY_BOUNDARY,
        "strategies": strategies,
        "reports": sorted(reports, key=lambda item: item.get("generatedAt") or "", reverse=True)[:30],
        "runtimeStatus": runtime_status or {},
        "signalTape": signal_tape or {},
        "paperObservationLedger": paper_observation_ledger or {},
    }
    write_mobile_status(build_mobile_status(payload))
    return payload


def _compact_signal_tape(signal_tape: dict[str, Any], limit: int = 20) -> dict[str, Any]:
    signals = signal_tape.get("signals") if isinstance(signal_tape.get("signals"), list) else []
    return {
        "version": signal_tape.get("version"),
        "generatedAt": signal_tape.get("generatedAt"),
        "source": signal_tape.get("source"),
        "summary": signal_tape.get("summary") if isinstance(signal_tape.get("summary"), dict) else {},
        "signals": signals[:limit],
    }


def _compact_paper_observation_ledger(paper_ledger: dict[str, Any], limit: int = 20) -> dict[str, Any]:
    observations = paper_ledger.get("observations") if isinstance(paper_ledger.get("observations"), list) else []
    return {
        "version": paper_ledger.get("version"),
        "generatedAt": paper_ledger.get("generatedAt"),
        "source": paper_ledger.get("source"),
        "summary": paper_ledger.get("summary") if isinstance(paper_ledger.get("summary"), dict) else {},
        "observations": observations[:limit],
    }


def _compact_runtime_status(runtime_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": runtime_status.get("version"),
        "generatedAt": runtime_status.get("generatedAt"),
        "source": runtime_status.get("source"),
        "activeStrategy": runtime_status.get("activeStrategy")
        if isinstance(runtime_status.get("activeStrategy"), dict)
        else None,
        "strategyCount": runtime_status.get("strategyCount"),
        "reportCount": runtime_status.get("reportCount"),
        "signalTapeCount": runtime_status.get("signalTapeCount"),
        "paperObservationCount": runtime_status.get("paperObservationCount"),
        "runtimeHealth": runtime_status.get("runtimeHealth")
        if isinstance(runtime_status.get("runtimeHealth"), dict)
        else {},
        "latestSignalTime": runtime_status.get("latestSignalTime"),
        "paperObservationSummary": runtime_status.get("paperObservationSummary")
        if isinstance(runtime_status.get("paperObservationSummary"), dict)
        else {},
        "nextStep": runtime_status.get("nextStep"),
        "contractFiles": runtime_status.get("contractFiles")
        if isinstance(runtime_status.get("contractFiles"), dict)
        else {},
    }


def _metric_number(metrics: dict[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    try:
        number_value = float(value)
    except (TypeError, ValueError):
        return None
    return number_value


def _strategy_signal_count(strategy: dict[str, Any] | None) -> int | None:
    if not strategy:
        return None
    metrics = strategy.get("metrics") if isinstance(strategy.get("metrics"), dict) else {}
    value = strategy.get("selectedSignalCount") or metrics.get("filledSignalCount") or metrics.get("tradeCount")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _pick_primary_strategy(strategies: list[dict[str, Any]]) -> dict[str, Any] | None:
    for status in ("local_paper_ready", "forward_testing", "research_only"):
        strategy = next((item for item in strategies if item.get("consoleStatus") == status), None)
        if strategy:
            return strategy
    return strategies[0] if strategies else None


def _build_command_summary(payload: dict[str, Any]) -> dict[str, Any]:
    strategies = payload.get("strategies") if isinstance(payload.get("strategies"), list) else []
    reports = payload.get("reports") if isinstance(payload.get("reports"), list) else []
    primary = _pick_primary_strategy(strategies)
    metrics = primary.get("metrics", {}) if primary else {}
    ready_count = sum(1 for item in strategies if item.get("consoleStatus") == "local_paper_ready")
    research_count = sum(1 for item in strategies if item.get("consoleStatus") == "research_only")
    signal_count = _strategy_signal_count(primary)
    win_rate = _metric_number(metrics, "winRatePct")
    profit_factor = _metric_number(metrics, "profitFactor")
    reward_risk = _metric_number(metrics, "rewardRiskRatio")
    max_drawdown = _metric_number(metrics, "maxDrawdownPct")

    health_score = 0
    if primary:
        health_score += 20
    if ready_count > 0:
        health_score += 20
    if signal_count and signal_count >= 10:
        health_score += 15
    if profit_factor is not None and profit_factor >= 1:
        health_score += 15
    if reward_risk is not None and reward_risk >= 1.5:
        health_score += 15
    if max_drawdown is not None and max_drawdown <= 25:
        health_score += 15
    health_score = min(100, health_score)

    if ready_count > 0:
        readiness = "local_paper_review_ready"
    elif primary:
        readiness = "research_observer_ready"
    else:
        readiness = "needs_quant_report_import"

    if health_score >= 75:
        health_label = "healthy_research_runtime"
    elif health_score >= 45:
        health_label = "partial_research_runtime"
    else:
        health_label = "needs_more_data"

    return {
        "activeStrategyId": primary.get("strategyId") if primary else None,
        "activeStrategyTitle": primary.get("title") if primary else None,
        "activeStrategyVersion": primary.get("version") if primary else None,
        "activeStatus": primary.get("consoleStatus") if primary else None,
        "readyCount": ready_count,
        "researchCount": research_count,
        "reportCount": len(reports),
        "strategyCount": len(strategies),
        "signalCount": signal_count,
        "winRatePct": win_rate,
        "profitFactor": profit_factor,
        "rewardRiskRatio": reward_risk,
        "maxDrawdownPct": max_drawdown,
        "healthScore": health_score,
        "healthLabel": health_label,
        "readiness": readiness,
        "executionLockLabel": "read_only_no_trade_execution",
        "nextStep": "Review strategy, signal, risk, and local paper evidence before any future manual action.",
    }


def build_mobile_status(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": payload["version"],
        "generatedAt": payload["generatedAt"],
        "source": payload["source"],
        "safetyBoundary": payload["safetyBoundary"],
        "strategyCount": len(payload["strategies"]),
        "commandSummary": _build_command_summary(payload),
        "runtimeStatus": _compact_runtime_status(payload.get("runtimeStatus", {})),
        "signalTape": _compact_signal_tape(payload.get("signalTape", {})),
        "paperObservationLedger": _compact_paper_observation_ledger(payload.get("paperObservationLedger", {})),
        "exchangeConnectivity": _mobile_exchange_connectivity(),
        "strategies": [
            {
                "strategyId": item["strategyId"],
                "title": item["title"],
                "version": item["version"],
                "consoleStatus": item["consoleStatus"],
                "suggestedStatus": item["suggestedStatus"],
                "exchangeDryRunApproved": item["exchangeDryRunApproved"],
                "liveTradingApproved": item["liveTradingApproved"],
                "metrics": item["metrics"],
            }
            for item in payload["strategies"]
        ],
    }


def _mobile_exchange_connectivity() -> dict[str, Any]:
    probe = read_exchange_probe_results()
    if not probe:
        return {
            "latestProbeAt": None,
            "publicOnly": True,
            "resultCount": 0,
            "connectedExchangeCount": 0,
            "message": "No public exchange probe has been run yet.",
        }
    results = probe.get("results") if isinstance(probe.get("results"), list) else []
    return {
        "latestProbeAt": probe.get("generatedAt"),
        "publicOnly": True,
        "symbol": probe.get("symbol"),
        "timeframe": probe.get("timeframe"),
        "resultCount": len(results),
        "connectedExchangeCount": sum(1 for item in results if item.get("ok")),
        "exchanges": [
            {
                "exchange": item.get("exchange"),
                "ok": item.get("ok"),
                "latencyMs": item.get("latencyMs"),
                "apiKeyUsed": item.get("apiKeyUsed"),
                "ordersAllowed": item.get("ordersAllowed"),
            }
            for item in results
        ],
    }


def import_now() -> dict[str, Any]:
    payload = scan_quant_engine()
    append_audit(
        "quant_reports_imported",
        {
            "strategyCount": len(payload["strategies"]),
            "reportCount": len(payload["reports"]),
            "quantEnginePath": payload["quantEnginePath"],
        },
    )
    return payload


def main() -> None:
    payload = import_now()
    print(json.dumps({
        "strategyCount": len(payload["strategies"]),
        "reportCount": len(payload["reports"]),
        "quantEngineAvailable": payload["quantEngineAvailable"],
        "reportsDirAvailable": payload["reportsDirAvailable"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
