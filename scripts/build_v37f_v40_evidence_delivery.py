from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.v37f_v40_evidence_delivery import (
    build_evidence_delivery,
    collect_repository_snapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the V37F-V40 independent-audit evidence delivery.")
    parser.add_argument("--quant-root", required=True)
    parser.add_argument("--console-root", default=str(ROOT))
    parser.add_argument("--docs-root", required=True)
    parser.add_argument("--requirements", required=True)
    parser.add_argument("--screenshots", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--git", required=True)
    parser.add_argument("--test-summary", required=True)
    args = parser.parse_args()

    roots = {
        "Quant": Path(args.quant_root),
        "Console": Path(args.console_root),
        "Docs": Path(args.docs_root),
    }
    snapshots = {
        name: collect_repository_snapshot(path, git_executable=args.git)
        for name, path in roots.items()
    }
    test_summary = json.loads(Path(args.test_summary).read_text(encoding="utf-8"))
    result = build_evidence_delivery(
        quant_root=roots["Quant"],
        console_root=roots["Console"],
        docs_root=roots["Docs"],
        requirements_path=Path(args.requirements),
        screenshot_root=Path(args.screenshots),
        output_root=Path(args.output),
        repository_snapshots=snapshots,
        test_summary=test_summary,
    )
    print(json.dumps({
        "outerZip": str(result["outerZip"]),
        "sha256": result["outerZipSha256"],
        "finalRoute": result["finalRoute"]["finalRoute"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
