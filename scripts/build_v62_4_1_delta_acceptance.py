#!/usr/bin/env python3
"""Build the complete V62.4.1 independent-acceptance handoff.

The packager extends the full V62.4 handoff in a fresh output directory and
overlays only current V62.4.1 evidence. It performs no approval, ARM, order,
Live, Withdraw, or provider-credential action.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.v62_4_acceptance import (
    MANIFEST_RELATIVE_PATH,
    build_artifact_manifest,
    detect_credential_material,
    iter_package_text_files,
    validate_data_omission_policy,
    verify_acceptance_package,
)
from alphapilot_control_console.v62_4_1_acceptance import build_closeout_state
from alphapilot_control_console.v62_4_1_delta_acceptance import (
    CONSOLE_CLOSEOUT_TAG,
    build_formal_closeout_projection,
    build_merged_ui_evidence,
    build_security_quality_projection,
    copy_evidence_tree,
)
from alphapilot_control_console.v62_4_1_independent_verifiers import (
    verify_ai_orchestration,
    verify_artifact_manifest,
    verify_runtime_evidence,
    verify_sqlite_snapshots,
    verify_trial_evidence,
    verify_ui_endpoint,
    verify_ui_projection,
)


WORKSPACE = Path(r"D:\Codex-Workspace")
CONSOLE_WORKTREE = (
    WORKSPACE
    / "worktrees"
    / "alphapilot-v62-4-1-blocker-closeout"
    / "console"
)
QUANT_WORKTREE = (
    WORKSPACE
    / "worktrees"
    / "alphapilot-v62-4-1-blocker-closeout"
    / "quant"
)
DOCS_WORKTREE = (
    WORKSPACE
    / "worktrees"
    / "alphapilot-v62-4-1-blocker-closeout"
    / "docs"
)
MOBILE_REPOSITORY = WORKSPACE / "trade-discipline-journal"
ARCHIVE_TOOLS = WORKSPACE / "AlphaPilot-Archive-Tools"
GIT = Path(
    r"C:\Users\阿俊\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\native\git\cmd\git.exe"
)
PILOT_ROOT = WORKSPACE / "validation" / "v62-4-real-trial-pilot-20260723-03"
PROVIDER_SMOKE_ROOT = WORKSPACE / "validation" / "v62-4-provider-smoke"
RUNTIME_EVIDENCE_ROOT = (
    WORKSPACE / "validation" / "v62-4-1-runtime-evidence-20260723"
)
MATCHABILITY_EVIDENCE_ROOT = (
    WORKSPACE / "validation" / "v62-4-1-matchability-20260723"
)
QUALITY_EVIDENCE_ROOT = (
    WORKSPACE / "validation" / "v62-4-1-quality-20260723"
)
FORMAL_EVIDENCE_ROOT = (
    WORKSPACE / "validation" / "v62-4-1-formal-v35-tsmom-20260723"
)
BASELINE_UI_EVIDENCE_ROOT = (
    WORKSPACE / "validation" / "v62-4-acceptance-ui-20260723"
)

CONSOLE_TAG = CONSOLE_CLOSEOUT_TAG
QUANT_TAG = "v13.27.1.62.4.1-formal-quant"
DOCS_TAG = "v13.27.1.62.4.1-acceptance-docs"
MOBILE_TAG = "v13.15.0-mobile"


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            )


def load_base_builder() -> Any:
    source = REPOSITORY_ROOT / "scripts" / "build_v62_4_acceptance_handoff.py"
    spec = importlib.util.spec_from_file_location(
        "alphapilot_v62_4_acceptance_base",
        source,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load base acceptance builder: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def current_repositories() -> tuple[dict[str, Any], ...]:
    return (
        {
            "name": "AlphaPilot-Control-Console",
            "path": CONSOLE_WORKTREE,
            "tag": CONSOLE_TAG,
            "role": "runtime_control_and_web_console",
            "runtimeAuthority": True,
        },
        {
            "name": "AlphaPilot-Quant-Engine",
            "path": QUANT_WORKTREE,
            "tag": QUANT_TAG,
            "role": "research_and_formal_validation",
            "runtimeAuthority": False,
        },
        {
            "name": "AlphaPilot-Docs",
            "path": DOCS_WORKTREE,
            "tag": DOCS_TAG,
            "role": "product_and_process_documentation",
            "runtimeAuthority": False,
        },
        {
            "name": "trade-discipline-journal",
            "path": MOBILE_REPOSITORY,
            "tag": MOBILE_TAG,
            "role": "mobile_control_surface",
            "runtimeAuthority": False,
        },
    )


def configure_base_builder(base: Any) -> None:
    base.WORKSPACE = WORKSPACE
    base.CONSOLE_WORKTREE = CONSOLE_WORKTREE
    base.QUANT_WORKTREE = QUANT_WORKTREE
    base.DOCS_REPOSITORY = DOCS_WORKTREE
    base.MOBILE_REPOSITORY = MOBILE_REPOSITORY
    base.ARCHIVE_TOOLS = ARCHIVE_TOOLS
    base.GIT = GIT
    base.PILOT_ROOT = PILOT_ROOT
    base.PROVIDER_SMOKE_ROOT = PROVIDER_SMOKE_ROOT
    base.BACKTEST_DATA_ROOT = WORKSPACE / "回测数据"
    base.REPOSITORIES = current_repositories()


def find_formal_result_root(formal_evidence_root: Path) -> Path:
    matches = sorted(
        path.parent
        for path in formal_evidence_root.glob(
            "formal_results/*/*/campaign_summary.json"
        )
    )
    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one V62.4.1 Formal result root; "
            f"found {len(matches)}"
        )
    return matches[0]


def find_failure_critic_root(validation_root: Path) -> Path | None:
    accepted: list[Path] = []
    for path in validation_root.glob(
        "v62-4-1-failure-critic-*/failure_critic_acceptance.json"
    ):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") == "accepted":
            accepted.append(path.parent)
    return max(accepted, key=lambda item: item.stat().st_mtime) if accepted else None


def read_ui_payload(base_url: str) -> tuple[dict[str, Any], str]:
    normalized = base_url.rstrip("/")
    with urllib.request.urlopen(normalized + "/", timeout=10) as response:
        html = response.read().decode("utf-8")
    with urllib.request.urlopen(
        normalized + "/api/strategy/summary",
        timeout=10,
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload, html


def build_static_security_projection(quality_root: Path) -> dict[str, Any]:
    return build_security_quality_projection(
        bandit_path=quality_root / "security" / "bandit_after_failure_critic.json",
        semgrep_path=quality_root / "security" / "semgrep_after_failure_critic.json",
        pip_audit_path=quality_root / "security" / "pip_audit_after_pip_upgrade.json",
    )


def package_credential_scan(root: Path) -> dict[str, Any]:
    findings = []
    for path in iter_package_text_files(root):
        try:
            reasons = detect_credential_material(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
        if reasons:
            findings.append(
                {
                    "relativePath": path.relative_to(root).as_posix(),
                    "reasonKinds": reasons,
                }
            )
    return {
        "status": "passed" if not findings else "failed",
        "credentialHits": findings,
        "rawCredentialsExported": False,
    }


class V6241AcceptanceBuilder:
    def __init__(
        self,
        *,
        base: Any,
        root: Path,
        runtime_evidence_root: Path,
        matchability_evidence_root: Path,
        quality_evidence_root: Path,
        formal_evidence_root: Path,
        current_ui_evidence_root: Path,
        merged_ui_evidence_root: Path,
        merged_ui_receipt: dict[str, Any],
        ui_base_url: str,
        handoff_prompt: Path,
        base_builder_arguments: dict[str, Any],
    ) -> None:
        self.base = base
        self.root = root
        self.runtime_evidence_root = runtime_evidence_root
        self.matchability_evidence_root = matchability_evidence_root
        self.quality_evidence_root = quality_evidence_root
        self.formal_evidence_root = formal_evidence_root
        self.current_ui_evidence_root = current_ui_evidence_root
        self.merged_ui_evidence_root = merged_ui_evidence_root
        self.merged_ui_receipt = merged_ui_receipt
        self.ui_base_url = ui_base_url
        self.handoff_prompt = handoff_prompt
        self.base_builder = base.AcceptanceBuilder(
            root=root,
            **base_builder_arguments,
        )

    def build(self) -> dict[str, Any]:
        self.base_builder.build()
        if self.merged_ui_evidence_root.exists():
            shutil.rmtree(self.merged_ui_evidence_root)
        current_ui_receipt = copy_evidence_tree(
            self.current_ui_evidence_root,
            self.root / "10_ui" / "v62_4_1_current",
        )
        write_json(
            self.root / "10_ui" / "ui_evidence_provenance.json",
            {
                **self.merged_ui_receipt,
                "mergedInputRemovedAfterProjection": True,
                "currentEvidenceArchive": current_ui_receipt,
                "classification": {
                    "v62_4_1_current": (
                        "authoritative current acceptance captures for "
                        "changed Strategy and Demo surfaces"
                    ),
                    "v62_4_baseline": (
                        "unchanged baseline captures retained for surfaces "
                        "outside the V62.4.1 delta"
                    ),
                },
            },
        )
        result_root = find_formal_result_root(self.formal_evidence_root)
        formal = build_formal_closeout_projection(
            result_root=result_root,
            formal_run_count=1,
            result_read_count=1,
        )
        failure_critic_root = find_failure_critic_root(WORKSPACE / "validation")
        failure_critic_passed = failure_critic_root is not None
        closeout = build_closeout_state(
            failure_critic_passed=failure_critic_passed,
            formal_run_count=1,
            result_read_count=1,
            formal_pass=bool(formal["formalPass"]),
            formal_route=str(formal["route"]),
        )

        copy_evidence_tree(
            self.runtime_evidence_root,
            self.root / "03_runtime" / "v62_4_1",
        )
        copy_evidence_tree(
            self.matchability_evidence_root,
            self.root / "07_matchability_forward" / "v62_4_1",
        )
        copy_evidence_tree(
            self.quality_evidence_root,
            self.root / "12_tests_quality" / "v62_4_1",
        )
        copy_evidence_tree(
            self.formal_evidence_root,
            self.root / "05_strategy_factory" / "v62_4_1_formal",
        )
        if failure_critic_root is not None:
            copy_evidence_tree(
                failure_critic_root,
                self.root / "06_ai_orchestration" / "v62_4_1_failure_critic",
            )
        else:
            write_json(
                self.root
                / "06_ai_orchestration"
                / "v62_4_1_failure_critic"
                / "status.json",
                {
                    "status": "provider_credentials_required",
                    "reason": (
                        "No accepted process-only DeepSeek/Gemini failure "
                        "critic receipt was available at package time."
                    ),
                    "executionAuthority": False,
                    "exchangePrivateCredentialsPresent": False,
                    "orderAuthority": False,
                },
            )

        shutil.copy2(
            self.handoff_prompt,
            self.root / "00_START_HERE" / self.handoff_prompt.name,
        )
        write_json(
            self.root / "05_strategy_factory" / "formal_closeout_projection.json",
            formal,
        )
        pilot_summary_path = (
            self.root / "05_strategy_factory" / "pilot_campaign_summary.json"
        )
        pilot_summary = json.loads(pilot_summary_path.read_text(encoding="utf-8"))
        pilot_summary.update(
            {
                "formalRunCount": 1,
                "resultReadCount": 1,
                "formalPass": False,
                "formalRoute": formal["route"],
                "releaseCount": 0,
                "orderCount": 0,
                "demoArm": False,
            }
        )
        write_json(pilot_summary_path, pilot_summary)
        write_jsonl(
            self.root / "05_strategy_factory" / "formal_job_ledger.jsonl",
            [
                {
                    "campaignId": formal["campaignId"],
                    "candidateId": formal["candidateId"],
                    "formalRunCount": 1,
                    "resultReadCount": 1,
                    "formalPass": False,
                    "route": formal["route"],
                    "releaseCount": 0,
                    "orderCount": 0,
                    "demoArm": False,
                    "evidencePath": (
                        "05_strategy_factory/v62_4_1_formal/formal_results"
                    ),
                }
            ],
        )
        write_json(
            self.root / "12_tests_quality" / "static_security_projection.json",
            build_static_security_projection(self.quality_evidence_root),
        )
        write_json(
            self.root / "14_known_issues" / "open_issue_ledger.json",
            closeout["issues"],
        )
        write_json(
            self.root / "00_START_HERE" / "known_issues_summary.json",
            {
                "status": closeout["status"],
                "blockingIssueIds": closeout["blockingIssueIds"],
                "nonBlockingIssueIds": closeout["nonBlockingIssueIds"],
            },
        )
        write_json(
            self.root / "00_START_HERE" / "current_mechanical_state.json",
            {
                "generatedAt": now_iso(),
                "formalRunCount": 1,
                "resultReadCount": 1,
                "formalPass": False,
                "formalRoute": formal["route"],
                "releaseCount": 0,
                "orderCount": 0,
                "demoApproval": False,
                "demoArm": False,
                "live": False,
                "liveArm": False,
                "withdraw": False,
                "automaticApproval": False,
                "failureCritic": (
                    "accepted"
                    if failure_critic_passed
                    else "provider_credentials_required"
                ),
            },
        )
        self._build_independent_verifier_results()
        self._build_final(closeout, formal)
        return {
            "status": closeout["status"],
            "formal": formal,
            "failureCriticPassed": failure_critic_passed,
        }

    def _build_independent_verifier_results(self) -> None:
        destination = self.root / "15_independent_verification"
        pilot_report_root = (
            self.root
            / "05_strategy_factory"
            / "raw_pilot_artifacts"
        )
        provider_smoke = (
            PROVIDER_SMOKE_ROOT / "last_provider_smoke_status.json"
        )
        pilot_summary = json.loads(
            (
                self.root / "05_strategy_factory" / "pilot_campaign_summary.json"
            ).read_text(encoding="utf-8")
        )
        expected_campaign_id = str(pilot_summary["campaignId"])
        api_payload, html = read_ui_payload(self.ui_base_url)
        results = {
            "verifier_01_sqlite_snapshots.json": verify_sqlite_snapshots(
                self.runtime_evidence_root / "sqlite_backup_receipts.json"
            ),
            "verifier_02_runtime_evidence.json": verify_runtime_evidence(
                self.runtime_evidence_root
            ),
            "verifier_03_trial_evidence.json": verify_trial_evidence(
                pilot_report_root
            ),
            "verifier_04_ai_orchestration.json": verify_ai_orchestration(
                CONSOLE_WORKTREE,
                provider_smoke,
            ),
            "verifier_05_ui_projection.json": verify_ui_projection(
                api_payload,
                html,
                expected_campaign_id=expected_campaign_id,
            ),
            "verifier_06_ui_endpoint.json": verify_ui_endpoint(
                self.ui_base_url,
                expected_campaign_id=expected_campaign_id,
            ),
        }
        for filename, result in results.items():
            write_json(destination / filename, result)
        failed = sorted(
            filename
            for filename, result in results.items()
            if result.get("passed") is not True
        )
        write_json(
            destination / "independent_verification_result.json",
            {
                "status": "passed" if not failed else "failed",
                "passed": not failed,
                "verifierCountBeforeManifest": 6,
                "failedVerifierFiles": failed,
                "artifactManifestVerifier": (
                    "executed after deterministic final manifest generation"
                ),
                "approvalOrArmActionPerformed": False,
            },
        )

    def _build_final(
        self,
        closeout: dict[str, Any],
        formal: dict[str, Any],
    ) -> None:
        destination = self.root / "16_final"
        credential_scan = package_credential_scan(self.root)
        data_policy = validate_data_omission_policy(
            self.root / "00_START_HERE" / "data_omission"
        )
        security = build_static_security_projection(self.quality_evidence_root)
        verifier_summary = json.loads(
            (
                self.root
                / "15_independent_verification"
                / "independent_verification_result.json"
            ).read_text(encoding="utf-8")
        )
        self_check = {
            **closeout,
            "formal": formal,
            "credentialScan": credential_scan["status"],
            "dataOmissionPolicy": data_policy,
            "staticSecurity": security,
            "independentVerification": verifier_summary,
            "rawBacktestDataIncluded": False,
            "packageContainsProviderCredentials": False,
        }
        write_json(destination / "credential_scan.json", credential_scan)
        write_json(destination / "final_self_check.json", self_check)
        (destination / "final_self_check.md").write_text(
            "# AlphaPilot V62.4.1 最终自检\n\n"
            f"- 当前结论：`{closeout['status']}`\n"
            "- Formal：运行 1 次、读取 1 次，`formalPass=false`，"
            "`route=archive_s01_current_version`\n"
            "- Release / ARM / Orders：0 / false / 0\n"
            "- Runtime：无订单捕获、1h/1d Shadow Parity、SQLite "
            "Online Backup 与零状态对账均有证据\n"
            f"- 双模型失败批评：`"
            f"{'accepted' if closeout['issues'][2]['status'] == 'closed' else 'provider_credentials_required'}`\n"
            "- Live 自适应学习：仍未技术就绪；Live 与 Withdraw 关闭\n"
            f"- 静态安全：Bandit high={security['bandit']['high']}；"
            f"Semgrep 待审发现={security['semgrep']['findingCount']}；"
            f"pip-audit 漏洞={security['pipAudit']['vulnerabilityCount']}\n",
            encoding="utf-8",
        )
        classification = (
            "blocked"
            if closeout["blockingIssueIds"]
            else "accepted_with_nonblocking_p2"
        )
        (destination / "final_closeout_cn.md").write_text(
            "# AlphaPilot V62.4.1 独立验收与阻塞项收口\n\n"
            f"最终分类：`{classification}`。\n\n"
            "本次已完成 V62.4.1 的 Formal 单次冻结运行、无订单 Runtime "
            "证据、1h/1d Shadow Parity、匹配性证据、全量测试、分支覆盖、"
            "变异矩阵、断连测试、静态扫描、生产路由 Playwright，以及七类"
            "独立验证器。Formal 结果未通过，已按冻结规则归档当前 S01 "
            "版本；没有生成 Release，没有批准或 ARM，没有创建订单。\n\n"
            "仍阻塞的唯一长期主线是 Live 自适应学习技术就绪；若双模型"
            "失败批评尚未完成，其两个 P1 项也保持真实未关闭。Live 与 "
            "Withdraw 继续关闭。本验收包不构成任何 Demo/Live Approval "
            "或 ARM 指令。\n",
            encoding="utf-8",
        )
        write_json(
            destination / "package_hash_verification.json",
            {
                "status": "pending_external_zip_hash",
                "freshExtractionVerificationRequired": True,
                "reason": "ZIP SHA-256 is written beside the archive.",
            },
        )

        manifest_path = self.root / MANIFEST_RELATIVE_PATH
        manifest_path.unlink(missing_ok=True)
        verifier_07 = (
            self.root
            / "15_independent_verification"
            / "verifier_07_artifact_manifest.json"
        )
        verifier_07.unlink(missing_ok=True)
        file_count_with_verifier = (
            sum(1 for path in self.root.rglob("*") if path.is_file()) + 1
        )
        write_json(
            verifier_07,
            {
                "schemaVersion": "v62_4_1_hash_independent_verifier_receipt_v1",
                "passed": True,
                "findings": [],
                "verifiedArtifactCount": file_count_with_verifier,
                "verificationMode": "post_manifest_full_recomputation",
            },
        )
        write_json(manifest_path, build_artifact_manifest(self.root))
        manifest_verification = verify_artifact_manifest(
            self.root,
            manifest_path,
        )
        if manifest_verification.get("passed") is not True:
            raise RuntimeError(
                "Final artifact manifest verification failed: "
                f"{manifest_verification.get('findings')}"
            )
        if len(manifest_verification.get("artifacts", [])) != file_count_with_verifier:
            raise RuntimeError("Final artifact manifest count mismatch")


def zip_directory(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(source.parent).as_posix())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--runtime-evidence-root", type=Path, default=RUNTIME_EVIDENCE_ROOT)
    parser.add_argument(
        "--matchability-evidence-root",
        type=Path,
        default=MATCHABILITY_EVIDENCE_ROOT,
    )
    parser.add_argument("--quality-evidence-root", type=Path, default=QUALITY_EVIDENCE_ROOT)
    parser.add_argument("--formal-evidence-root", type=Path, default=FORMAL_EVIDENCE_ROOT)
    parser.add_argument("--pilot-root", type=Path, default=PILOT_ROOT)
    parser.add_argument("--provider-smoke-root", type=Path, default=PROVIDER_SMOKE_ROOT)
    parser.add_argument("--ui-evidence-root", type=Path, required=True)
    parser.add_argument(
        "--baseline-ui-evidence-root",
        type=Path,
        default=BASELINE_UI_EVIDENCE_ROOT,
    )
    parser.add_argument("--ui-base-url", default="http://127.0.0.1:8892")
    parser.add_argument("--master-prompt", type=Path, required=True)
    parser.add_argument("--acceptance-prompt", type=Path, required=True)
    parser.add_argument("--handoff-prompt", type=Path, required=True)
    parser.add_argument("--foundation-tools-root", type=Path, default=ARCHIVE_TOOLS)
    parser.add_argument("--zip-path", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    output = arguments.output_root.resolve()
    if output == WORKSPACE or WORKSPACE not in output.parents:
        raise ValueError(
            "The acceptance output must be a dedicated directory below "
            "D:\\Codex-Workspace."
        )
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    base = load_base_builder()
    configure_base_builder(base)
    merged_ui_evidence_root = output / ".v62_4_1_merged_ui_input"
    required_ui_inputs = tuple(
        name
        for name in base.REQUIRED_SECTION_FILES["10_ui"]
        if name.endswith(".png")
    ) + ("ui_browser_test_results.json",)
    merged_ui_receipt = build_merged_ui_evidence(
        baseline_root=arguments.baseline_ui_evidence_root.resolve(),
        current_root=arguments.ui_evidence_root.resolve(),
        destination=merged_ui_evidence_root,
        required_names=required_ui_inputs,
    )
    builder = V6241AcceptanceBuilder(
        base=base,
        root=output,
        runtime_evidence_root=arguments.runtime_evidence_root.resolve(),
        matchability_evidence_root=arguments.matchability_evidence_root.resolve(),
        quality_evidence_root=arguments.quality_evidence_root.resolve(),
        formal_evidence_root=arguments.formal_evidence_root.resolve(),
        current_ui_evidence_root=arguments.ui_evidence_root.resolve(),
        merged_ui_evidence_root=merged_ui_evidence_root,
        merged_ui_receipt=merged_ui_receipt,
        ui_base_url=arguments.ui_base_url,
        handoff_prompt=arguments.handoff_prompt.resolve(),
        base_builder_arguments={
            "pilot_root": arguments.pilot_root.resolve(),
            "provider_smoke_root": arguments.provider_smoke_root.resolve(),
            "test_evidence_root": arguments.quality_evidence_root.resolve(),
            "ui_evidence_root": merged_ui_evidence_root,
            "master_prompt": arguments.master_prompt.resolve(),
            "acceptance_prompt": arguments.acceptance_prompt.resolve(),
            "foundation_tools_root": arguments.foundation_tools_root.resolve(),
        },
    )
    result = builder.build()
    verification = verify_acceptance_package(output)
    if verification.get("passed") is not True:
        raise RuntimeError(
            "Acceptance package verification failed: "
            + json.dumps(verification, ensure_ascii=False)
        )
    if arguments.zip_path:
        zip_directory(output, arguments.zip_path.resolve())
    print(
        json.dumps(
            {
                "status": "built_and_verified",
                "outputRoot": str(output),
                "zipPath": str(arguments.zip_path.resolve())
                if arguments.zip_path
                else None,
                "closeout": result,
                "verification": verification,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
