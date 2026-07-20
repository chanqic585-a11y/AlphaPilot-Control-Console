from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphapilot_control_console.top200_minimal_ui_projection import (
    Top200MinimalUiProjection,
    write_top200_minimal_ui_projection_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build read-only TOP200 Strategy and Demo UI projections."
    )
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = write_top200_minimal_ui_projection_artifacts(
        Top200MinimalUiProjection(args.evidence_root),
        args.output_dir,
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
