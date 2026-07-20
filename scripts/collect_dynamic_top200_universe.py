"""Collect and persist one immutable OKX Demo TOP200 universe snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from alphapilot_control_console.credential_runtime import OkxDemoCredentials
from alphapilot_control_console.dynamic_top200_collector import (
    collect_dynamic_top200_snapshot,
)
from alphapilot_control_console.exchange_connectors.okx_demo_client import OkxDemoClient
from alphapilot_control_console.windows_demo_credential_vault import (
    DEMO_CREDENTIAL_VAULT,
)


def _write(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    arguments = parser.parse_args()
    output_dir = Path(arguments.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle = DEMO_CREDENTIAL_VAULT.load()
    if bundle is None:
        raise SystemExit("OKX Demo credential vault is empty")
    client = OkxDemoClient(
        OkxDemoCredentials(
            apiKey=bundle.apiKey,
            secretKey=bundle.secretKey,
            passphrase=bundle.passphrase,
        )
    )
    result = collect_dynamic_top200_snapshot(
        private_client=client,
        snapshot_dir=output_dir / "daily_snapshots",
    )
    policy = result["policy"]
    snapshot = result["snapshot"]
    audit = result["readinessAudit"]
    _write(output_dir / "top200_demo_universe_policy.json", policy)
    _write(
        output_dir / "top200_demo_universe_policy_hash.json",
        {
            "schemaVersion": "top200_demo_universe_policy_hash_v1",
            "policyId": policy["policyId"],
            "policyHash": policy["policyHash"],
        },
    )
    _write(output_dir / "initial_top200_demo_universe_snapshot.json", snapshot)
    _write(output_dir / "top200_universe_readiness_audit.json", audit)
    print(
        json.dumps(
            {
                "status": audit["collectionStatus"],
                "actualInstrumentCount": snapshot["actualInstrumentCount"],
                "policyHash": policy["policyHash"],
                "snapshotHash": snapshot["snapshotHash"],
                "snapshotReused": result["freeze"]["reused"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
