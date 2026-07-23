from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.v62_4_1_ui_evidence import (  # noqa: E402
    build_current_pilot_projection,
    build_provider_smoke_summary,
)


def _write_json(path: Path, payload: dict) -> dict[str, object]:
    body = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(body)
    temporary.replace(path)
    return {
        "path": path.name,
        "sha256": sha256(body).hexdigest(),
        "bytes": len(body),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-summary", required=True, type=Path)
    parser.add_argument("--formal-handoff", required=True, type=Path)
    parser.add_argument("--provider-smoke", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts = [
        _write_json(
            output_root / "current_pilot_projection.json",
            build_current_pilot_projection(
                args.campaign_summary.resolve(),
                args.formal_handoff.resolve(),
            ),
        ),
        _write_json(
            output_root / "provider_smoke_summary.json",
            build_provider_smoke_summary(args.provider_smoke.resolve()),
        ),
    ]
    manifest = {
        "schemaVersion": "alphapilot_v62_4_1_ui_evidence_manifest_v1",
        "artifacts": artifacts,
        "artifactCount": len(artifacts),
        "readOnly": True,
        "executionAuthorized": False,
        "approvalGranted": False,
        "demoArm": False,
        "strategyOrderCount": 0,
        "liveEnabled": False,
        "withdrawEnabled": False,
    }
    _write_json(output_root / "artifact_manifest.json", manifest)
    print(json.dumps({"status": "completed", **manifest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
