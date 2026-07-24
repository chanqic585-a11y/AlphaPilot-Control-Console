from __future__ import annotations

import json
from pathlib import Path

from scripts.build_v63_1_state_driven_ui_evidence import (
    REQUIRED_JSON_ARTIFACTS,
    build_evidence,
)


def test_v63_1_evidence_builder_emits_required_contracts(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"
    validation_root.mkdir()
    (validation_root / "control-desktop.png").write_bytes(b"png-evidence")
    output_root = tmp_path / "evidence"

    manifest = build_evidence(
        output_root=output_root,
        validation_root=validation_root,
        repository_commit="test-commit",
    )

    for filename in REQUIRED_JSON_ARTIFACTS:
        payload = json.loads((output_root / filename).read_text(encoding="utf-8"))
        assert payload["schemaVersion"]
        assert payload["generatedAt"]
        assert payload["repositoryCommit"] == "test-commit"
        assert payload["sourceHashes"]
        assert payload["status"] in {"passed", "not_run"}
        assert isinstance(payload["knownLimitations"], list)

    reliability = json.loads(
        (output_root / "reliability_hardening_audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert reliability["cursorPagination"]["allListsBounded"] is True
    assert reliability["stateVersionMismatch"]["httpStatus"] == 409
    assert reliability["connectionLiveness"]["staleAfterSeconds"] == 3

    assert (output_root / "v63_1_closeout.md").is_file()
    assert (output_root / "artifact_manifest.json").is_file()
    assert manifest["executionAuthorized"] is False
