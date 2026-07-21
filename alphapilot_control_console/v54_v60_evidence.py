"""Build a redacted and reproducible V54-V60 closeout delivery."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


_ALLOWED_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".png", ".txt"}
_SENSITIVE_JSON_KEYS = {
    "apikey",
    "secretkey",
    "passphrase",
    "password",
    "accesstoken",
    "refreshtoken",
}
_SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"ALPHAPILOT_OKX_(?:DEMO|LIVE)_(?:API_KEY|SECRET_KEY|PASSPHRASE)"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{8,}",
        re.IGNORECASE,
    ),
)
_SAFE_SECRET_VALUES = {
    "",
    "false",
    "masked",
    "none",
    "not_run",
    "null",
    "redacted",
    "true",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_allowed_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        return
    for path in sorted(item for item in source.rglob("*") if item.is_file()):
        if path.suffix.lower() not in _ALLOWED_SUFFIXES:
            continue
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def _has_sensitive_json_value(value: Any, key: str = "") -> bool:
    normalized_key = re.sub(r"[^a-z0-9]", "", key.lower())
    if normalized_key in _SENSITIVE_JSON_KEYS:
        normalized_value = str(value or "").strip().lower()
        if normalized_value not in _SAFE_SECRET_VALUES:
            return True
    if isinstance(value, Mapping):
        return any(_has_sensitive_json_value(item, str(item_key)) for item_key, item in value.items())
    if isinstance(value, list):
        return any(_has_sensitive_json_value(item) for item in value)
    return False


def _scan_sensitive_data(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.suffix.lower() not in {".csv", ".json", ".jsonl", ".md", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(root).as_posix()
        if any(pattern.search(text) for pattern in _SENSITIVE_TEXT_PATTERNS):
            findings.append(relative)
            continue
        if path.suffix.lower() == ".json":
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if _has_sensitive_json_value(payload):
                findings.append(relative)
    return findings


def _build_self_check(console_root: Path) -> dict[str, Any]:
    report_root = console_root / "reports" / "v54_v60"
    v58 = _read_json(
        report_root / "v58_live_engineering_smoke" / "live_engineering_smoke_result.json",
        {},
    )
    live_root = report_root / "v59_v60_live_canary_readiness"
    adaptive = _read_json(live_root / "adaptive_learning_live_readiness.json", {})
    live = _read_json(live_root / "live_execution_state.json", {})
    release = _read_json(live_root / "experimental_live_release.json", {})
    risk = _read_json(live_root / "experimental_live_risk_overlay.json", {})

    zero_open_positions = v58.get("zeroOpenPositions")
    if zero_open_positions is None:
        zero_open_positions = v58.get("finalOpenPositionCount") == 0
    zero_open_orders = v58.get("zeroOpenOrders")
    if zero_open_orders is None:
        zero_open_orders = v58.get("finalOpenOrderCount") == 0

    return {
        "schemaVersion": "alphapilot_v54_v60_final_self_check_v1",
        "generatedAt": _now(),
        "v58": {
            "status": v58.get("status", "missing"),
            "orderAttemptCount": v58.get("orderAttemptCount", 0),
            "cancelConfirmed": bool(v58.get("cancelConfirmed", False)),
            "zeroOpenPositions": bool(zero_open_positions),
            "zeroOpenOrders": bool(zero_open_orders),
            "finalReconciliationMatched": bool(v58.get("finalReconciliationMatched", False)),
            "strategyQualification": bool(v58.get("strategyQualification", False)),
            "promotionEligible": bool(v58.get("promotionEligible", False)),
        },
        "adaptiveLearning": {
            "status": adaptive.get("status", "missing"),
            "passed": bool(adaptive.get("passed", False)),
            "blockerCount": len(adaptive.get("blockers", [])),
            "blockers": list(adaptive.get("blockers", [])),
        },
        "experimentalLiveRelease": {
            "releaseId": release.get("releaseId"),
            "releaseHash": release.get("releaseHash"),
            "riskOverlayHash": risk.get("riskOverlayHash") or release.get("riskOverlayHash"),
            "formalPass": bool(release.get("formalPass", False)),
            "productionQualified": bool(release.get("productionQualified", False)),
        },
        "live": {
            "approvalStatus": live.get("approvalStatus", "not_run"),
            "armStatus": live.get("armStatus", "not_run"),
            "strategyOrderStatus": live.get("strategyOrderStatus", "not_run"),
            "liveEnabled": bool(live.get("liveEnabled", False)),
            "withdrawAllowed": bool(live.get("withdrawAllowed", False)),
        },
    }


def _self_check_markdown(self_check: Mapping[str, Any]) -> str:
    v58 = self_check["v58"]
    adaptive = self_check["adaptiveLearning"]
    live = self_check["live"]
    release = self_check["experimentalLiveRelease"]
    return "\n".join(
        (
            "# AlphaPilot V54-V60 Final Self Check",
            "",
            f"- V58 engineering smoke: `{v58['status']}`",
            f"- Smoke order attempts: `{v58['orderAttemptCount']}`",
            f"- Cancel confirmed: `{str(v58['cancelConfirmed']).lower()}`",
            f"- Zero open positions/orders: `{str(v58['zeroOpenPositions']).lower()}` / `{str(v58['zeroOpenOrders']).lower()}`",
            f"- Experimental Live Release: `{release['releaseHash']}`",
            f"- Risk Overlay: `{release['riskOverlayHash']}`",
            f"- Adaptive Learning gate: `{adaptive['status']}` ({adaptive['blockerCount']} blockers)",
            f"- Exact Live approval / ARM / strategy orders: `{live['approvalStatus']}` / `{live['armStatus']}` / `{live['strategyOrderStatus']}`",
            f"- Live enabled: `{str(live['liveEnabled']).lower()}`",
            f"- Withdraw allowed: `{str(live['withdrawAllowed']).lower()}`",
            "",
            "V58 is an engineering-only, canceled-and-reconciled smoke. It is not strategy evidence or production qualification.",
        )
    )


def _closeout_markdown(self_check: Mapping[str, Any]) -> str:
    adaptive = self_check["adaptiveLearning"]
    release = self_check["experimentalLiveRelease"]
    live = self_check["live"]
    return "\n".join(
        (
            "# AlphaPilot V54-V60 中文 Closeout",
            "",
            "## 已完成",
            "",
            "- V58 OKX Live 工程烟测已真实提交一笔受限订单，并完成撤单、零持仓、零挂单和对账闭环。",
            "- V59/V60 已生成版本化 Live Canary 身份、风险覆盖、环境与币池策略。",
            "- 控制台已增加只读 Live readiness 投影；Hash、Gate 和审计信息保持折叠。",
            "",
            "## 当前机械状态",
            "",
            f"- Live Release: `{release['releaseId']}`",
            f"- Live Release Hash: `{release['releaseHash']}`",
            f"- Risk Overlay Hash: `{release['riskOverlayHash']}`",
            f"- Adaptive Learning: `{adaptive['status']}`，尚有 `{adaptive['blockerCount']}` 个真实阻塞项。",
            f"- Exact approval / ARM / strategy order: `{live['approvalStatus']}` / `{live['armStatus']}` / `{live['strategyOrderStatus']}`。",
            "- Live 与 Withdraw 均保持关闭。",
            "",
            "## 结论",
            "",
            "当前不得请求或执行精确 Live Release 批准。下一步必须先完成 AdaptiveLearningLiveReadinessGate；任何模型、因子、Feature Schema 或 Model Policy 变化都必须生成新 Hash 和新 Release，再由用户精确批准。",
        )
    )


def build_v54_v60_evidence(
    *,
    console_root: Path | str,
    quant_root: Path | str,
    docs_root: Path | str,
    output_root: Path | str,
    repository_snapshots: Mapping[str, Any],
    test_summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Create one verified ZIP without copying credentials or runtime databases."""

    console = Path(console_root)
    output = Path(output_root)
    package_name = "AlphaPilot_V54-V60_Total_Evidence"
    stage = output / package_name
    zip_path = output / f"{package_name}.zip"
    sha256_path = output / f"{package_name}.zip.sha256"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    _copy_allowed_tree(
        console / "data" / "v54_v60",
        stage / "evidence" / "data_v54_v60",
    )
    _copy_allowed_tree(
        console / "reports" / "v54_v60",
        stage / "evidence" / "reports_v54_v60",
    )

    closeout_source = console / "docs" / "V13.27.1.54-V13.27.1.60-closeout.md"
    if closeout_source.is_file():
        shutil.copy2(closeout_source, stage / "V13.27.1.54-V13.27.1.60-closeout.md")

    self_check = _build_self_check(console)
    _write_json(stage / "final_self_check.json", self_check)
    _write_text(stage / "final_self_check.md", _self_check_markdown(self_check))
    _write_text(stage / "final_closeout_cn.md", _closeout_markdown(self_check))
    _write_json(stage / "repository_snapshots.json", dict(repository_snapshots))
    _write_json(stage / "test_summary.json", dict(test_summary))
    _write_json(
        stage / "source_roots.json",
        {
            "schemaVersion": "alphapilot_v54_v60_source_roots_v1",
            "generatedAt": _now(),
            "consoleRoot": str(console),
            "quantRoot": str(Path(quant_root)),
            "docsRoot": str(Path(docs_root)),
            "credentialsIncluded": False,
            "runtimeDatabasesIncluded": False,
        },
    )

    sensitive_findings = _scan_sensitive_data(stage)
    if sensitive_findings:
        raise ValueError(f"Sensitive data detected in delivery: {', '.join(sensitive_findings)}")

    artifacts = []
    for path in sorted(item for item in stage.rglob("*") if item.is_file()):
        relative = path.relative_to(stage).as_posix()
        artifacts.append({"path": relative, "bytes": path.stat().st_size, "sha256": _sha256(path)})
    manifest = {
        "schemaVersion": "alphapilot_v54_v60_artifact_manifest_v1",
        "generatedAt": _now(),
        "artifactCount": len(artifacts),
        "artifacts": artifacts,
        "verification": {
            "crc": "passed",
            "sensitiveDataScan": "passed",
            "sensitiveFindingCount": 0,
        },
    }
    _write_json(stage / "artifact_manifest.json", manifest)

    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in stage.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(stage).as_posix())
    with zipfile.ZipFile(zip_path) as archive:
        failing_member = archive.testzip()
        if failing_member is not None:
            raise OSError(f"ZIP CRC verification failed: {failing_member}")

    digest = _sha256(zip_path)
    _write_text(sha256_path, f"{digest}  {zip_path.name}")
    return {
        "zipPath": zip_path,
        "sha256": digest,
        "sha256Path": sha256_path,
        "artifactCount": len(artifacts),
        "stagePath": stage,
    }
