"""Truth-preserving helpers for the V62.4.1 acceptance delta.

The functions in this module only project and package existing evidence. They
must not approve releases, ARM a runtime, submit orders, or read credentials.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


CONSOLE_CLOSEOUT_TAG = "v13.27.1.62.4.1-final-console"

CURRENT_UI_EVIDENCE_MAP = {
    "desktop-1440-strategy.png": "strategy_factory_desktop.png",
    "mobile-390-strategy.png": "strategy_factory_mobile_390.png",
    "desktop-1440-demo.png": "demo_desktop.png",
    "mobile-390-demo.png": "demo_mobile_390.png",
    "playwright_acceptance.json": "ui_browser_test_results.json",
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _error_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, int):
        return value
    return 0


def _manifest_entry(path: Path, root: Path) -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "relativePath": path.relative_to(root).as_posix(),
        "sizeBytes": path.stat().st_size,
        "sha256": digest,
    }


def copy_evidence_tree(source: Path, destination: Path) -> dict[str, Any]:
    """Replace a destination with a byte-for-byte evidence tree copy."""

    source = source.resolve()
    destination = destination.resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Evidence source does not exist: {source}")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    files = sorted(path for path in destination.rglob("*") if path.is_file())
    return {
        "source": str(source),
        "destination": str(destination),
        "fileCount": len(files),
        "artifacts": [_manifest_entry(path, destination) for path in files],
    }


def build_merged_ui_evidence(
    *,
    baseline_root: Path,
    current_root: Path,
    destination: Path,
    required_names: tuple[str, ...],
) -> dict[str, Any]:
    """Merge unchanged baseline surfaces with current acceptance captures."""

    baseline_root = baseline_root.resolve()
    current_root = current_root.resolve()
    destination = destination.resolve()
    if not baseline_root.is_dir():
        raise FileNotFoundError(
            f"Baseline UI evidence does not exist: {baseline_root}"
        )
    if not current_root.is_dir():
        raise FileNotFoundError(
            f"Current UI evidence does not exist: {current_root}"
        )
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    sources: dict[str, str] = {}
    for name in required_names:
        source = baseline_root / name
        if not source.is_file():
            raise FileNotFoundError(
                f"Required baseline UI evidence is missing: {source}"
            )
        shutil.copy2(source, destination / name)
        sources[name] = "v62_4_baseline"

    current_override_count = 0
    required = set(required_names)
    for current_name, package_name in CURRENT_UI_EVIDENCE_MAP.items():
        source = current_root / current_name
        if package_name not in required or not source.is_file():
            continue
        shutil.copy2(source, destination / package_name)
        sources[package_name] = "v62_4_1_current"
        current_override_count += 1

    current_archive = destination / "v62_4_1_current"
    shutil.copytree(current_root, current_archive)
    return {
        "baselineRoot": str(baseline_root),
        "currentRoot": str(current_root),
        "destination": str(destination),
        "requiredFileCount": len(required_names),
        "currentOverrideCount": current_override_count,
        "baselineFallbackCount": len(required_names) - current_override_count,
        "sources": sources,
    }


def _failed_gates(gate_matrix: Any) -> list[str]:
    if not isinstance(gate_matrix, dict):
        return []
    rows = gate_matrix.get("gates", gate_matrix.get("gateMatrix", []))
    if isinstance(rows, dict):
        rows = [
            {"gateId": gate_id, **(value if isinstance(value, dict) else {})}
            for gate_id, value in rows.items()
        ]
    if not isinstance(rows, list):
        return []
    return sorted(
        str(row.get("gateId") or row.get("name") or "unknown_gate")
        for row in rows
        if isinstance(row, dict)
        and row.get("passed", row.get("status") == "passed") is not True
    )


def build_formal_closeout_projection(
    *,
    result_root: Path,
    formal_run_count: int,
    result_read_count: int,
) -> dict[str, Any]:
    """Project a frozen Formal result without widening execution authority."""

    result_root = result_root.resolve()
    summary = _read_json(result_root / "campaign_summary.json")
    route = _read_json(result_root / "route_decision.json")
    gates = _read_json(result_root / "gate_matrix.json")
    failed_gate_ids = _failed_gates(gates)
    metrics = summary.get("baseMetrics", summary)
    return {
        "campaignId": summary.get("campaignId"),
        "candidateId": (
            summary.get("candidateId")
            or route.get("candidateId")
            or result_root.name
        ),
        "formalRunCount": int(formal_run_count),
        "resultReadCount": int(result_read_count),
        "formalPass": bool(summary.get("formalPass", False)),
        "route": route.get("route") or route.get("decision"),
        "failedGateCount": len(failed_gate_ids),
        "failedGateIds": failed_gate_ids,
        "metrics": {
            "profitFactor": metrics.get("profitFactor"),
            "averageNetR": metrics.get("averageNetR"),
            "maximumDrawdownR": (
                metrics.get("maximumDrawdownR")
                if metrics.get("maximumDrawdownR") is not None
                else metrics.get("maximumDrawdownPercent")
            ),
            "tradeCount": metrics.get("tradeCount"),
        },
        "releaseCount": 0,
        "orderCount": 0,
        "demoArm": False,
        "live": False,
        "liveArm": False,
        "withdraw": False,
        "automaticApproval": False,
    }


def build_security_quality_projection(
    *,
    bandit_path: Path,
    semgrep_path: Path,
    pip_audit_path: Path,
) -> dict[str, Any]:
    """Summarize static checks without hiding audit findings."""

    bandit = _read_json(bandit_path)
    semgrep = _read_json(semgrep_path)
    pip_audit = _read_json(pip_audit_path)
    totals = bandit.get("metrics", {}).get("_totals", {})
    dependencies = pip_audit.get("dependencies", [])
    vulnerability_count = sum(
        len(dependency.get("vulns", []))
        for dependency in dependencies
        if isinstance(dependency, dict)
    )
    bandit_summary = {
        "high": int(totals.get("SEVERITY.HIGH", 0)),
        "medium": int(totals.get("SEVERITY.MEDIUM", 0)),
        "low": int(totals.get("SEVERITY.LOW", 0)),
        "errors": _error_count(bandit.get("errors", [])),
    }
    semgrep_summary = {
        "findingCount": len(semgrep.get("results", [])),
        "errorCount": _error_count(semgrep.get("errors", [])),
    }
    pip_summary = {
        "dependencyCount": len(dependencies),
        "vulnerabilityCount": vulnerability_count,
    }
    blocking = (
        bandit_summary["high"]
        + bandit_summary["errors"]
        + semgrep_summary["errorCount"]
        + vulnerability_count
    )
    review = (
        bandit_summary["medium"]
        + bandit_summary["low"]
        + semgrep_summary["findingCount"]
    )
    if blocking:
        status = "failed"
    elif review:
        status = "passed_with_review_findings"
    else:
        status = "passed"
    return {
        "status": status,
        "bandit": bandit_summary,
        "semgrep": semgrep_summary,
        "pipAudit": pip_summary,
        "blockingFindingCount": blocking,
        "reviewFindingCount": review,
        "reviewPolicy": (
            "Semgrep and Bandit medium/low findings remain visible for "
            "manual triage and are not represented as zero findings."
        ),
    }
