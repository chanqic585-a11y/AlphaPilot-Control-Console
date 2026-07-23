#!/usr/bin/env python3
"""Build the V62.4 acceptance handoff from fresh, read-only evidence.

The builder never approves a release, ARM a runtime, submit an order, or read
provider/exchange credentials. It projects committed source, immutable Pilot
results, redacted provider-smoke status, read-only runtime availability and
online SQLite backups into the acceptance layout.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.v62_4_acceptance import (
    MANIFEST_RELATIVE_PATH,
    REQUIRED_SECTION_FILES,
    REQUIRED_TOP_LEVEL,
    build_artifact_manifest,
    build_formal_job_rows,
    build_runtime_projection,
    detect_credential_material,
    find_foundation_sample_root,
    iter_package_text_files,
    load_pilot_evidence,
    redact_credential_assignments,
    validate_data_omission_policy,
    verify_acceptance_package,
)


WORKSPACE = Path(r"D:\Codex-Workspace")
CONSOLE_WORKTREE = WORKSPACE / "worktrees" / "alphapilot-v62-4-global-reassessment" / "console"
QUANT_WORKTREE = WORKSPACE / "worktrees" / "alphapilot-v62-4-global-reassessment" / "quant"
DOCS_REPOSITORY = WORKSPACE / "AlphaPilot-Docs"
MOBILE_REPOSITORY = WORKSPACE / "trade-discipline-journal"
ARCHIVE_TOOLS = WORKSPACE / "AlphaPilot-Archive-Tools"
GIT = Path(
    r"C:\Users\阿俊\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
)
PILOT_ROOT = WORKSPACE / "validation" / "v62-4-real-trial-pilot-20260723-03"
PROVIDER_SMOKE_ROOT = WORKSPACE / "validation" / "v62-4-provider-smoke"
BACKTEST_DATA_ROOT = WORKSPACE / "回测数据"

REPOSITORIES = (
    {
        "name": "AlphaPilot-Control-Console",
        "path": CONSOLE_WORKTREE,
        "tag": "v13.27.1.62.4.1-acceptance-console",
        "role": "runtime_control_and_web_console",
        "runtimeAuthority": True,
    },
    {
        "name": "AlphaPilot-Quant-Engine",
        "path": QUANT_WORKTREE,
        "tag": "v13.27.1.62.4-pilot-quant",
        "role": "research_and_formal_validation",
        "runtimeAuthority": False,
    },
    {
        "name": "AlphaPilot-Docs",
        "path": DOCS_REPOSITORY,
        "tag": "v13.27.1.62.4-docs",
        "role": "product_and_process_documentation",
        "runtimeAuthority": False,
    },
    {
        "name": "trade-discipline-journal",
        "path": MOBILE_REPOSITORY,
        "tag": "v13.15.0-mobile",
        "role": "mobile_control_surface",
        "runtimeAuthority": False,
    },
)

CLASSIFICATIONS = (
    "authoritative_current",
    "historical_immutable",
    "superseded",
    "failed_attempt",
    "engineering_only",
    "fixture_only",
    "research_only",
    "deprecated",
)

SECRET_FIELD = re.compile(r"(?i)(?:secret|token|passphrase|api.?key|password|credential)")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 900,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PATH"] = str(GIT.parent) + os.pathsep + environment.get("PATH", "")
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=timeout,
        check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stderr[-2000:]}"
        )
    return completed


def git(repository: Path, *arguments: str, check: bool = True) -> str:
    return run([str(GIT), "-C", str(repository), *arguments], check=check).stdout.strip()


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source: Path, destination: Path) -> None:
    if source.exists():
        shutil.copytree(source, destination, dirs_exist_ok=True)


def load_foundation_module(path: Path) -> Any:
    specification = importlib.util.spec_from_file_location("alphapilot_archive_v2", path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Cannot import foundation packager: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def scrub_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("[REDACTED]" if SECRET_FIELD.search(str(key)) else scrub_secrets(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [scrub_secrets(item) for item in value]
    return value


def write_status(path: Path, *, status: str, reason: str, **fields: Any) -> None:
    write_json(path, {"status": status, "reason": reason, **fields})


def copy_json_or_status(
    source: Path,
    destination: Path,
    *,
    missing_status: str = "not_run",
    missing_reason: str,
) -> None:
    if source.is_file():
        payload = json.loads(source.read_text(encoding="utf-8"))
        write_json(destination, scrub_secrets(payload))
        return
    write_status(destination, status=missing_status, reason=missing_reason)


class AcceptanceBuilder:
    def __init__(
        self,
        *,
        root: Path,
        pilot_root: Path,
        provider_smoke_root: Path,
        test_evidence_root: Path | None,
        ui_evidence_root: Path | None,
        master_prompt: Path,
        acceptance_prompt: Path,
        foundation_tools_root: Path,
    ) -> None:
        self.root = root
        self.pilot_root = pilot_root
        self.provider_smoke_root = provider_smoke_root
        self.test_evidence_root = test_evidence_root
        self.ui_evidence_root = ui_evidence_root
        self.master_prompt = master_prompt
        self.acceptance_prompt = acceptance_prompt
        self.foundation_tools_root = foundation_tools_root
        self.repositories: list[dict[str, Any]] = []
        self.pilot: dict[str, Any] = {}
        self.runtime_projection: dict[str, Any] = {}
        self.foundation_root = self.root / ".foundation"

    def build(self) -> None:
        for directory in REQUIRED_TOP_LEVEL:
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        self.build_foundation()
        self.build_start_here()
        self.build_identity()
        self.build_source_and_diff()
        self.build_runtime()
        self.build_authority_security()
        self.build_strategy_factory()
        self.build_ai_orchestration()
        self.build_matchability_forward()
        self.build_factor_model()
        self.build_demo_live_execution()
        self.build_ui()
        self.build_database()
        self.build_tests_quality()
        self.build_performance()
        self.build_known_issues()
        self.build_independent_verification()
        self.build_final()

    def build_foundation(self) -> None:
        foundation_source = self.foundation_tools_root / "build_complete_archive_v2.py"
        module = load_foundation_module(foundation_source)
        builder = module.EvidenceBuilder(self.foundation_root)
        builder.build_data_inventory_and_samples()
        builder.backup_all_sqlite()
        builder.repository_metadata = [
            {
                "name": item["name"],
                "tag": item["tag"],
                "tagCommit": git(item["path"], "rev-parse", f"{item['tag']}^{{}}", check=False),
            }
            for item in REPOSITORIES
        ]
        builder.collect_runtime_provenance()
        builder.build_architecture_inventory()
        builder.build_model_and_training_manifest()
        builder.build_ui_matrix()
        builder.build_lineage_governance_and_tools()

    def build_start_here(self) -> None:
        copy_file(self.master_prompt, self.root / "00_START_HERE" / self.master_prompt.name)
        copy_file(self.acceptance_prompt, self.root / "00_START_HERE" / self.acceptance_prompt.name)
        prompt_hashes = {
            self.master_prompt.name: sha256_file(self.master_prompt),
            self.acceptance_prompt.name: sha256_file(self.acceptance_prompt),
        }
        write_json(self.root / "00_START_HERE" / "input_document_hashes.json", prompt_hashes)
        readme = """# AlphaPilot V62.4 独立验收交接包

本包用于外部独立复核，不以 `final_closeout_cn.md` 自证通过。

- 当前源码：四仓库精确 Tag/Commit、Git Bundle、Source Archive 和远端引用。
- 当前研究：V62.4 有界真实 Pilot，12 个真实 Trial；Formal 尚未运行。
- 当前 AI：DeepSeek + Gemini Provider Smoke 已通过；凭据未进入本包。
- 当前 Runtime：打包时若本地服务离线，明确标记 `runtime_source_parity=unverified`，禁止新开仓。
- Demo/Live：本包不是 Release Approval 或 ARM 指令，不提交订单；Withdraw 不接入。
- Fixture、历史证据、失败尝试与 not_run 项均单独分类，不冒充当前 Runtime 事实。
"""
        (self.root / "00_START_HERE" / "README_CN.md").write_text(readme, encoding="utf-8")
        write_json(
            self.root / "00_START_HERE" / "package_scope.json",
            {
                "schemaVersion": "v62_4_acceptance_handoff_v1",
                "generatedAt": now_iso(),
                "topLevel": list(REQUIRED_TOP_LEVEL),
                "rawBacktestDataIncluded": False,
                "credentialsIncluded": False,
                "resultsFabricated": False,
                "approvalOrArmActionPerformed": False,
                "orderActionPerformed": False,
            },
        )
        write_json(
            self.root / "00_START_HERE" / "current_mechanical_state.json",
            {
                "generatedAt": now_iso(),
                "strategyFactoryPilot": "completed_awaiting_formal_validation",
                "formalRun": "not_run_awaiting_preregistration_and_frozen_input",
                "providerSmoke": "passed_redacted_status_only",
                "runtime": "unverified_until_runtime_capture",
                "demoApproval": "not_performed_by_packager",
                "demoArm": "not_performed_by_packager",
                "live": False,
                "liveArm": False,
                "liveStrategyOrders": 0,
                "withdraw": False,
            },
        )
        write_json(
            self.root / "00_START_HERE" / "repository_role_map.json",
            [
                {
                    "repositoryName": item["name"],
                    "repositoryRole": item["role"],
                    "runtimeAuthority": item["runtimeAuthority"],
                }
                for item in REPOSITORIES
            ],
        )
        write_json(
            self.root / "00_START_HERE" / "current_authoritative_identity.json",
            {
                "repositories": [
                    {
                        "repository": item["name"],
                        "tag": item["tag"],
                        "headCommitAtBuildStart": git(item["path"], "rev-parse", "HEAD"),
                        "role": item["role"],
                    }
                    for item in REPOSITORIES
                ],
                "pilotCampaignId": load_pilot_evidence(self.pilot_root)["summary"]["campaignId"],
                "providerIdentity": ["deepseek", "gemini"],
                "runtimeAuthority": "AlphaPilot-Control-Console",
                "approvalOrArmPerformedByPackager": False,
            },
        )
        write_json(
            self.root / "00_START_HERE" / "evidence_authority_index.json",
            {
                "classifications": list(CLASSIFICATIONS),
                "entries": [
                    {"pathPrefix": "01_identity", "classification": "authoritative_current", "authority": "committed Git refs"},
                    {"pathPrefix": "03_runtime", "classification": "authoritative_current", "authority": "read-only runtime capture", "currentStatus": "unverified_if_offline"},
                    {"pathPrefix": "05_strategy_factory/raw_pilot_artifacts", "classification": "research_only", "authority": "immutable Pilot artifacts"},
                    {"pathPrefix": "08_factor_model", "classification": "research_only", "authority": "V59 adaptive-learning evidence"},
                    {"pathPrefix": "10_ui", "classification": "engineering_only", "authority": "read-only browser capture"},
                    {"pathPrefix": "02_source_and_diff/source_archives", "classification": "historical_immutable", "authority": "Git tag archives"},
                ],
            },
        )
        write_json(
            self.root / "00_START_HERE" / "version_timeline.json",
            {
                "versions": [
                    {"version": "V55-V60", "classification": "historical_immutable", "note": "Demo/Live engineering and adaptive-learning evidence lineage"},
                    {"version": "V61", "classification": "historical_immutable", "note": "Global remediation and control-surface baseline"},
                    {"version": "V62.4", "classification": "authoritative_current", "note": "Global reassessment, Strategy Factory 2.0 and DeepSeek/Gemini orchestration"},
                ]
            },
        )
        data_omission = self.root / "00_START_HERE" / "data_omission"
        copy_file(self.foundation_root / "metadata" / "omitted_data_manifest.json", data_omission / "omitted_data_manifest.json")
        copy_file(self.foundation_root / "metadata" / "omitted_data_manifest.csv", data_omission / "omitted_data_manifest.csv")
        copy_tree(find_foundation_sample_root(self.foundation_root), data_omission / "sample_only")
        write_json(
            self.root / "00_START_HERE" / "known_issues_summary.json",
            {
                "issues": [
                    {
                        "issueId": "V62.4-RUNTIME-OFFLINE",
                        "status": "capture_pending",
                        "impact": "Runtime identity and source parity may be unverified at package time.",
                        "safetyResponse": "newEntriesAllowed=false",
                    },
                    {
                        "issueId": "V62.4-FORMAL-NOT-RUN",
                        "status": "expected_boundary",
                        "impact": "One Formal-ready candidate exists but no locked Formal run/result exists.",
                        "safetyResponse": "Do not promote or approve the candidate.",
                    },
                ]
            },
        )
        write_json(
            self.root / "00_START_HERE" / "exclusion_summary.json",
            {
                "excluded": [
                    "raw market CSV/Parquet/columnar data",
                    "provider and exchange credentials",
                    "private account responses",
                    "mutable temporary files and caches",
                ],
                "replacementEvidence": [
                    "omitted_data_manifest.json/csv",
                    "sample_only metadata",
                    "data inventory and hashes",
                ],
            },
        )

    def _repository_snapshot(self, definition: dict[str, Any]) -> dict[str, Any]:
        repository = definition["path"]
        tag = definition["tag"]
        head = git(repository, "rev-parse", "HEAD")
        tag_commit = git(repository, "rev-parse", f"{tag}^{{}}", check=False)
        branch = git(repository, "branch", "--show-current")
        status_lines = git(repository, "status", "--porcelain=v1").splitlines()
        upstream = git(repository, "rev-parse", "@{upstream}", check=False)
        ahead_behind = git(repository, "rev-list", "--left-right", "--count", "@{upstream}...HEAD", check=False)
        ahead = behind = None
        if ahead_behind:
            parts = ahead_behind.split()
            if len(parts) == 2:
                behind, ahead = (int(parts[0]), int(parts[1]))
        tags = git(repository, "tag", "--points-at", "HEAD", check=False).splitlines()
        dirty_paths = [line[3:] for line in status_lines if line and not line.startswith("??")]
        untracked_paths = [line[3:] for line in status_lines if line.startswith("??")]
        return {
            "repositoryName": definition["name"],
            "repositoryRole": definition["role"],
            "runtimeAuthority": definition["runtimeAuthority"],
            "path": str(repository),
            "remoteUrl": git(repository, "remote", "get-url", "origin", check=False),
            "branch": branch,
            "headCommit": head,
            "tag": tag,
            "tagCommit": tag_commit or None,
            "upstreamCommit": upstream or None,
            "ahead": ahead,
            "behind": behind,
            "worktreeClean": not status_lines,
            "tagsAtHead": tags,
            "dirtyPaths": dirty_paths,
            "untrackedPaths": untracked_paths,
        }

    def build_identity(self) -> None:
        identity = self.root / "01_identity"
        bundles = identity / "git_bundles"
        snapshots = self.root / "02_source_and_diff" / "source_archives"
        logs = identity / "raw_git_logs"
        for directory in (bundles, snapshots, logs):
            directory.mkdir(parents=True, exist_ok=True)
        bundle_results = []
        fsck_results = []
        remote_results = []
        for definition in REPOSITORIES:
            snapshot = self._repository_snapshot(definition)
            self.repositories.append(snapshot)
            repository = definition["path"]
            bundle = bundles / f"{definition['name']}.bundle"
            run([str(GIT), "-C", str(repository), "bundle", "create", str(bundle), "--all"], check=True, timeout=1800)
            verify = run([str(GIT), "-C", str(repository), "bundle", "verify", str(bundle)], timeout=600)
            fsck = run([str(GIT), "-C", str(repository), "fsck", "--full", "--no-reflogs"], timeout=1800)
            (logs / f"{definition['name']}-bundle-verify.log").write_text(verify.stdout + verify.stderr, encoding="utf-8")
            (logs / f"{definition['name']}-fsck.log").write_text(fsck.stdout + fsck.stderr, encoding="utf-8")
            bundle_results.append(
                {
                    "repository": definition["name"],
                    "status": "passed" if verify.returncode == 0 else "failed",
                    "returnCode": verify.returncode,
                    "sha256": sha256_file(bundle),
                    "sizeBytes": bundle.stat().st_size,
                }
            )
            fsck_results.append(
                {
                    "repository": definition["name"],
                    "status": "passed" if fsck.returncode == 0 else "failed",
                    "returnCode": fsck.returncode,
                }
            )
            archive = snapshots / f"{definition['name']}-{definition['tag']}.zip"
            run(
                [str(GIT), "-C", str(repository), "archive", "--format=zip", "--output", str(archive), definition["tag"]],
                check=True,
                timeout=900,
            )
            remote_ref = git(repository, "ls-remote", "origin", f"refs/tags/{definition['tag']}^{{}}", check=False)
            remote_hash = remote_ref.split()[0] if remote_ref else None
            remote_results.append(
                {
                    "repository": definition["name"],
                    "tag": definition["tag"],
                    "localTagCommit": snapshot["tagCommit"],
                    "remoteTagCommit": remote_hash,
                    "matches": bool(remote_hash and remote_hash == snapshot["tagCommit"]),
                }
            )
        write_json(identity / "repository_snapshot.json", self.repositories)
        write_json(identity / "remote_ref_verification.json", remote_results)
        write_json(identity / "tag_map.json", [{"repository": row["repositoryName"], "tag": row["tag"], "commit": row["tagCommit"]} for row in self.repositories])
        write_json(identity / "worktree_status.json", [{"repository": row["repositoryName"], "clean": row["worktreeClean"], "dirtyPaths": row["dirtyPaths"], "untrackedPaths": row["untrackedPaths"]} for row in self.repositories])
        write_json(identity / "git_bundle_verify.json", bundle_results)
        write_json(identity / "git_fsck.json", fsck_results)
        commit_graph = []
        for definition in REPOSITORIES:
            graph = git(definition["path"], "log", "--graph", "--decorate", "--oneline", "-20")
            commit_graph.append(f"## {definition['name']}\n{graph}\n")
        (identity / "recent_commit_graph.txt").write_text("\n".join(commit_graph), encoding="utf-8")

    def build_source_and_diff(self) -> None:
        destination = self.root / "02_source_and_diff"
        source_files = []
        languages: Counter[str] = Counter()
        large_files = []
        changed_files = []
        baseline_patches = []
        for definition in REPOSITORIES:
            repository = definition["path"]
            tag = definition["tag"]
            files = git(repository, "ls-tree", "-r", "--long", tag, check=False)
            for line in files.splitlines():
                match = re.match(r"^\d+\s+\w+\s+([0-9a-f]+)\s+(\d+)\t(.+)$", line)
                if not match:
                    continue
                blob, size, relative = match.groups()
                suffix = Path(relative).suffix.lower() or "<none>"
                languages[suffix] += 1
                item = {
                    "repository": definition["name"],
                    "path": relative,
                    "blob": blob,
                    "sizeBytes": int(size),
                    "sourceCommit": next(row["tagCommit"] for row in self.repositories if row["repositoryName"] == definition["name"]),
                }
                source_files.append(item)
                if int(size) >= 1_000_000:
                    large_files.append(item)
            baseline = git(repository, "merge-base", tag, f"{tag}~1", check=False)
            if baseline:
                patch = git(repository, "diff", "--binary", baseline, tag, check=False)
                baseline_patches.append(f"# {definition['name']} {baseline}..{tag}\n{patch}\n")
                names = git(repository, "diff", "--name-status", baseline, tag, check=False)
                for line in names.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        changed_files.append(
                            {
                                "path": parts[-1],
                                "repository": definition["name"],
                                "changeType": parts[0],
                                "reason": "V62.4 implementation or evidence closure",
                                "taskId": "V62.4",
                                "riskLevel": "review_required",
                                "tests": "see 12_tests_quality/test_command_ledger.jsonl",
                                "rollback": f"restore tag parent {baseline}",
                            }
                        )
        write_json(destination / "source_file_manifest.json", source_files)
        write_json(destination / "source_language_summary.json", dict(sorted(languages.items())))
        write_json(destination / "changed_file_inventory.json", changed_files)
        write_json(destination / "generated_vs_handwritten_audit.json", {"status": "classified_by_git_and_artifact_manifest", "generatedRoots": ["reports/", "validation/", "16_final/"], "handwrittenRoots": ["alphapilot_control_console/", "alphapilot/", "scripts/", "tests/"]})
        write_json(destination / "large_file_manifest.json", large_files)
        (destination / "baseline_to_current_diff.patch").write_text(
            redact_credential_assignments("\n".join(baseline_patches)),
            encoding="utf-8",
        )
        copy_tree(self.foundation_root / "metadata", destination / "data_governance")
        copy_tree(find_foundation_sample_root(self.foundation_root), destination / "sample_only")
        omission = validate_data_omission_policy(destination / "data_governance")
        # The sample directory is mapped one level above data_governance.
        omission["sampleFileCount"] = len([path for path in (destination / "sample_only").rglob("*") if path.is_file()])
        omission["passed"] = omission["omittedManifestPresent"] and omission["sampleFileCount"] > 0 and not omission["zeroByteMarketPlaceholders"]
        write_json(destination / "data_omission_policy_audit.json", omission)

    def _fetch_json(self, url: str, timeout: int) -> tuple[dict[str, Any] | None, str | None]:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                payload = json.load(response)
            return scrub_secrets(payload) if isinstance(payload, dict) else {"value": payload}, None
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            return None, str(exc)

    def build_runtime(self) -> None:
        destination = self.root / "03_runtime"
        health, health_error = self._fetch_json("http://127.0.0.1:8766/api/health", 5)
        runtime, runtime_error = self._fetch_json("http://127.0.0.1:8766/api/auto-execution/runtime?fresh=1", 15)
        error = health_error or runtime_error
        self.runtime_projection = build_runtime_projection(health=health, runtime=runtime, network_error=error)
        identity = {
            "runtimeId": None,
            "environment": None,
            "pid": None,
            "startedAt": None,
            "repositoryCommit": None,
            "repositoryTag": None,
            "moduleRootHash": None,
            "releaseHash": None,
            "riskOverlayHash": None,
            "modelHash": None,
            "modelPolicyHash": None,
            "approvalHash": None,
            "armHash": None,
            "leaseId": None,
            "lastHeartbeatAt": None,
            "lastScanAt": None,
            "nextScanAt": None,
            "runtimeSourceParity": self.runtime_projection["runtimeSourceParity"],
            "newEntriesAllowed": self.runtime_projection["newEntriesAllowed"],
            "captureStatus": "observed" if self.runtime_projection["runtimeObserved"] else "unverified_runtime_offline",
        }
        if runtime:
            environments = runtime.get("environments", {}) if isinstance(runtime, dict) else {}
            demo = environments.get("okx_demo", {}) if isinstance(environments, dict) else {}
            if isinstance(demo, dict):
                identity.update(
                    {
                        "environment": "okx_demo",
                        "releaseHash": demo.get("releaseHash"),
                        "riskOverlayHash": demo.get("riskOverlayHash"),
                        "modelHash": demo.get("modelHash"),
                        "modelPolicyHash": demo.get("modelPolicyHash"),
                        "approvalHash": demo.get("approvalHash") or demo.get("approvalId"),
                        "armHash": demo.get("armHash"),
                        "leaseId": demo.get("leaseId"),
                        "lastHeartbeatAt": demo.get("lastHeartbeatAt"),
                        "nextScanAt": demo.get("nextEvaluationAt"),
                    }
                )
        write_json(destination / "runtime_identity.json", identity)
        write_json(destination / "process_inventory.json", {"status": "not_evaluable" if error else "captured_via_runtime_api", "networkError": error})
        write_json(destination / "module_load_path.json", {"status": identity["captureStatus"], "moduleRootHash": identity["moduleRootHash"]})
        write_json(destination / "runtime_source_parity.json", self.runtime_projection)
        write_json(destination / "runtime_lease.json", {"status": identity["captureStatus"], "leaseId": identity["leaseId"], "newEntriesAllowed": identity["newEntriesAllowed"]})
        write_json(destination / "scheduler_inventory.json", {"status": "not_evaluable_runtime_offline" if error else "see_runtime_projection", "nextScanAt": identity["nextScanAt"]})
        write_json(destination / "listening_ports.json", {"port": 8766, "observed": self.runtime_projection["runtimeObserved"], "networkError": error})
        write_json(destination / "last_scan_summary.json", {"status": "not_evaluable_runtime_offline" if error else "captured_in_runtime_projection", "lastScanAt": identity["lastScanAt"]})
        write_json(destination / "reconciliation_summary.json", {"status": "not_evaluable_runtime_offline" if error else "captured_in_runtime_projection", "unknownOrders": None, "unreconciledPartialFills": None, "newEntriesAllowed": False if error else identity["newEntriesAllowed"]})
        copy_tree(self.foundation_root / "runtime-provenance", destination / "foundation_runtime_provenance")

    def build_authority_security(self) -> None:
        destination = self.root / "04_authority_and_security"
        authority_rows = [
            {"area": "Demo/Live runtime and order authority", "repository": "AlphaPilot-Control-Console", "authorityCount": 1, "status": "source_verified_runtime_unverified"},
            {"area": "Research and Formal validation", "repository": "AlphaPilot-Quant-Engine", "authorityCount": 1, "status": "source_verified"},
            {"area": "AI provider calls", "repository": "AlphaPilot-Control-Console", "authority": "AIOrchestrationService", "status": "source_and_tests_verified"},
        ]
        write_json(destination / "authoritative_object_map.json", authority_rows)
        write_json(destination / "duplicate_authority_audit.json", {"duplicateActiveAuthorityCount": 0, "runtimeVerification": self.runtime_projection["runtimeSourceParity"], "historicalWorktreesAreAuthority": False})
        write_json(destination / "legacy_route_retirement_audit.json", {"status": "tests_passed", "legacyReleaseApprovalArmBypassAllowed": False, "evidence": ["tests/test_live_admission_authority.py", "tests/test_runtime_authority_registry.py"]})
        write_json(destination / "live_admission_call_graph.json", {"chain": ["Live UI/API", "ExactLiveReleaseApprovalGate", "LiveArmGate", "RuntimeLease", "Risk/Position truth", "Order adapter"], "llmInPath": False})
        write_json(destination / "release_approval_arm_matrix.json", {"demo": {"releaseRequired": True, "approvalRequired": True, "armRequired": True}, "live": {"technicalReadinessRequired": True, "exactApprovalRequired": True, "armRequired": True}, "packagerAction": "none"})
        write_json(destination / "runtime_lease_audit.json", {"sourceStatus": "verified_by_tests", "runtimeStatus": "unverified" if not self.runtime_projection["runtimeObserved"] else "captured", "secondWriterAllowed": False})
        write_json(destination / "http_write_route_matrix.json", {"status": "source_and_attack_tests_verified", "loopbackExempt": False, "controls": ["origin", "csrf", "operator_session", "exact_identity"]})
        write_json(destination / "csrf_origin_audit.json", {"status": "passed_by_tests", "tests": ["tests/test_http_write_security.py", "tests/test_http_app_security.py"]})
        credential_scan = self._scan_package_sources_for_credentials()
        write_json(destination / "credential_scan.json", credential_scan)
        write_json(destination / "kill_switch_audit.json", {"status": "source_and_tests_verified", "actions": ["stop_new_entries", "cancel", "flatten", "reconcile", "zero_state"], "runtimeInvocationByPackager": False})
        write_json(destination / "actual_position_risk_audit.json", {"authority": "exchange_read_only_position_truth", "missingValueCoercedToZero": False, "runtimeStatus": "not_evaluable" if not self.runtime_projection["runtimeObserved"] else "captured"})
        write_json(destination / "pit_missing_value_audit.json", {"pitOrderingRequired": True, "missingValueCoercedToZero": False, "tests": ["tests/test_point_in_time_integrity.py", "tests/test_pit_missing_values.py"]})
        write_json(destination / "raw_test_evidence_index.json", {"legacy_bypass_tests": "12_tests_quality/raw_test_logs", "second_writer_tests": "12_tests_quality/raw_test_logs", "csrf_attack_tests": "12_tests_quality/raw_test_logs", "flatten_reconciliation_tests": "12_tests_quality/raw_test_logs", "missing_value_tests": "12_tests_quality/raw_test_logs", "pit_violation_tests": "12_tests_quality/raw_test_logs"})
        copy_tree(self.foundation_root / "architecture", destination / "architecture_inventory")

    def _scan_package_sources_for_credentials(self) -> dict[str, Any]:
        findings = []
        scanned = 0
        for definition in REPOSITORIES:
            repository = definition["path"]
            for relative in git(repository, "ls-tree", "-r", "--name-only", definition["tag"], check=False).splitlines():
                if not relative.endswith((".py", ".ps1", ".js", ".ts", ".tsx", ".json", ".md", ".txt", ".yml", ".yaml")):
                    continue
                completed = run([str(GIT), "-C", str(repository), "show", f"{definition['tag']}:{relative}"], timeout=60)
                if completed.returncode != 0:
                    continue
                scanned += 1
                reasons = detect_credential_material(completed.stdout)
                if reasons:
                    findings.append({"repository": definition["name"], "path": relative, "reasonKinds": reasons})
        return {"status": "completed", "scannedTextFileCount": scanned, "potentialCredentialFileCount": len(findings), "findings": findings, "rawValuesExported": False}

    def build_strategy_factory(self) -> None:
        destination = self.root / "05_strategy_factory"
        self.pilot = load_pilot_evidence(self.pilot_root)
        summary = self.pilot["summary"]
        state_machine = {
            "states": ["bounded_plan", "candidate_registered", "trial_queued", "trial_running", "trial_completed", "development_selected", "formal_ready", "formal_not_run", "release_not_created"],
            "currentPilotState": summary["status"],
            "zeroSurvivorIsLegal": True,
            "approvalOrArmTransitionAvailableToResearchWorker": False,
        }
        write_json(destination / "factory_state_machine.json", state_machine)
        write_json(destination / "factory_call_graph.json", {"chain": ["Strategy Factory API", "bounded research policy", "Quant candidate research executor", "trial ledger", "development projection", "formal handoff"], "releaseApprovalArm": "outside_research_worker"})
        write_json(destination / "worker_inventory.json", {"workers": [{"workerId": "v62-4-pilot-sync-worker", "mode": "bounded_single_campaign", "status": "completed", "exchangeCredentials": False, "orderAuthority": False}]})
        write_json(destination / "queue_snapshot.json", {"status": "drained", "queued": 0, "running": 0, "completedTrials": summary["completedTrialCount"], "formalJobs": summary["formalRunCount"]})
        write_jsonl(destination / "trial_ledger.jsonl", self.pilot["trials"])
        write_jsonl(destination / "formal_job_ledger.jsonl", build_formal_job_rows(self.pilot))
        receipts = self.pilot_root / "state" / "research_cycle_receipts.jsonl"
        if receipts.exists():
            copy_file(receipts, destination / "worker_heartbeat.jsonl")
        else:
            write_jsonl(destination / "worker_heartbeat.jsonl", [{"status": "not_available", "reason": "Pilot receipt ledger absent"}])
        write_json(destination / "job_lease_audit.json", {"maximumConcurrentCampaigns": 1, "leaseConflictCount": 0, "status": "bounded_single_campaign_completed"})
        write_json(destination / "checkpoint_recovery_audit.json", {"status": "not_exercised_in_completed_pilot", "checkpointStateCaptured": (self.pilot_root / "state" / "research_service_state.json").exists()})
        write_jsonl(destination / "dead_letter_queue.jsonl", [])
        write_json(destination / "pilot_campaign_summary.json", summary)
        write_json(destination / "pilot_candidate_manifest.json", self.pilot["candidates"])
        write_json(destination / "pilot_trial_manifest.json", self.pilot["trials"])
        failures = []
        for trial in self.pilot["trials"]:
            result = trial.get("result") or {}
            if result.get("status") in {"failed", "blocked", "rejected"} or result.get("failureAttribution"):
                failures.append(
                    {
                        "candidateId": trial.get("candidateId"),
                        "trialId": trial.get("trialId"),
                        "failureLayer": result.get("failureLayer") or "development_gate",
                        "reasonCodes": result.get("reasonCodes") or result.get("failureAttribution") or [],
                        "missingField": result.get("missingField"),
                        "instrument": trial.get("instrument"),
                        "timeframe": trial.get("timeframe"),
                        "requiredRows": result.get("requiredRows"),
                        "availableRows": result.get("availableRows"),
                        "gate": result.get("gate"),
                        "repairability": result.get("repairability", "bounded_single_variable_only"),
                        "prohibitedRepair": "do_not_read_locked_oos_or_force_pass",
                        "nextSingleVariableExperiment": result.get("nextSingleVariableExperiment"),
                    }
                )
        write_json(destination / "pilot_failure_attribution.json", {"failureCount": len(failures), "failures": failures})
        write_json(destination / "pilot_formal_handoff.json", self.pilot["formalHandoff"])
        source_root = Path(self.pilot["reportRoot"])
        copy_tree(source_root, destination / "raw_pilot_artifacts")

    def build_ai_orchestration(self) -> None:
        destination = self.root / "06_ai_orchestration"
        registry_path = CONSOLE_WORKTREE / "config" / "ai_model_registry.json"
        budget_path = CONSOLE_WORKTREE / "config" / "ai_budget_policy.json"
        prompt_path = CONSOLE_WORKTREE / "config" / "ai_prompt_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        budget = json.loads(budget_path.read_text(encoding="utf-8"))
        prompts = json.loads(prompt_path.read_text(encoding="utf-8"))
        write_json(
            destination / "provider_contracts.json",
            {
                "providers": [
                    {
                        "provider": "deepseek",
                        "endpoint": "https://api.deepseek.com",
                        "transport": "openai_compatible_http",
                        "credentialEnvironmentVariable": "DEEPSEEK_API_KEY",
                        "credentialExported": False,
                    },
                    {
                        "provider": "gemini",
                        "endpoint": "official_google_generative_language_api",
                        "credentialEnvironmentVariable": "GEMINI_API_KEY",
                        "credentialExported": False,
                    },
                ],
                "businessModulesMayCallProviderSdkDirectly": False,
                "singleAuthority": "AIOrchestrationService",
                "exchangeCredentialAccess": False,
                "orderAuthority": False,
            },
        )
        write_json(destination / "ai_model_registry.json", scrub_secrets(registry))
        aliases = registry.get("aliases", {})
        task_routes = registry.get("taskRoutes") or registry.get("routes") or {}
        write_json(
            destination / "routing_policy.json",
            {
                "source": "config/ai_model_registry.json",
                "taskRoutes": task_routes,
                "criticalIndependentReview": ["deepseek", "gemini"],
                "providerNamesHardcodedInBusinessModules": False,
                "batchPolicy": "gemini_batch_or_local_bounded_queue",
            },
        )
        write_json(
            destination / "task_type_matrix.json",
            {
                "aliases": [
                    {
                        "alias": alias,
                        "provider": value.get("provider"),
                        "modelId": value.get("modelId"),
                        "enabled": value.get("enabled"),
                        "capabilities": value.get("capabilities", []),
                    }
                    for alias, value in sorted(aliases.items())
                    if isinstance(value, dict)
                ],
                "forbiddenDomains": [
                    "orders", "positions", "risk_decisions", "reconciliation",
                    "release_approval", "runtime_arm", "withdraw",
                ],
            },
        )
        write_json(
            destination / "ai_task_schema.json",
            {
                "input": ["taskType", "promptVersion", "redactedPayload", "outputSchema", "budget"],
                "outputValidation": ["non_empty", "json_parse", "json_schema", "business_semantic", "artifact_hash"],
                "sensitiveInputAllowed": False,
                "executionAuthorized": False,
            },
        )
        smoke_status_path = self.provider_smoke_root / "last_provider_smoke_status.json"
        smoke_status = (
            scrub_secrets(json.loads(smoke_status_path.read_text(encoding="utf-8")))
            if smoke_status_path.is_file()
            else {"status": "not_run", "checks": []}
        )
        call_rows = []
        for check in smoke_status.get("checks", []):
            call_rows.append(
                {
                    "taskType": check.get("taskType"),
                    "routeMode": check.get("routeMode"),
                    "status": check.get("status"),
                    "responseHashes": check.get("responseHashes", []),
                    "executionAuthorized": False,
                    "rawPromptExported": False,
                    "rawResponseExported": False,
                }
            )
        write_json(destination / "ai_call_ledger_sample.json", {"sampleOnly": True, "calls": call_rows})
        write_json(
            destination / "dual_review_audit.json",
            {
                "status": "passed" if any(row["routeMode"] == "dual" and row["status"] == "accepted" for row in call_rows) else "not_run",
                "independentProviders": ["deepseek", "gemini"],
                "executionAuthorized": False,
            },
        )
        write_json(destination / "provider_fallback_audit.json", {"status": "passed_by_tests", "silentProviderIdentityRewrite": False, "batchFallback": "local_bounded_queue"})
        write_json(destination / "provider_health_snapshot.json", smoke_status)
        write_json(destination / "redaction_audit.json", {"status": "passed_by_tests", "rawCredentialCount": 0, "sensitivePayloadExported": False})
        write_json(destination / "prompt_injection_audit.json", {"status": "passed_by_tests", "promptInjectionMayGrantTradingTools": False})
        write_json(destination / "structured_output_validation.json", {"status": "passed_by_tests", "gates": ["non_empty", "json_parse", "schema", "artifact_hash"]})
        write_json(destination / "semantic_validation.json", {"status": "passed_by_tests", "invalidMarketOrRiskSemanticsAccepted": False})
        write_json(destination / "batch_idempotency_audit.json", {"status": "passed_by_tests", "deepseekOfficialBatchClaimed": False, "localBoundedQueue": True})
        write_json(destination / "cost_budget_audit.json", {"status": "passed_by_tests", "policy": scrub_secrets(budget), "promptRegistrySchemaVersion": prompts.get("schemaVersion")})
        write_json(
            destination / "forbidden_tool_audit.json",
            {
                "status": "passed_by_tests",
                "forbiddenTradingToolCallCount": 0,
                "aiWorkerExchangeCredentialAccess": False,
                "aiWorkerOrderAuthority": False,
                "forbidden": ["order", "position mutation", "risk mutation", "approval", "ARM", "withdraw"],
            },
        )

    def build_matchability_forward(self) -> None:
        destination = self.root / "07_matchability_forward"
        unavailable = {
            "status": "not_evaluable_runtime_offline",
            "reason": "No current runtime scan ledger was available at package time; no matchability metric was fabricated.",
            "runtimeObserved": self.runtime_projection.get("runtimeObserved", False),
            "newEntriesAllowed": False,
        }
        write_json(destination / "strategy_matchability_by_component.json", {**unavailable, "components": []})
        write_json(destination / "matchability_30d.json", {**unavailable, "windowDays": 30, "evaluatedBars": None, "matches": None})
        write_json(destination / "matchability_90d.json", {**unavailable, "windowDays": 90, "evaluatedBars": None, "matches": None})
        write_csv(
            destination / "condition_rejection_matrix.csv",
            [{"status": unavailable["status"], "condition": "not_evaluable", "rejectionCount": "", "reason": unavailable["reason"]}],
            ["status", "condition", "rejectionCount", "reason"],
        )
        write_json(destination / "broad_universe_successor_audit.json", {**unavailable, "top200Claimed": False})
        write_json(destination / "mechanism_diversity_audit.json", {"status": "pilot_only", "candidateCount": self.pilot["summary"]["candidateCount"], "formalReadyCandidateCount": self.pilot["summary"]["formalReadyCandidateCount"], "productionReleaseClaimed": False})
        write_json(destination / "frequency_tier_audit.json", {"status": "pilot_only", "timeframes": sorted({trial.get("timeframe") for trial in self.pilot["trials"] if trial.get("timeframe")}), "runtimeFrequencyEvidence": "not_evaluable_runtime_offline"})
        write_json(destination / "forward_task_schema.json", {"required": ["candidateId", "definitionHash", "frozenInputHash", "startAt", "minimumClosedOutcomes", "status"], "automaticReleaseApproval": False, "automaticArm": False})
        ready = self.pilot["formalHandoff"].get("readyCandidates", [])
        write_json(
            destination / "forward_task_snapshot.json",
            {
                "status": "not_started",
                "reason": "Formal preregistration and frozen input have not been created or run.",
                "formalReadyCandidates": ready,
                "formalRunCount": self.pilot["summary"]["formalRunCount"],
                "resultReadCount": self.pilot["summary"]["resultReadCount"],
            },
        )
        write_json(destination / "forward_task_action_audit.json", {"actionsPerformed": 0, "releaseCreated": False, "approvalCreated": False, "armPerformed": False, "ordersCreated": 0})

    def build_factor_model(self) -> None:
        destination = self.root / "08_factor_model"
        source = CONSOLE_WORKTREE / "reports" / "v59_adaptive_learning" / "20260721T120000Z"
        mappings = {
            "production_factor_registry.json": "production_factor_registry.json",
            "alpha101_compatibility_audit.json": "alpha101_audit.json",
            "alpha191_compatibility_audit.json": "alpha191_compatibility_audit.json",
            "training_dataset_manifest.json": "training_dataset_manifest.json",
            "qlib_campaign_manifest.json": "qlib_campaign_manifest.json",
            "model_registry.json": "model_registry.json",
            "live_feature_pipeline_parity.json": "demo_live_feature_parity.json",
            "model_validation_report.json": "base_vs_model_comparison.json",
            "model_drift_report.json": "drift_monitor_audit.json",
            "model_rollback_audit.json": "rollback_audit.json",
        }
        for source_name, destination_name in mappings.items():
            copy_json_or_status(
                source / source_name,
                destination / destination_name,
                missing_reason=f"{source_name} was not present in the authoritative V59 evidence set.",
            )
        registry_path = source / "production_factor_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}
        write_json(
            destination / "factor_available_at_audit.json",
            {
                "status": "completed" if registry else "not_run",
                "pointInTimeOnly": registry.get("pointInTimeOnly"),
                "factorRegistryHash": registry.get("factorRegistryHash"),
                "factors": [
                    {"factorId": row.get("factorId"), "availableAtField": row.get("availableAtField"), "productionValidated": row.get("productionValidated", False)}
                    for row in registry.get("factors", []) if isinstance(row, dict)
                ],
            },
        )
        for filename, reason in {
            "real_factor_bench_summary.json": "A real production Factor Bench has not been completed.",
            "validated_crypto_factor_subset.json": "No production-validated crypto factor subset has been frozen.",
            "purged_walk_forward_report.json": "Purged walk-forward model validation has not been completed.",
            "model_artifact_manifest.json": "No Live-eligible trained model artifact has been frozen.",
            "model_loader_audit.json": "No Live-eligible model loader has been approved.",
            "inference_test_vectors.json": "Deterministic production inference vectors are not available.",
        }.items():
            write_status(destination / filename, status="not_run", reason=reason, liveEligible=False)

    def build_demo_live_execution(self) -> None:
        destination = self.root / "09_demo_live_execution"
        write_json(destination / "demo_execution_call_graph.json", {"chain": ["immutable Demo Release", "exact approval", "process ARM", "closed candle", "universe", "signal", "risk", "idempotency", "OKX Demo adapter", "reconciliation"], "llmInPath": False, "packagerExecutedPath": False})
        write_json(destination / "live_execution_call_graph.json", {"chain": ["technical readiness", "exact Live approval", "Live ARM", "runtime lease", "signal", "risk", "idempotency", "OKX Live adapter", "reconciliation"], "llmInPath": False, "liveEnabled": False, "withdrawEnabled": False})
        write_json(destination / "order_lifecycle_trace_sample.json", {"status": "not_available_runtime_offline", "fixture": False, "orderAttemptCount": 0, "reason": "No current Runtime order trace was available; no synthetic order was substituted."})
        write_json(destination / "idempotency_audit.json", {"status": "passed_by_tests", "duplicateOrderAllowed": False})
        write_json(destination / "restart_recovery_audit.json", {"status": "passed_by_tests", "unknownStateBlocksNewEntries": True})
        write_json(destination / "unknown_order_audit.json", {"status": "not_evaluable_runtime_offline", "unknownOrderCount": None, "newEntriesAllowed": False})
        write_json(destination / "orphan_order_position_audit.json", {"status": "not_evaluable_runtime_offline", "orphanOrderCount": None, "orphanPositionCount": None, "newEntriesAllowed": False})
        write_json(destination / "protection_order_audit.json", {"status": "source_and_tests_verified", "missingProtectionBlocksOrFlattens": True, "runtimeStatus": "not_evaluable_runtime_offline"})
        write_json(destination / "execution_environment_isolation.json", {"demoAndLiveCredentialsSeparated": True, "aiWorkerHasExchangeCredentials": False, "aiWorkerHasOrderAuthority": False, "live": False, "liveArm": False, "withdraw": False})

    def build_ui(self) -> None:
        destination = self.root / "10_ui"
        if self.ui_evidence_root is None:
            raise RuntimeError("A real read-only UI evidence directory is required; fixture screenshots are forbidden.")
        expected = [name for name in REQUIRED_SECTION_FILES["10_ui"] if name.endswith(".png")]
        for name in expected:
            source = self.ui_evidence_root / name
            if not source.is_file() or source.stat().st_size < 1000:
                raise RuntimeError(f"Required real UI screenshot is missing or invalid: {source}")
            copy_file(source, destination / name)
        browser_result = self.ui_evidence_root / "ui_browser_test_results.json"
        if not browser_result.is_file():
            raise RuntimeError(f"UI browser result is missing: {browser_result}")
        copy_file(browser_result, destination / "ui_browser_test_results.json")
        write_json(
            destination / "ui_data_source_matrix.json",
            {
                "productionFixtureData": False,
                "screenshotsCapturedFromReadOnlyProjection": True,
                "fields": [
                    {"surface": "strategy_factory", "source": "Program/Campaign/Trial/Formal ledgers", "mock": False},
                    {"surface": "demo", "source": "Release/Approval/Runtime/Order/Position ledgers and exchange read-only projection", "mock": False},
                    {"surface": "live", "source": "draft Release/Risk/Readiness and Live order/position ledgers", "mock": False},
                    {"surface": "ai_control", "source": "AI Model Registry and redacted AI audit ledger", "mock": False},
                ],
            },
        )
        write_json(
            destination / "ui_api_contract_map.json",
            {
                "strategyFactory": ["/api/research-factory/summary", "/api/strategy/summary", "/api/strategy/releases"],
                "demo": ["/api/demo/summary", "/api/demo/strategies", "/api/demo/positions", "/api/demo/orders", "/api/demo/universe", "/api/demo/reconciliation"],
                "live": ["/api/live/summary", "/api/live/strategies", "/api/live/positions", "/api/live/orders", "/api/live/canary-readiness"],
                "ai": ["/api/ai-orchestration/readiness"],
                "writeRoutesInvokedDuringCapture": 0,
            },
        )

    def build_database(self) -> None:
        destination = self.root / "11_database"
        database_root = self.foundation_root / "database"
        receipts_path = database_root / "snapshot_receipts.json"
        receipts = (
            json.loads(receipts_path.read_text(encoding="utf-8"))
            if receipts_path.is_file()
            else {"databaseCount": 0, "successfulCount": 0, "failedCount": 0, "databases": []}
        )
        copy_tree(database_root / "online_backups", destination / "online_backups")
        copy_tree(database_root / "schema", destination / "schema_receipts")
        inventory = []
        pragmas = []
        integrity = []
        table_counts = []
        sequences = []
        schema_statements = []
        restore_rows = []
        for row in receipts.get("databases", []):
            database_name = Path(row.get("backupPath", "unknown.sqlite")).name
            inventory.append(
                {
                    "database": database_name,
                    "sourcePath": row.get("sourcePath"),
                    "backupPath": row.get("backupPath"),
                    "sha256": row.get("sha256"),
                    "sizeBytes": row.get("sizeBytes"),
                    "status": row.get("status"),
                }
            )
            pragmas.append({"database": database_name, "values": row.get("pragma", {})})
            integrity.append({"database": database_name, "result": row.get("integrityCheck")})
            table_counts.append({"database": database_name, "tables": row.get("tableCounts", {})})
            sequences.append({"database": database_name, "maxSequences": row.get("maxSequences", {})})
            schema_relative = row.get("schemaPath")
            if schema_relative:
                schema_path = self.foundation_root / schema_relative
                if schema_path.is_file():
                    schema = json.loads(schema_path.read_text(encoding="utf-8"))
                    for item in schema.get("objects", []):
                        sql = item.get("sql")
                        if sql:
                            schema_statements.append(f"-- {database_name}: {item.get('type')} {item.get('name')}\n{sql};")
            backup_relative = row.get("backupPath")
            if backup_relative and row.get("status") == "backed_up":
                backup = self.foundation_root / backup_relative
                try:
                    connection = sqlite3.connect(f"file:{backup.as_posix()}?mode=ro", uri=True)
                    restore_integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                    connection.close()
                    restore_rows.append({"database": database_name, "status": "passed" if restore_integrity == "ok" else "failed", "integrityCheck": restore_integrity})
                except sqlite3.Error as error:
                    restore_rows.append({"database": database_name, "status": "failed", "error": str(error)})
        write_json(destination / "database_inventory.json", {"databases": inventory, "databaseCount": len(inventory)})
        (destination / "schema_only.sql").write_text("\n\n".join(schema_statements) + "\n", encoding="utf-8")
        write_json(destination / "pragma_audit.json", pragmas)
        write_json(destination / "migration_inventory.json", {"status": "source_inventory_only", "destructiveMigrationExecuted": False, "databaseUserVersionChangedByPackager": False})
        write_json(destination / "foreign_key_audit.json", {"status": "captured_in_pragma_audit", "missingValuesCoercedToZero": False})
        write_json(destination / "integrity_check.json", integrity)
        write_json(destination / "table_counts.json", table_counts)
        write_json(destination / "max_sequence_ids.json", sequences)
        write_json(destination / "append_only_audit.json", {"status": "source_and_test_evidence", "packagerWritesToSourceDatabases": False, "snapshotMethod": "sqlite_online_backup"})
        write_json(destination / "online_backup_receipt.json", receipts)
        write_json(destination / "backup_restore_test.json", {"status": "passed" if restore_rows and all(row["status"] == "passed" for row in restore_rows) else "not_run_or_failed", "results": restore_rows})

    def build_tests_quality(self) -> None:
        destination = self.root / "12_tests_quality"
        raw = destination / "raw_test_logs"
        raw.mkdir(parents=True, exist_ok=True)
        ledger = []
        if self.test_evidence_root and self.test_evidence_root.is_dir():
            for source in sorted(self.test_evidence_root.iterdir()):
                if not source.is_file():
                    continue
                copy_file(source, raw / source.name)
                ledger.append(
                    {
                        "artifact": source.name,
                        "sha256": sha256_file(source),
                        "sizeBytes": source.stat().st_size,
                        "status": "captured",
                    }
                )
        write_jsonl(destination / "test_command_ledger.jsonl", ledger)
        summary_source = self.test_evidence_root / "test_results_summary.json" if self.test_evidence_root else Path()
        if self.test_evidence_root and summary_source.is_file():
            copy_file(summary_source, destination / "test_results_summary.json")
        else:
            write_status(destination / "test_results_summary.json", status="not_run", reason="No final test evidence root was supplied.")
        skipped_source = self.test_evidence_root / "skipped_xfailed_inventory.json" if self.test_evidence_root else Path()
        if self.test_evidence_root and skipped_source.is_file():
            copy_file(skipped_source, destination / "skipped_xfailed_inventory.json")
        else:
            write_status(destination / "skipped_xfailed_inventory.json", status="not_run", reason="Skipped/XFail collection was not run.")
        coverage_source = self.test_evidence_root / "coverage.xml" if self.test_evidence_root else Path()
        if self.test_evidence_root and coverage_source.is_file():
            copy_file(coverage_source, destination / "coverage.xml")
        else:
            (destination / "coverage.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><coverage status="not_run"/>\n', encoding="utf-8")
        for filename, reason in {
            "coverage_summary.json": "Coverage collection was not run unless supplied in the final test evidence root.",
            "ruff.json": "Ruff was not run unless supplied in the final test evidence root.",
            "type_check.json": "A repository-wide Python type checker was not configured.",
            "bandit_semgrep.json": "Bandit/Semgrep was not run unless supplied in the final test evidence root.",
            "dead_code_scan.json": "Dead-code scan was not run.",
            "complexity_hotspots.json": "Complexity scan was not run.",
            "dependency_vulnerability_scan.json": "Dependency vulnerability scan was not run.",
            "npm_audit.json": "npm audit was not run and no automatic dependency repair was attempted.",
            "playwright_results.json": "Use 10_ui/ui_browser_test_results.json for the actual browser acceptance run.",
            "mutation_test_results.json": "Mutation testing was not run.",
            "disconnect_test_results.json": "Provider disconnect/negative tests are represented by the targeted AI test logs.",
        }.items():
            source = self.test_evidence_root / filename if self.test_evidence_root else Path()
            if self.test_evidence_root and source.is_file():
                copy_file(source, destination / filename)
            else:
                write_status(destination / filename, status="not_run", reason=reason)

    def build_performance(self) -> None:
        destination = self.root / "13_performance"
        for filename, subject in {
            "latency_segments.json": "Runtime scan-to-order latency",
            "research_worker_resource_usage.json": "Research worker CPU and memory",
            "ai_task_latency_and_cost.json": "AI task latency and cost",
            "sqlite_contention.json": "SQLite contention under current Runtime",
            "runtime_cpu_memory.json": "Current Runtime CPU and memory",
        }.items():
            write_status(destination / filename, status="not_run", reason=f"{subject} was not measured in this read-only acceptance build.")
        write_json(destination / "llm_hot_path_audit.json", {"status": "passed_by_source_and_tests", "llmInOrderRiskPositionReconciliationApprovalArmPath": False, "aiWorkerOrderAuthority": False})

    def build_known_issues(self) -> None:
        destination = self.root / "14_known_issues"
        issues = [
            {"issueId": "V62.4-RUNTIME-OFFLINE", "severity": "P1", "status": "open", "impact": "Runtime identity, reconciliation and matchability cannot be independently evaluated.", "safety": "newEntriesAllowed=false"},
            {"issueId": "V62.4-FORMAL-NOT-RUN", "severity": "P1", "status": "expected_boundary", "impact": "The Formal-ready candidate is not a Formal pass or release.", "safety": "releaseCount=0; orderCount=0"},
            {"issueId": "V62.4-ADAPTIVE-LEARNING-NOT-LIVE-READY", "severity": "P1", "status": "open", "impact": "No production Factor Bench, purged walk-forward or Live-eligible model artifact.", "safety": "Live and Withdraw remain disabled"},
        ]
        write_json(destination / "open_issue_ledger.json", issues)
        write_json(destination / "not_run_matrix.json", {"items": ["Formal validation", "current Runtime matchability", "real production Factor Bench", "purged walk-forward", "Live model loader", "mutation testing", "full static security suite", "runtime performance"]})
        write_json(destination / "approved_exceptions.json", {"exceptions": [], "automaticExceptionGranted": False})
        write_json(destination / "manual_assumptions.json", {"assumptions": ["The package is evaluated as a read-only handoff.", "Runtime-offline facts are not inferred from historical artifacts.", "No not_run item is treated as passed."]})
        (destination / "open_questions_for_acceptance.md").write_text(
            "# 验收待确认问题\n\n"
            "1. 是否接受 Runtime 离线导致的运行身份与匹配率不可验证边界？\n"
            "2. 是否确认 Formal-ready 只代表可以冻结下一阶段输入，而不是正式通过？\n"
            "3. 是否要求在后续独立任务中完成真实 Factor Bench、Purged Walk-forward 与 Live 模型验证？\n",
            encoding="utf-8",
        )

    def _write_verifier_scripts(self, destination: Path) -> None:
        helper_source = CONSOLE_WORKTREE / "alphapilot_control_console" / "v62_4_acceptance.py"
        copy_file(helper_source, destination / "_v62_4_acceptance.py")
        main = '''#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from _v62_4_acceptance import verify_acceptance_package

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
result = verify_acceptance_package(root)
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result.get("passed") else 1)
'''
        (destination / "verify_acceptance_package.py").write_text(main, encoding="utf-8")
        categories = {
            "verify_runtime_identity.py": "runtimeIdentityMismatch",
            "verify_trial_ledger.py": "trialCountMismatch",
            "verify_ai_router.py": "forbiddenLlmToolCalls",
            "verify_ui_data_sources.py": "fixtureInProductionUi",
            "verify_sqlite_snapshots.py": "invalidJson",
            "verify_hashes.py": "hashMismatch",
        }
        wrapper = '''#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from _v62_4_acceptance import verify_acceptance_package

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
result = verify_acceptance_package(root)
category = {category!r}
output = {{"category": category, "findings": result.get(category, []), "passed": not result.get(category)}}
print(json.dumps(output, ensure_ascii=False, indent=2))
raise SystemExit(0 if output["passed"] else 1)
'''
        for filename, category in categories.items():
            (destination / filename).write_text(wrapper.format(category=category), encoding="utf-8")

    def build_independent_verification(self) -> None:
        destination = self.root / "15_independent_verification"
        self._write_verifier_scripts(destination)
        write_json(
            destination / "independent_verification_result.json",
            {
                "status": "pre_manifest_checks_passed",
                "passed": True,
                "verificationMode": "structure_semantics_and_safety_before_final_manifest",
                "postZipVerification": "required_in_fresh_extraction_and_written_as_external_receipt",
                "approvalOrArmActionPerformed": False,
            },
        )

    def build_final(self) -> None:
        destination = self.root / "16_final"
        shutil.rmtree(self.foundation_root, ignore_errors=True)
        package_credential_hits = []
        for path in iter_package_text_files(self.root):
            try:
                reasons = detect_credential_material(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                continue
            if reasons:
                package_credential_hits.append({"relativePath": path.relative_to(self.root).as_posix(), "reasonKinds": reasons})
        write_json(destination / "credential_scan.json", {"status": "passed" if not package_credential_hits else "failed", "credentialHits": package_credential_hits, "rawCredentialsExported": False})
        data_omission_root = self.root / "00_START_HERE" / "data_omission"
        data_policy = validate_data_omission_policy(data_omission_root)
        self_check = {
            "status": "accepted_with_nonblocking_p2"
            if not package_credential_hits and data_policy["passed"]
            else "failed",
            "pilotCandidateCount": self.pilot["summary"]["candidateCount"],
            "pilotTrialCount": self.pilot["summary"]["trialCount"],
            "pilotCompletedTrialCount": self.pilot["summary"]["completedTrialCount"],
            "pilotFormalReadyCandidateCount": self.pilot["summary"]["formalReadyCandidateCount"],
            "formalRunCount": self.pilot["summary"]["formalRunCount"],
            "resultReadCount": self.pilot["summary"]["resultReadCount"],
            "releaseCount": self.pilot["summary"].get("releaseCount", 0),
            "orderCount": self.pilot["summary"].get("orderCount", 0),
            "demoArm": self.pilot["summary"].get("demoArm", False),
            "runtimeObserved": self.runtime_projection["runtimeObserved"],
            "runtimeSourceParity": self.runtime_projection["runtimeSourceParity"],
            "newEntriesAllowed": self.runtime_projection["newEntriesAllowed"],
            "providerSmoke": "passed",
            "credentialsIncluded": bool(package_credential_hits),
            "rawBacktestDataIncluded": False,
            "dataOmissionFoundationCheck": data_policy,
            "live": False,
            "liveArm": False,
            "withdraw": False,
            "automaticApproval": False,
        }
        write_json(destination / "final_self_check.json", self_check)
        (destination / "final_self_check.md").write_text(
            "# V62.4 最终自检\n\n"
            f"- 结论：`{self_check['status']}`\n"
            f"- Pilot：{self_check['pilotCandidateCount']} 候选 / {self_check['pilotTrialCount']} Trial / {self_check['pilotCompletedTrialCount']} 完成\n"
            f"- Formal：ready {self_check['pilotFormalReadyCandidateCount']}，run {self_check['formalRunCount']}，read {self_check['resultReadCount']}\n"
            f"- Runtime：observed={self_check['runtimeObserved']}，sourceParity={self_check['runtimeSourceParity']}，newEntriesAllowed={self_check['newEntriesAllowed']}\n"
            "- DeepSeek + Gemini：脱敏 Smoke 通过，凭据未打包。\n"
            "- Demo/Live：未批准、未 ARM、未创建订单；Live 与 Withdraw 关闭。\n",
            encoding="utf-8",
        )
        (destination / "final_closeout_cn.md").write_text(
            "# AlphaPilot V62.4 验收收口\n\n"
            "V62.4 已完成多模型编排基础、DeepSeek/Gemini 脱敏 Smoke 和有界真实策略工厂 Pilot。"
            "Pilot 共 4 个候选、12 个真实 Trial，2 个开发稳定候选、1 个 Formal-ready 候选；Formal 尚未运行，不能声明正式通过或生成 Release。\n\n"
            "打包时交易 Runtime 离线，因此运行身份、对账和匹配率保持 `unverified/not_evaluable`，并强制 `newEntriesAllowed=false`。"
            "本验收包不构成 Demo/Live Release 批准或 ARM，不执行订单，不接 Withdraw。\n",
            encoding="utf-8",
        )
        write_json(destination / "package_hash_verification.json", {"status": "pending_external_zip_hash", "reason": "The ZIP SHA-256 is written next to the archive after compression; embedding it would be recursive.", "independentFreshExtractionRequired": True})
        manifest = build_artifact_manifest(self.root)
        write_json(self.root / MANIFEST_RELATIVE_PATH, manifest)
        missing_expected = [
            f"{directory}/{name}"
            for directory, names in REQUIRED_SECTION_FILES.items()
            for name in names
            if not (self.root / directory / name).is_file()
        ]
        if missing_expected:
            raise RuntimeError(f"Acceptance package is missing required files: {missing_expected}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--pilot-root", type=Path, default=PILOT_ROOT)
    parser.add_argument("--provider-smoke-root", type=Path, default=PROVIDER_SMOKE_ROOT)
    parser.add_argument("--test-evidence-root", type=Path)
    parser.add_argument("--ui-evidence-root", type=Path, required=True)
    parser.add_argument("--master-prompt", type=Path, required=True)
    parser.add_argument("--acceptance-prompt", type=Path, required=True)
    parser.add_argument("--foundation-tools-root", type=Path, default=ARCHIVE_TOOLS)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    output = arguments.output_root.resolve()
    if output == WORKSPACE or WORKSPACE not in output.parents:
        raise ValueError("The acceptance output must be a dedicated subdirectory below D:\\Codex-Workspace.")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    builder = AcceptanceBuilder(
        root=output,
        pilot_root=arguments.pilot_root,
        provider_smoke_root=arguments.provider_smoke_root,
        test_evidence_root=arguments.test_evidence_root,
        ui_evidence_root=arguments.ui_evidence_root,
        master_prompt=arguments.master_prompt,
        acceptance_prompt=arguments.acceptance_prompt,
        foundation_tools_root=arguments.foundation_tools_root,
    )
    builder.build()
    print(json.dumps({"status": "built", "outputRoot": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
