from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from alphapilot_control_console.v62_4_1_mutation_matrix import run_mutation_matrix


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the V62.4.1 source mutation matrix.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    arguments = parser.parse_args()
    result = run_mutation_matrix(
        repository_root=REPOSITORY_ROOT,
        python_executable=arguments.python,
        output_directory=arguments.output,
    )
    print(
        "mutation-matrix "
        f"status={result['status']} "
        f"killed={result['killedCount']}/{result['totalCount']}"
    )
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
