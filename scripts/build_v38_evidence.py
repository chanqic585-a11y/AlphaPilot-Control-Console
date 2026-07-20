from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.config import get_quant_engine_path
from alphapilot_control_console.v38_evidence import write_v38_evidence_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build V38 isolated Demo and Strategy Lab evidence.")
    parser.add_argument("--output", default="reports/v38")
    parser.add_argument("--quant-root", default=str(get_quant_engine_path()))
    args = parser.parse_args()
    result = write_v38_evidence_bundle(Path(args.output), quant_root=Path(args.quant_root))
    print(json.dumps(result["finalRoute"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
