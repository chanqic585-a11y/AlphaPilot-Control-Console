from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.v59_artifact_manifest import build_artifact_manifest


class V59ArtifactManifestTests(unittest.TestCase):
    def test_manifest_hashes_files_and_excludes_itself(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "evidence.json").write_text(
                "{}\n", encoding="utf-8", newline="\n"
            )
            nested = root / "nested"
            nested.mkdir()
            (nested / "report.md").write_text(
                "# Report\n", encoding="utf-8", newline="\n"
            )
            (root / "artifact_manifest.json").write_text("stale", encoding="utf-8")

            manifest = build_artifact_manifest(
                root,
                generated_at="2026-07-21T12:00:00Z",
                status="blocked_not_ready",
            )

            self.assertEqual(manifest["fileCount"], 2)
            self.assertEqual(
                [row["path"] for row in manifest["files"]],
                ["evidence.json", "nested/report.md"],
            )
            self.assertEqual(
                manifest["files"][0]["sha256"],
                hashlib.sha256(b"{}\n").hexdigest(),
            )
            self.assertEqual(manifest["selfReferenceExclusions"], ["artifact_manifest.json"])
            self.assertTrue(manifest["manifestHash"].startswith("v59_artifact_manifest_"))


if __name__ == "__main__":
    unittest.main()
