from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from alphapilot_control_console.v54_baseline_audit import (
    BaselineAuditError,
    build_release_to_head_execution_diff_audit,
    reconcile_strategy_order_scope,
    verify_evidence_zip,
)


def _json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


class V54BaselineAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build_evidence_zip(self) -> Path:
        artifact = _json_bytes({"status": "passed", "strategyOrderCount": 0})
        manifest = {
            "schemaVersion": "fixture_manifest_v1",
            "status": "complete_waiting_exact_release_approval",
            "fileCount": 1,
            "files": [
                {
                    "path": "evidence/final_self_check.json",
                    "bytes": len(artifact),
                    "sha256": hashlib.sha256(artifact).hexdigest(),
                }
            ],
        }
        path = self.root / "evidence.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("artifact_manifest.json", _json_bytes(manifest))
            bundle.writestr("evidence/final_self_check.json", artifact)
        return path

    def test_verifies_zip_hash_crc_manifest_and_every_declared_artifact(self) -> None:
        path = self._build_evidence_zip()
        expected_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()

        result = verify_evidence_zip(path, expected_sha256=expected_sha256)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["zipSha256"], expected_sha256)
        self.assertTrue(result["crcPassed"])
        self.assertEqual(result["declaredArtifactCount"], 1)
        self.assertEqual(result["verifiedArtifactCount"], 1)
        self.assertEqual(result["missingArtifacts"], [])
        self.assertEqual(result["hashMismatches"], [])

    def test_rejects_an_unexpected_zip_hash(self) -> None:
        path = self._build_evidence_zip()

        with self.assertRaisesRegex(BaselineAuditError, "evidence ZIP hash mismatch"):
            verify_evidence_zip(path, expected_sha256="0" * 64)

    def test_release_to_head_diff_separates_execution_and_projection_changes(self) -> None:
        release = {
            "releaseId": "release_fixture",
            "releaseHash": "release_hash_fixture",
            "executionIdentity": {"consoleExecutionCommit": "base_commit"},
        }

        audit = build_release_to_head_execution_diff_audit(
            release,
            final_head="final_head",
            changed_files=[
                "alphapilot_control_console/top200_minimal_ui_projection.py",
                "alphapilot_control_console/http_app.py",
                "web/top200-minimal-ui.js",
            ],
        )

        self.assertEqual(audit["status"], "passed")
        self.assertEqual(audit["releaseExecutionCommit"], "base_commit")
        self.assertEqual(audit["finalHead"], "final_head")
        self.assertEqual(audit["executionSensitiveChangedFiles"], [])
        self.assertIn(
            "alphapilot_control_console/http_app.py",
            audit["controlOrProjectionChangedFiles"],
        )

    def test_release_to_head_diff_blocks_execution_engine_changes(self) -> None:
        release = {
            "releaseId": "release_fixture",
            "releaseHash": "release_hash_fixture",
            "executionIdentity": {"consoleExecutionCommit": "base_commit"},
        }

        audit = build_release_to_head_execution_diff_audit(
            release,
            final_head="final_head",
            changed_files=["alphapilot_control_console/demo_execution_engine.py"],
        )

        self.assertEqual(audit["status"], "blocked")
        self.assertEqual(
            audit["executionSensitiveChangedFiles"],
            ["alphapilot_control_console/demo_execution_engine.py"],
        )

    def test_reconciles_engineering_smoke_and_strategy_order_scopes(self) -> None:
        audit = reconcile_strategy_order_scope(
            package_manifest={"strategyOrderCount": 0},
            approval_request={"strategyOrderCount": 0, "orderCount": 0},
            engineering_smoke={"orderAttempts": 3, "fills": 2},
            strategy_ledger_rows=[],
        )

        self.assertEqual(audit["status"], "passed")
        self.assertEqual(audit["strategyScope"]["orderCount"], 0)
        self.assertEqual(audit["engineeringSmokeScope"]["orderAttemptCount"], 3)
        self.assertTrue(audit["engineeringSmokeScope"]["excludedFromStrategyEvidence"])

    def test_blocks_strategy_order_scope_disagreement(self) -> None:
        audit = reconcile_strategy_order_scope(
            package_manifest={"strategyOrderCount": 0},
            approval_request={"strategyOrderCount": 0, "orderCount": 0},
            engineering_smoke={"orderAttempts": 3, "fills": 2},
            strategy_ledger_rows=[{"orderId": "strategy_order_1"}],
        )

        self.assertEqual(audit["status"], "blocked")
        self.assertIn("strategy_order_count_mismatch", audit["blockers"])

    def test_builder_script_runs_directly_from_repository_root(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [
                sys.executable,
                str(repository_root / "scripts" / "build_v54_baseline_audit.py"),
                "--help",
            ],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Build the V54 baseline audits", completed.stdout)


if __name__ == "__main__":
    unittest.main()
