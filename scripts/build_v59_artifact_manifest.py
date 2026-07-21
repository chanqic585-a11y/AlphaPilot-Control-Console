"""Build the V59 adaptive-learning evidence artifact manifest."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from alphapilot_control_console.v59_artifact_manifest import (
    build_artifact_manifest,
    write_artifact_manifest,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--status", default="blocked_not_ready")
    parser.add_argument("--generated-at")
    args = parser.parse_args(argv)

    root = args.root.expanduser().resolve()
    output = (args.output or root / "artifact_manifest.json").expanduser().resolve()
    manifest = build_artifact_manifest(
        root,
        generated_at=args.generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        status=args.status,
    )
    write_artifact_manifest(output, manifest)
    print(
        json.dumps(
            {
                "fileCount": manifest["fileCount"],
                "manifestHash": manifest["manifestHash"],
                "output": str(output),
                "status": manifest["status"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
