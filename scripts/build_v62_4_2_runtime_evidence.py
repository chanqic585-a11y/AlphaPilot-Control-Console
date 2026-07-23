from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.v62_4_1_independent_verifiers import canonical_hash
from alphapilot_control_console.v62_4_2_delta_closeout import (
    verify_final_runtime_source_identity,
)
from scripts.build_v62_4_1_runtime_evidence import build_evidence


V62_4_2_MODULE_PATHS = (
    "alphapilot_control_console/v62_4_1_independent_verifiers.py",
    "alphapilot_control_console/v62_4_2_delta_closeout.py",
    "alphapilot_control_console/v62_4_2_failure_critic.py",
    "alphapilot_control_console/v62_4_2_package_builder.py",
    "scripts/build_v62_4_2_runtime_evidence.py",
    "scripts/build_v62_4_2_delta_acceptance.py",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def upgrade_runtime_evidence(
    *,
    repository_root: Path,
    evidence_root: Path,
) -> dict[str, object]:
    """Bind a V62.4.1 no-order capture to the exact V62.4.2 source set."""

    capture_path = evidence_root / "runtime_identity_capture.json"
    summary_path = evidence_root / "runtime_evidence_summary.json"
    receipts_path = evidence_root / "sqlite_backup_receipts.json"
    capture = _read_json(capture_path)
    summary = _read_json(summary_path)
    receipts = _read_json(receipts_path)

    identity = dict(capture.get("runtimeIdentity") or {})
    module_hashes = dict(identity.get("moduleHashes") or {})
    for relative in V62_4_2_MODULE_PATHS:
        module = repository_root / relative
        if not module.is_file():
            raise FileNotFoundError(f"runtime_identity_module_missing:{relative}")
        module_hashes[relative] = _sha256(module)
    identity["moduleHashes"] = dict(sorted(module_hashes.items()))
    capture["schemaVersion"] = "v62_4_2_no_order_runtime_capture_v1"
    capture["runtimeIdentity"] = identity
    capture["runtimeIdentityHash"] = canonical_hash(identity)
    capture["privateReconciliationStatus"] = "not_run_credentials_unavailable"
    capture["artifactHash"] = canonical_hash(
        {key: value for key, value in capture.items() if key != "artifactHash"}
    )
    _write_json(capture_path, capture)

    summary["schemaVersion"] = "v62_4_2_runtime_evidence_bundle_v1"
    summary["privateReconciliationStatus"] = "not_run_credentials_unavailable"
    summary["activeExecutionLeaseCount"] = int(
        capture.get("activeExecutionLeaseCount") or 0
    )
    summary["artifactHash"] = canonical_hash(
        {key: value for key, value in summary.items() if key != "artifactHash"}
    )
    _write_json(summary_path, summary)

    rewritten_receipts: list[dict[str, object]] = []
    if not isinstance(receipts, list):
        raise ValueError("sqlite_backup_receipts_must_be_a_list")
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ValueError("sqlite_backup_receipt_invalid")
        name = Path(str(receipt.get("snapshotPath") or "")).name
        rewritten = dict(receipt)
        rewritten["sourcePath"] = f"runtime_data/{name}"
        rewritten["snapshotPath"] = f"source_snapshots/{name}"
        rewritten_receipts.append(rewritten)
    _write_json(receipts_path, rewritten_receipts)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(r"D:\Codex-Workspace\AlphaPilot-Control-Console\data"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-tag", required=True)
    args = parser.parse_args()
    repository = args.repo_root.resolve()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"fresh_output_directory_required:{output}")
    build_evidence(repository, args.data_root.resolve(), output)
    upgrade_runtime_evidence(repository_root=repository, evidence_root=output)
    verification = verify_final_runtime_source_identity(
        output,
        repository,
        expected_commit=args.expected_commit,
        expected_tag=args.expected_tag,
    )
    _write_json(output / "runtime_source_verification.json", verification)
    print(json.dumps(verification, ensure_ascii=False, sort_keys=True))
    return 0 if verification["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
