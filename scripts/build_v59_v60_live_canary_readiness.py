from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.experimental_live_canary_release import (
    build_experimental_live_canary_bundle,
    write_experimental_live_canary_bundle,
)


DEFAULT_PROFILE = ROOT / "data" / "v54_v60" / "live_canary" / "live_experiment_profile_v1.json"
DEFAULT_SOURCE_RELEASE = (
    ROOT / "data" / "v54_v60" / "release" / "final_superseding_provisional_release.json"
)
DEFAULT_SMOKE_RESULT = (
    ROOT / "reports" / "v54_v60" / "v58_live_engineering_smoke" / "live_engineering_smoke_result.json"
)
DEFAULT_OBSERVER_BINDING = ROOT / "reports" / "v55_1_adaptive_learning" / "observer_sidecar_binding.json"
DEFAULT_ADAPTIVE_READINESS = (
    ROOT / "reports" / "v55_1_adaptive_learning" / "adaptive_learning_live_readiness.json"
)
DEFAULT_OUTPUT = ROOT / "reports" / "v54_v60" / "v59_v60_live_canary_readiness"


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build immutable V59/V60 Live Canary readiness evidence")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--source-demo-release", type=Path, default=DEFAULT_SOURCE_RELEASE)
    parser.add_argument("--smoke-result", type=Path, default=DEFAULT_SMOKE_RESULT)
    parser.add_argument("--observer-binding", type=Path, default=DEFAULT_OBSERVER_BINDING)
    parser.add_argument("--adaptive-readiness", type=Path, default=DEFAULT_ADAPTIVE_READINESS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--generated-at", default=None)
    args = parser.parse_args()

    bundle = build_experimental_live_canary_bundle(
        profile_input=_read(args.profile),
        source_demo_release=_read(args.source_demo_release),
        smoke_result=_read(args.smoke_result),
        observer_binding=_read(args.observer_binding),
        adaptive_learning_readiness=_read(args.adaptive_readiness),
        generated_at=str(args.generated_at or _now()),
    )
    manifest = write_experimental_live_canary_bundle(args.output, bundle)
    print(
        json.dumps(
            {
                "status": bundle["status"],
                "releaseId": bundle["liveRelease"]["releaseId"],
                "releaseHash": bundle["liveRelease"]["releaseHash"],
                "riskOverlayHash": bundle["riskOverlay"]["riskOverlayHash"],
                "environmentHash": bundle["environment"]["environmentHash"],
                "universePolicyHash": bundle["universePolicy"]["universePolicyHash"],
                "adaptiveLearningPassed": bundle["adaptiveLearningReadiness"]["passed"],
                "requiredConfirmation": bundle["approvalRequest"]["requiredConfirmation"],
                "artifactCount": manifest["artifactCount"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
