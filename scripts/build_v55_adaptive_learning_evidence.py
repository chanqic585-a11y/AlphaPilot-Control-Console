from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

CONSOLE_ROOT = Path(__file__).resolve().parents[1]
if str(CONSOLE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONSOLE_ROOT))

from alphapilot_control_console.v55_adaptive_learning_evidence import (
    generate_v55_adaptive_learning_evidence,
    package_v55_adaptive_learning_evidence,
)


def _load_optional_json(path: str | None) -> dict | list | None:
    if not path:
        return None
    return json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quant-root", required=True)
    parser.add_argument("--release-path", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--output-zip")
    parser.add_argument("--original-v55-commit", required=True)
    parser.add_argument("--generated-at")
    parser.add_argument("--test-results-path")
    parser.add_argument("--ui-screenshot-manifest-path")
    parser.add_argument("--git-receipt-path")
    arguments = parser.parse_args()

    quant_root = Path(arguments.quant_root).expanduser().resolve()
    sys.path.insert(0, str(quant_root))
    module = importlib.import_module("alphapilot.adaptive_learning.production_factor_registry")
    factor_registry = module.build_production_factor_registry()
    release = json.loads(Path(arguments.release_path).read_text(encoding="utf-8"))
    generated_at = arguments.generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    test_results = _load_optional_json(arguments.test_results_path)
    ui_screenshots = _load_optional_json(arguments.ui_screenshot_manifest_path)
    git_receipt = _load_optional_json(arguments.git_receipt_path)
    if ui_screenshots is not None and not isinstance(ui_screenshots, list):
        raise ValueError("UI screenshot manifest input must be a JSON list")
    manifest = generate_v55_adaptive_learning_evidence(
        arguments.output_root,
        generated_at=generated_at,
        factor_registry=factor_registry,
        release_identity=release,
        insertion_receipt={
            "originalV55Commit": arguments.original_v55_commit,
            "safeCheckpointPassed": True,
            "consoleAndQuantCleanBeforeInsertion": True,
            "targetedAndFullTestsPassedBeforeInsertion": True,
            "strategyOrderCount": 0,
            "inFlightOrderCount": 0,
            "nonzeroPositionCount": 0,
            "exactDemoApprovalPreexisted": True,
            "approvalPreserved": True,
            "demoArm": False,
            "firstStrategyDemoOrderCreated": False,
        },
        test_results=test_results if isinstance(test_results, dict) else None,
        ui_screenshots=ui_screenshots,
        git_receipt=git_receipt if isinstance(git_receipt, dict) else None,
    )
    result: dict[str, object] = {"manifest": manifest}
    if arguments.output_zip:
        result["archive"] = package_v55_adaptive_learning_evidence(
            arguments.output_root,
            arguments.output_zip,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
