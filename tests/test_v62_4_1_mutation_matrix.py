from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alphapilot_control_console.v62_4_1_mutation_matrix import (
    MutationCase,
    build_default_mutation_cases,
    run_mutation_matrix,
)


class V6241MutationMatrixTests(unittest.TestCase):
    def test_default_cases_cover_execution_and_ai_safety_boundaries(self) -> None:
        cases = build_default_mutation_cases()

        self.assertGreaterEqual(len(cases), 5)
        self.assertEqual(len({case.mutation_id for case in cases}), len(cases))
        self.assertIn("execution_runtime_lease.py", {case.source_path.name for case in cases})
        self.assertIn("task_router.py", {case.source_path.name for case in cases})
        self.assertTrue(all(case.original != case.mutated for case in cases))

    def test_matrix_counts_only_assertion_failures_as_killed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            package = root / "alphapilot_control_console"
            tests = root / "tests"
            package.mkdir()
            tests.mkdir()
            source = package / "policy.py"
            source.write_text("ALLOWED = True\n", encoding="utf-8")
            test_path = tests / "test_policy.py"
            test_path.write_text("def test_policy(): assert True\n", encoding="utf-8")
            case = MutationCase(
                mutation_id="policy_flip",
                source_path=Path("alphapilot_control_console/policy.py"),
                test_path=Path("tests/test_policy.py"),
                original="ALLOWED = True",
                mutated="ALLOWED = False",
                rationale="fixture",
            )
            baseline = subprocess.CompletedProcess(
                args=["pytest"],
                returncode=0,
                stdout="1 passed",
                stderr="",
            )
            completed = subprocess.CompletedProcess(
                args=["pytest"],
                returncode=1,
                stdout="1 failed",
                stderr="",
            )

            with patch(
                "alphapilot_control_console.v62_4_1_mutation_matrix.subprocess.run",
                side_effect=[baseline, completed],
            ):
                result = run_mutation_matrix(
                    repository_root=root,
                    python_executable=Path("python"),
                    output_directory=root / "evidence",
                    cases=[case],
                )

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["killedCount"], 1)
            self.assertEqual(result["survivedCount"], 0)
            evidence = json.loads(
                (root / "evidence" / "mutation_matrix.json").read_text(encoding="utf-8")
            )
            self.assertEqual(evidence["cases"][0]["status"], "killed")

    def test_collection_errors_are_invalid_not_killed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            package = root / "alphapilot_control_console"
            tests = root / "tests"
            package.mkdir()
            tests.mkdir()
            (package / "policy.py").write_text("ALLOWED = True\n", encoding="utf-8")
            (tests / "test_policy.py").write_text(
                "def test_policy(): assert True\n",
                encoding="utf-8",
            )
            case = MutationCase(
                mutation_id="policy_flip",
                source_path=Path("alphapilot_control_console/policy.py"),
                test_path=Path("tests/test_policy.py"),
                original="ALLOWED = True",
                mutated="ALLOWED = False",
                rationale="fixture",
            )
            baseline = subprocess.CompletedProcess(
                args=["pytest"],
                returncode=0,
                stdout="1 passed",
                stderr="",
            )
            completed = subprocess.CompletedProcess(
                args=["pytest"],
                returncode=2,
                stdout="ERROR collecting",
                stderr="",
            )

            with patch(
                "alphapilot_control_console.v62_4_1_mutation_matrix.subprocess.run",
                side_effect=[baseline, completed],
            ):
                result = run_mutation_matrix(
                    repository_root=root,
                    python_executable=Path("python"),
                    output_directory=root / "evidence",
                    cases=[case],
                )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["invalidCount"], 1)
            self.assertEqual(result["killedCount"], 0)


if __name__ == "__main__":
    unittest.main()
