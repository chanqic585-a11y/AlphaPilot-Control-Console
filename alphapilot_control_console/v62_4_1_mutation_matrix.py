from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class MutationCase:
    mutation_id: str
    source_path: Path
    test_path: Path
    original: str
    mutated: str
    rationale: str


def build_default_mutation_cases() -> list[MutationCase]:
    return [
        MutationCase(
            mutation_id="runtime_lease_accepts_expired_lease",
            source_path=Path("alphapilot_control_console/execution_runtime_lease.py"),
            test_path=Path("tests/test_execution_runtime_lease.py"),
            original='and _parse(str(row["expiresAt"])) > now',
            mutated='and _parse(str(row["expiresAt"])) < now',
            rationale="An expired execution lease must never be treated as current.",
        ),
        MutationCase(
            mutation_id="runtime_guard_ignores_unknown_orders",
            source_path=Path("alphapilot_control_console/demo_runtime_guard.py"),
            test_path=Path("tests/test_demo_runtime_guard.py"),
            original='if statuses & {"prepared", "unknown"}:',
            mutated='if False and statuses & {"prepared", "unknown"}:',
            rationale="Prepared or unknown orders must continue blocking unsafe runtime changes.",
        ),
        MutationCase(
            mutation_id="ai_router_allows_forbidden_trade_task",
            source_path=Path("alphapilot_control_console/ai_orchestration/task_router.py"),
            test_path=Path("tests/test_ai_orchestration_service.py"),
            original=(
                "if task_type in FORBIDDEN_TASK_TYPES:\n"
                '            raise ForbiddenAITaskError(f"LLM use is forbidden for task type: {task_type}")'
            ),
            mutated=(
                "if task_type in FORBIDDEN_TASK_TYPES:\n"
                '            return TaskRoute(mode="single", model_aliases=("deepseek_fast",))'
            ),
            rationale="AI orchestration must reject order, risk, position, approval, and ARM tasks.",
        ),
        MutationCase(
            mutation_id="latency_policy_reverses_critical_threshold",
            source_path=Path("alphapilot_control_console/demo_entry_latency_policy.py"),
            test_path=Path("tests/test_demo_entry_latency_policy.py"),
            original='if close_to_ready_ms >= int(profile["criticalLatencyFailureMs"]):',
            mutated='if close_to_ready_ms < int(profile["criticalLatencyFailureMs"]):',
            rationale="Critical latency failures must remain fail-closed.",
        ),
        MutationCase(
            mutation_id="http_write_loopback_detection_disabled",
            source_path=Path("alphapilot_control_console/http_write_security.py"),
            test_path=Path("tests/test_http_write_security.py"),
            original='return ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback',
            mutated="return False",
            rationale="Loopback and remote write modes must remain distinguishable and authenticated.",
        ),
    ]


def _run_pytest(
    *,
    python_executable: Path,
    repository_root: Path,
    test_path: Path,
    python_path: str,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = python_path
    return subprocess.run(
        [
            str(python_executable),
            "-m",
            "pytest",
            str(repository_root / test_path),
            "-q",
        ],
        cwd=repository_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )


def _result_excerpt(completed: subprocess.CompletedProcess[str]) -> str:
    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    lines = [line.rstrip() for line in combined.splitlines() if line.strip()]
    return "\n".join(lines[-12:])


def run_mutation_matrix(
    *,
    repository_root: Path,
    python_executable: Path,
    output_directory: Path,
    cases: Iterable[MutationCase] | None = None,
) -> dict[str, object]:
    repository_root = repository_root.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    selected_cases = list(cases or build_default_mutation_cases())
    results: list[dict[str, object]] = []

    for case in selected_cases:
        source_path = repository_root / case.source_path
        test_path = repository_root / case.test_path
        if not source_path.is_file() or not test_path.is_file():
            results.append(
                {
                    "mutationId": case.mutation_id,
                    "status": "invalid",
                    "reason": "source_or_test_missing",
                    "sourcePath": case.source_path.as_posix(),
                    "testPath": case.test_path.as_posix(),
                }
            )
            continue

        baseline = _run_pytest(
            python_executable=python_executable,
            repository_root=repository_root,
            test_path=case.test_path,
            python_path=str(repository_root),
        )
        if baseline.returncode != 0:
            results.append(
                {
                    "mutationId": case.mutation_id,
                    "status": "invalid",
                    "reason": "baseline_test_failed",
                    "sourcePath": case.source_path.as_posix(),
                    "testPath": case.test_path.as_posix(),
                    "baselineExitCode": baseline.returncode,
                    "baselineOutput": _result_excerpt(baseline),
                }
            )
            continue

        with tempfile.TemporaryDirectory(prefix=f"alphapilot-{case.mutation_id}-") as temporary:
            temporary_root = Path(temporary)
            isolated_package = temporary_root / "alphapilot_control_console"
            shutil.copytree(
                repository_root / "alphapilot_control_console",
                isolated_package,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            shutil.copytree(
                repository_root / "tests",
                temporary_root / "tests",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            mutated_source = temporary_root / case.source_path
            source_text = mutated_source.read_text(encoding="utf-8")
            occurrence_count = source_text.count(case.original)
            if occurrence_count != 1:
                results.append(
                    {
                        "mutationId": case.mutation_id,
                        "status": "invalid",
                        "reason": "mutation_anchor_not_unique",
                        "anchorOccurrenceCount": occurrence_count,
                        "sourcePath": case.source_path.as_posix(),
                        "testPath": case.test_path.as_posix(),
                    }
                )
                continue
            mutated_source.write_text(
                source_text.replace(case.original, case.mutated, 1),
                encoding="utf-8",
            )
            completed = _run_pytest(
                python_executable=python_executable,
                repository_root=temporary_root,
                test_path=case.test_path,
                python_path=str(temporary_root),
            )

        if completed.returncode == 0:
            status = "survived"
            reason = "targeted_tests_still_passed"
        elif completed.returncode == 1 and "failed" in completed.stdout.casefold():
            status = "killed"
            reason = "targeted_test_failure"
        else:
            status = "invalid"
            reason = "pytest_execution_or_collection_error"
        results.append(
            {
                "mutationId": case.mutation_id,
                "status": status,
                "reason": reason,
                "sourcePath": case.source_path.as_posix(),
                "testPath": case.test_path.as_posix(),
                "rationale": case.rationale,
                "baselineExitCode": baseline.returncode,
                "mutatedExitCode": completed.returncode,
                "mutatedOutput": _result_excerpt(completed),
            }
        )

    killed_count = sum(result["status"] == "killed" for result in results)
    survived_count = sum(result["status"] == "survived" for result in results)
    invalid_count = sum(result["status"] == "invalid" for result in results)
    total_count = len(results)
    status = (
        "passed"
        if total_count > 0
        and killed_count == total_count
        and survived_count == 0
        and invalid_count == 0
        else "failed"
    )
    report: dict[str, object] = {
        "schemaVersion": "v62_4_1_mutation_matrix_v1",
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": status,
        "nativeMutmut": {
            "status": "not_run_unsupported_windows",
            "reason": "Mutmut 3.6.0 reports native Windows as unsupported.",
        },
        "customSourceMutationMatrix": {
            "status": status,
            "method": "isolated_package_copy_with_targeted_pytest",
        },
        "totalCount": total_count,
        "killedCount": killed_count,
        "survivedCount": survived_count,
        "invalidCount": invalid_count,
        "mutationScore": (killed_count / total_count) if total_count else 0.0,
        "cases": results,
    }
    (output_directory / "mutation_matrix.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_lines = [
        "# V62.4.1 Source Mutation Matrix",
        "",
        f"- Status: `{status}`",
        f"- Mutants killed: `{killed_count}/{total_count}`",
        f"- Mutation score: `{report['mutationScore']:.1%}`",
        "- Native Mutmut: `not_run_unsupported_windows`",
        "",
        "| Mutation | Result | Target test |",
        "|---|---:|---|",
    ]
    markdown_lines.extend(
        f"| `{result['mutationId']}` | `{result['status']}` | `{result['testPath']}` |"
        for result in results
    )
    (output_directory / "mutation_matrix.md").write_text(
        "\n".join(markdown_lines) + "\n",
        encoding="utf-8",
    )
    return report


__all__ = [
    "MutationCase",
    "build_default_mutation_cases",
    "run_mutation_matrix",
]
