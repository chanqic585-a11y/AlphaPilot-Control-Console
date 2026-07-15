from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import alphapilot_control_console.evolution_demo_service as demo_service
import alphapilot_control_console.demo_workflow_service as workflow_service
from alphapilot_control_console.demo_release_classification import (
    classify_release_files,
    legacy_release_projection,
)
from alphapilot_control_console.demo_release_classification_store import (
    DemoReleaseClassificationStore,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contract(release_id: str, candidate_id: str, family: str) -> dict:
    return {
        "demoReleaseId": release_id,
        "strategyCandidateId": candidate_id,
        "strategy": {"familyKey": family},
    }


class DemoReleaseClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.contract_dir = self.root / "contracts"
        self.contract_dir.mkdir()
        self.paths = []
        for index in (1, 2):
            path = self.contract_dir / f"demo_release_contract_release-{index}.json"
            path.write_text(
                json.dumps(_contract(f"release-{index}", f"candidate-{index}", "same-family"), sort_keys=True),
                encoding="utf-8",
            )
            self.paths.append(path)
        self.classification_path = self.root / "classification.sqlite"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_classification_is_an_overlay_and_preserves_release_and_execution_evidence(self) -> None:
        execution_path = self.root / "execution.sqlite"
        connection = sqlite3.connect(execution_path)
        connection.execute("CREATE TABLE Records (id TEXT PRIMARY KEY, status TEXT)")
        connection.execute("INSERT INTO Records VALUES ('record-1', 'filled')")
        connection.commit()
        connection.close()
        before_names = [path.name for path in self.paths]
        before_bytes = {path.name: path.read_bytes() for path in self.paths}
        before_hashes = {path.name: _sha256(path) for path in self.paths}
        before_execution = execution_path.read_bytes()

        store = DemoReleaseClassificationStore(self.classification_path)
        try:
            result = classify_release_files(self.paths, store=store, reason="phase2_legacy_diagnostic")
            rows = store.list_all()
        finally:
            store.close()

        self.assertEqual(result["classifiedCount"], 2)
        self.assertEqual([path.name for path in self.paths], before_names)
        self.assertEqual({path.name: path.read_bytes() for path in self.paths}, before_bytes)
        self.assertEqual({path.name: _sha256(path) for path in self.paths}, before_hashes)
        self.assertEqual(execution_path.read_bytes(), before_execution)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["releasePurpose"], "legacy_diagnostic")
            self.assertFalse(row["strategyQualification"])
            self.assertFalse(row["promotionEligible"])
            self.assertFalse(row["forwardPerformanceEligible"])
            self.assertFalse(row["demoPerformanceEligible"])

    def test_active_discovery_excludes_legacy_but_audit_projection_keeps_it(self) -> None:
        store = DemoReleaseClassificationStore(self.classification_path)
        try:
            classify_release_files(self.paths, store=store, reason="phase2_legacy_diagnostic")
        finally:
            store.close()

        with patch.object(demo_service, "_contract_paths", return_value=self.paths), patch.object(
            demo_service, "validate_demo_contract", return_value=None
        ):
            active, rejected = demo_service.discover_demo_contracts(
                classification_path=self.classification_path
            )
            history, _ = demo_service.discover_demo_contracts(
                classification_path=self.classification_path,
                include_legacy_diagnostic=True,
            )

        self.assertEqual(active, [])
        self.assertEqual(len(history), 2)
        self.assertEqual(
            [row["reason"] for row in rejected],
            ["legacy_diagnostic", "legacy_diagnostic"],
        )
        projection = legacy_release_projection(
            self.paths,
            classification_path=self.classification_path,
        )
        self.assertEqual(projection["legacyDiagnosticCount"], 2)
        self.assertTrue(
            all(row["variantLabel"] == "同源变体，不是独立假设" for row in projection["releases"])
        )

    def test_demo_workflow_status_exposes_legacy_diagnostics_without_reactivating_them(self) -> None:
        store = DemoReleaseClassificationStore(self.classification_path)
        try:
            classify_release_files(self.paths, store=store, reason="phase2_legacy_diagnostic")
        finally:
            store.close()

        with patch.object(workflow_service, "_build_sources", return_value=({}, {})), patch.object(
            workflow_service,
            "build_demo_workflow_projection",
            return_value={"summary": {"validatingCount": 0}},
        ), patch.object(workflow_service, "_contract_paths", return_value=self.paths), patch.object(
            workflow_service,
            "DEFAULT_CLASSIFICATION_PATH",
            self.classification_path,
        ):
            projection = workflow_service.build_demo_workflow_status()

        diagnostics = projection["legacyReleaseDiagnostics"]
        self.assertEqual(diagnostics["legacyDiagnosticCount"], 2)
        self.assertTrue(diagnostics["readOnly"])
        self.assertFalse(diagnostics["strategyQualification"])


if __name__ == "__main__":
    unittest.main()
