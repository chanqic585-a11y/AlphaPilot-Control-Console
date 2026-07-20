from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.v54_baseline_audit import (
    audit_repository_release_binding,
    read_zip_json,
    reconcile_strategy_order_scope,
    verify_evidence_zip,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the V54 baseline audits.")
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--zip-sha256", required=True)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    verification = verify_evidence_zip(args.zip, expected_sha256=args.zip_sha256)
    release = json.loads(
        (args.evidence_root / "superseding_provisional_release.json").read_text(
            encoding="utf-8"
        )
    )
    binding = audit_repository_release_binding(args.repo, release)
    with zipfile.ZipFile(args.zip, "r") as bundle:
        package_manifest = read_zip_json(bundle, "artifact_manifest.json")
        approval = read_zip_json(
            bundle,
            "evidence/console/top200_minimal_ui/superseding_demo_approval_request.json",
        )
        smoke = read_zip_json(bundle, "final_self_check.json").get("engineeringSmoke") or {}
    scope = reconcile_strategy_order_scope(
        package_manifest=package_manifest,
        approval_request=approval,
        engineering_smoke=smoke,
        strategy_ledger_rows=[],
    )

    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "baseline_evidence_verification.json", verification)
    write_json(args.output / "release_to_final_head_execution_diff_audit.json", binding)
    write_json(args.output / "strategy_order_scope_reconciliation.json", scope)
    print(
        json.dumps(
            {
                "evidence": verification["status"],
                "releaseBinding": binding["status"],
                "orderScope": scope["status"],
                "output": str(args.output.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if {verification["status"], binding["status"], scope["status"]} == {"passed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
