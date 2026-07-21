"""Build the V59 Demo/Live feature-pipeline parity evidence artifact."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from alphapilot_control_console.adaptive_learning_feature_parity import (
    build_feature_pipeline_parity_evidence,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adaptive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    root = args.adaptive_root.expanduser().resolve()
    model_registry = _load_json(root / "model_registry.json")
    model_policy = dict(
        model_registry.get("activeLiveModelPolicy")
        or model_registry.get("activeDemoModelPolicy")
        or {}
    )
    result = build_feature_pipeline_parity_evidence(
        factor_registry=_load_json(root / "production_factor_registry.json"),
        feature_schema=_load_json(root / "production_feature_schema.json"),
        model_policy=model_policy,
    )
    output = args.output.expanduser().resolve()
    _write_json_atomic(output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "passed": result["passed"],
                "evidenceHash": result["evidenceHash"],
                "output": str(output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
