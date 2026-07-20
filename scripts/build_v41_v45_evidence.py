from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.config import get_quant_engine_path
from alphapilot_control_console.v41_v45_evidence import write_v41_v45_evidence_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the V41-V45 dual-track closeout evidence.")
    parser.add_argument("--output", default="reports/v41_v45")
    parser.add_argument("--quant-root", default=str(get_quant_engine_path()))
    parser.add_argument("--screenshots-dir")
    args = parser.parse_args()
    result = write_v41_v45_evidence_bundle(
        Path(args.output),
        quant_root=Path(args.quant_root),
        screenshots_dir=Path(args.screenshots_dir) if args.screenshots_dir else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
