from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.adaptive_learning_governance_evidence import (
    generate_adaptive_learning_governance_evidence,
)


DEFAULT_SOURCE = ROOT / "reports" / "v54_v60" / "v59_v60_live_canary_readiness"
DEFAULT_OUTPUT_ROOT = ROOT / "reports" / "v60_1_adaptive_learning_governance"


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_id(generated_at: str) -> str:
    return generated_at.replace("-", "").replace(":", "").replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a non-mutating adaptive-learning Live governance overlay"
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--technical-snapshot", type=Path, default=None)
    parser.add_argument("--generated-at", default=None)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    generated_at = str(args.generated_at or _now())
    output = args.output_root / str(args.run_id or _run_id(generated_at))
    result = generate_adaptive_learning_governance_evidence(
        args.source,
        output,
        generated_at=generated_at,
        technical_snapshot_path=args.technical_snapshot,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
