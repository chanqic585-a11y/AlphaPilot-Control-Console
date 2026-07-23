from __future__ import annotations

import json
from pathlib import Path

import pytest

from alphapilot_control_console.v62_4_2_package_builder import (
    build_artifact_manifest,
    copy_current_quality_evidence,
    create_fresh_package_root,
    verify_manifest_coverage,
)


def test_create_fresh_package_root_rejects_incremental_append(
    tmp_path: Path,
) -> None:
    output = tmp_path / "delta"
    output.mkdir()
    (output / "stale.txt").write_text("stale", encoding="utf-8")

    with pytest.raises(FileExistsError, match="fresh_output_directory_required"):
        create_fresh_package_root(output)


def test_manifest_covers_all_files_except_itself(tmp_path: Path) -> None:
    root = create_fresh_package_root(tmp_path / "delta")
    (root / "00_START_HERE").mkdir()
    (root / "00_START_HERE" / "state.json").write_text(
        json.dumps({"status": "complete"}) + "\n",
        encoding="utf-8",
    )
    (root / "07_final").mkdir()
    (root / "07_final" / "final_self_check.md").write_text(
        "# Final\n",
        encoding="utf-8",
    )
    (root / "03_matchability").mkdir()
    (root / "03_matchability" / "artifact_manifest.json").write_text(
        json.dumps({"schemaVersion": "historical_manifest_v1"}) + "\n",
        encoding="utf-8",
    )

    manifest = build_artifact_manifest(root)
    manifest_path = root / "artifact_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    assert verify_manifest_coverage(root, manifest)["passed"] is True
    assert [row["relativePath"] for row in manifest["artifacts"]] == [
        "00_START_HERE/state.json",
        "03_matchability/artifact_manifest.json",
        "07_final/final_self_check.md",
    ]
    assert "artifact_manifest.json" not in {
        row["relativePath"] for row in manifest["artifacts"]
    }


def test_copy_current_quality_evidence_includes_only_referenced_logs(
    tmp_path: Path,
) -> None:
    source = tmp_path / "quality"
    source.mkdir()
    checks = source / "current_quality_checks.json"
    checks.write_text(
        json.dumps(
            {
                "passed": True,
                "checks": {
                    "pytest": {"status": "passed", "log": "pytest.log"},
                    "compileall": {
                        "status": "passed",
                        "log": "compileall.log",
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (source / "pytest.log").write_text("951 passed\n", encoding="utf-8")
    (source / "compileall.log").write_text("passed\n", encoding="utf-8")
    (source / "unreferenced.txt").write_text("do not copy\n", encoding="utf-8")

    destination = tmp_path / "package" / "05_strategy_and_quality"
    copied = copy_current_quality_evidence(checks, destination)

    assert copied == [
        "compileall.log",
        "pytest.log",
        "v62_4_2_current_checks.json",
    ]
    assert sorted(path.name for path in destination.iterdir()) == copied
