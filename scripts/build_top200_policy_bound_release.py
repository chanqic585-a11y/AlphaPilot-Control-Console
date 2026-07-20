from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.top200_policy_bound_release import (
    build_policy_bound_release,
    write_policy_bound_release_artifacts,
)


def _read(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a policy-bound successor to a frozen TOP200 Demo release."
    )
    parser.add_argument("--release", required=True, type=Path)
    parser.add_argument("--approval-request", required=True, type=Path)
    parser.add_argument("--generated-at")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generated_at = args.generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    result = build_policy_bound_release(
        source_release=_read(args.release),
        source_approval_request=_read(args.approval_request),
        generated_at=generated_at,
    )
    manifest = write_policy_bound_release_artifacts(args.output, result)
    print(
        json.dumps(
            {
                "status": result["hashAudit"]["status"],
                "releaseId": result["release"]["releaseId"],
                "releaseHash": result["release"]["releaseHash"],
                "approvalRequestHash": result["approvalRequest"]["requestHash"],
                "artifactCount": manifest["artifactCount"],
                "output": str(args.output.resolve()),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if result["hashAudit"]["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
