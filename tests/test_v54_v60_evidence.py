from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from alphapilot_control_console.v54_v60_evidence import build_v54_v60_evidence


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class V54V60EvidenceTests(unittest.TestCase):
    def test_builds_verified_truthful_redacted_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            console = root / "console"
            quant = root / "quant"
            docs = root / "docs"
            output = root / "deliveries"

            _write_json(
                console / "data" / "v54_v60" / "release" / "final_superseding_provisional_release.json",
                {"releaseId": "demo-release", "releaseHash": "demo-release-hash"},
            )
            _write_json(
                console / "reports" / "v54_v60" / "v58_live_engineering_smoke" / "live_engineering_smoke_result.json",
                {
                    "status": "completed_canceled_and_reconciled",
                    "orderAttemptCount": 1,
                    "cancelConfirmed": True,
                    "zeroOpenPositions": True,
                    "zeroOpenOrders": True,
                },
            )
            live_root = console / "reports" / "v54_v60" / "v59_v60_live_canary_readiness"
            _write_json(
                live_root / "experimental_live_release.json",
                {
                    "releaseId": "experimental-live",
                    "releaseHash": "experimental-live-hash",
                    "formalPass": False,
                    "productionQualified": False,
                },
            )
            _write_json(
                live_root / "experimental_live_risk_overlay.json",
                {"riskOverlayHash": "risk-overlay-hash", "allocatedCapitalUSDT": 1000},
            )
            _write_json(
                live_root / "adaptive_learning_live_readiness.json",
                {"status": "blocked_not_ready", "passed": False, "blockers": ["qlib_not_run"]},
            )
            _write_json(
                live_root / "live_execution_state.json",
                {
                    "status": "not_run",
                    "approvalStatus": "not_run",
                    "armStatus": "not_run",
                    "strategyOrderStatus": "not_run",
                    "liveEnabled": False,
                    "withdrawAllowed": False,
                },
            )
            for name in ("live_order_ledger.json", "live_fill_ledger.json", "live_position_ledger.json"):
                _write_json(live_root / name, {"status": "not_run", "records": []})
            _write_json(live_root / "exact_live_approval_request.json", {"status": "blocked_not_ready"})

            ui_root = console / "reports" / "v54_v60" / "ui"
            ui_root.mkdir(parents=True)
            (ui_root / "desktop.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            (console / "docs").mkdir(parents=True)
            (console / "docs" / "V13.27.1.54-V13.27.1.60-closeout.md").write_text(
                "# V54-V60 Closeout\n", encoding="utf-8"
            )

            result = build_v54_v60_evidence(
                console_root=console,
                quant_root=quant,
                docs_root=docs,
                output_root=output,
                repository_snapshots={
                    "Console": {"headCommit": "a" * 40, "pushStatus": "verified", "worktreeClean": True},
                    "Quant": {"headCommit": "b" * 40, "pushStatus": "verified", "worktreeClean": True},
                    "Docs": {"headCommit": "c" * 40, "pushStatus": "verified", "worktreeClean": True},
                },
                test_summary={"console": {"status": "passed"}, "quant": {"status": "passed"}},
            )

            self.assertTrue(result["zipPath"].is_file())
            self.assertEqual(64, len(result["sha256"]))
            self.assertEqual(result["sha256"], result["sha256Path"].read_text(encoding="utf-8").split()[0])

            with zipfile.ZipFile(result["zipPath"]) as archive:
                self.assertIsNone(archive.testzip())
                names = set(archive.namelist())
                self.assertIn("final_self_check.json", names)
                self.assertIn("final_closeout_cn.md", names)
                self.assertIn("artifact_manifest.json", names)
                self.assertIn(
                    "evidence/reports_v54_v60/v58_live_engineering_smoke/live_engineering_smoke_result.json",
                    names,
                )
                self.assertIn(
                    "evidence/reports_v54_v60/v59_v60_live_canary_readiness/live_execution_state.json",
                    names,
                )

                self_check = json.loads(archive.read("final_self_check.json"))
                self.assertEqual("completed_canceled_and_reconciled", self_check["v58"]["status"])
                self.assertFalse(self_check["adaptiveLearning"]["passed"])
                self.assertEqual("not_run", self_check["live"]["approvalStatus"])
                self.assertEqual("not_run", self_check["live"]["armStatus"])
                self.assertEqual("not_run", self_check["live"]["strategyOrderStatus"])
                self.assertFalse(self_check["live"]["liveEnabled"])
                self.assertFalse(self_check["live"]["withdrawAllowed"])

                manifest = json.loads(archive.read("artifact_manifest.json"))
                self.assertEqual(len(names) - 1, manifest["artifactCount"])
                self.assertEqual("passed", manifest["verification"]["crc"])
                self.assertEqual("passed", manifest["verification"]["sensitiveDataScan"])
                self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest["artifacts"]))


if __name__ == "__main__":
    unittest.main()
