from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.global_remediation_evidence import (
    build_global_remediation_evidence,
    package_global_remediation_evidence,
)


SCREENSHOT_NAMES = (
    "demo_v2_desktop.png",
    "demo_v2_mobile_390.png",
    "live_v2_desktop.png",
    "live_v2_mobile_390.png",
)


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the redacted AlphaPilot Global Remediation evidence ZIP."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--screenshots", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-zip", type=Path, required=True)
    args = parser.parse_args()

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError(f"Output directory must be empty: {args.output_dir}")

    payload = _read_object(args.input)
    screenshot_paths = {name: args.screenshots / name for name in SCREENSHOT_NAMES}
    result = build_global_remediation_evidence(
        output=args.output_dir,
        baseline=payload["baseline"],
        findings=payload["findings"],
        runtime_continuity=payload["runtimeContinuity"],
        shadow_parity=payload["shadowParity"],
        adaptive_learning=payload["adaptiveLearning"],
        strategy_factory=payload["strategyFactory"],
        risk=payload["risk"],
        security=payload["security"],
        database=payload["database"],
        tests=payload["tests"],
        git_receipt=payload["gitReceipt"],
        ui_acceptance=payload["uiAcceptance"],
        screenshot_paths=screenshot_paths,
    )
    package = package_global_remediation_evidence(args.output_dir, args.output_zip)
    print(json.dumps({**result, **package}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
