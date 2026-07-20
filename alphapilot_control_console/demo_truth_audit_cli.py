"""Command-line entry point for the read-only V47 Demo truth audit."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .demo_truth_audit import generate_demo_truth_audit
from .windows_demo_credential_vault import DEMO_CREDENTIAL_VAULT


_DEMO_CREDENTIAL_NAMES = (
    "ALPHAPILOT_OKX_DEMO_API_KEY",
    "ALPHAPILOT_OKX_DEMO_SECRET_KEY",
    "ALPHAPILOT_OKX_DEMO_PASSPHRASE",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--runtime-db", type=Path, required=True)
    parser.add_argument("--universe-db", type=Path, required=True)
    parser.add_argument("--private-read-evidence", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    private_read = None
    if args.private_read_evidence and args.private_read_evidence.is_file():
        private_read = json.loads(args.private_read_evidence.read_text(encoding="utf-8"))
    result = generate_demo_truth_audit(
        release_dir=args.release_dir,
        runtime_db=args.runtime_db,
        universe_db=args.universe_db,
        output_dir=args.output_dir,
        credential_metadata=DEMO_CREDENTIAL_VAULT.metadata(),
        process_credential_injected=all(
            str(os.environ.get(name) or "").strip() for name in _DEMO_CREDENTIAL_NAMES
        ),
        private_read_evidence=private_read,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
