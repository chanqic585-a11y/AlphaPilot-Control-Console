"""Operator CLI for the tested Top100 immutable Demo successor migration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import DATA_DIR
from .demo_release_successor import activate_top100_successors


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate rollback-safe Top100 Demo successors.")
    parser.add_argument("--contract-dir", type=Path, default=DATA_DIR / "demo_release_contracts")
    parser.add_argument("--archive-root", type=Path, default=DATA_DIR / "demo_release_contract_archive")
    parser.add_argument("--auto-execution-db", type=Path, default=DATA_DIR / "unified_auto_execution.sqlite")
    parser.add_argument("--expected-count", type=int, default=10)
    args = parser.parse_args()
    result = activate_top100_successors(
        args.contract_dir,
        args.archive_root,
        args.auto_execution_db,
        expected_count=args.expected_count,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
