from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.v62_4_1_playwright_acceptance import (
    run_playwright_acceptance,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run V62.4.1 Playwright acceptance against the production route."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chrome", type=Path, required=True)
    arguments = parser.parse_args()
    report = run_playwright_acceptance(
        base_url=arguments.base_url,
        output_directory=arguments.output,
        chrome_executable=arguments.chrome,
    )
    print(
        f"playwright-production-route status={report['status']} "
        f"viewports={len(report['snapshots'])}"
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
