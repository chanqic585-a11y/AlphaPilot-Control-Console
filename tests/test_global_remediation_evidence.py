from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.global_remediation_evidence import (
    REQUIRED_EVIDENCE_PATHS,
    build_global_remediation_evidence,
    package_global_remediation_evidence,
)


class GlobalRemediationEvidenceTests(unittest.TestCase):
    def test_builds_complete_truthful_evidence_tree_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            screenshots = root / "screenshots"
            screenshots.mkdir()
            screenshot_paths: dict[str, Path] = {}
            for name in (
                "demo_v2_desktop.png",
                "demo_v2_mobile_390.png",
                "live_v2_desktop.png",
                "live_v2_mobile_390.png",
            ):
                path = screenshots / name
                path.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
                screenshot_paths[name] = path

            output = root / "evidence"
            result = build_global_remediation_evidence(
                output=output,
                baseline={
                    "quant": {"commit": "q" * 40},
                    "console": {"commit": "c" * 40},
                    "docs": {"commit": "d" * 40},
                    "productionRuntime": {"running": True, "demoArmed": False},
                },
                findings=[
                    {
                        "riskId": index,
                        "classification": "already_fixed" if index < 17 else "confirmed_present",
                        "summary": f"risk-{index}",
                        "evidence": [f"source-{index}"],
                    }
                    for index in range(1, 18)
                ],
                runtime_continuity={"running": True, "cutoverPerformed": False},
                shadow_parity={"passed": True, "cutoverPerformed": False},
                adaptive_learning={"status": "blocked_not_ready", "readyCapabilities": 9, "totalCapabilities": 19},
                strategy_factory={"status": "ready", "orderAccess": False},
                risk={"liveArm": False, "withdraw": False},
                security={"remoteWritesDefault": "read_only"},
                database={"integrity": "ok"},
                tests={"status": "passed"},
                git_receipt={"status": "pending"},
                ui_acceptance={"status": "passed", "writeActions": 0},
                screenshot_paths=screenshot_paths,
            )

            self.assertEqual(result["status"], "completed")
            for relative_path in REQUIRED_EVIDENCE_PATHS:
                self.assertTrue((output / relative_path).is_file(), relative_path)
            manifest = json.loads((output / "artifact_manifest.json").read_text(encoding="utf-8"))
            paths = {row["path"] for row in manifest["artifacts"]}
            self.assertNotIn("artifact_manifest.json", paths)
            self.assertIn("runtime_continuity/shadow_parity.json", paths)
            self.assertEqual(len(manifest["artifacts"]), len(REQUIRED_EVIDENCE_PATHS) - 1)
            closeout = (output / "final_closeout_cn.md").read_text(encoding="utf-8")
            self.assertIn("AlphaPilot 全局整改收口", closeout)
            self.assertIn("当前生产 Demo Runtime 未被隔离工作树热改或自动重启", closeout)
            baseline = json.loads(
                (output / "baseline/global_remediation_baseline.json").read_text(encoding="utf-8")
            )
            self.assertEqual(baseline["baseline"]["quant"]["commit"], "q" * 40)

            zip_path = root / "delivery.zip"
            packaged = package_global_remediation_evidence(output, zip_path)
            self.assertEqual(packaged["status"], "completed")
            self.assertTrue(zip_path.is_file())
            self.assertEqual(len(packaged["sha256"]), 64)
            checksum_path = Path(packaged["sha256Path"])
            self.assertTrue(checksum_path.is_file())
            self.assertEqual(
                checksum_path.read_text(encoding="utf-8").strip(),
                f"{packaged['sha256']}  {zip_path.name}",
            )

    def test_rejects_incomplete_or_unknown_finding_classification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                build_global_remediation_evidence(
                    output=Path(directory),
                    baseline={},
                    findings=[{"riskId": 1, "classification": "fixed_enough"}],
                    runtime_continuity={},
                    shadow_parity={},
                    adaptive_learning={},
                    strategy_factory={},
                    risk={},
                    security={},
                    database={},
                    tests={},
                    git_receipt={},
                    ui_acceptance={},
                    screenshot_paths={},
                )


if __name__ == "__main__":
    unittest.main()
