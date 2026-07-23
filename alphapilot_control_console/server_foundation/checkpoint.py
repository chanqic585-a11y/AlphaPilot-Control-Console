"""Atomic role checkpoints with strict resume identity validation."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import FoundationRole


class CheckpointIdentityMismatch(PermissionError):
    """Raised when a checkpoint belongs to another frozen runtime identity."""


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


class FoundationCheckpointStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, role: FoundationRole) -> Path:
        return self.root / f"{FoundationRole(role).value}.checkpoint.json"

    def write(
        self,
        *,
        role: FoundationRole,
        manifest_hash: str,
        config_hash: str,
        fencing_token: int,
        progress: dict[str, Any],
    ) -> dict[str, Any]:
        role = FoundationRole(role)
        payload: dict[str, Any] = {
            "schemaVersion": "alphapilot_v63_foundation_checkpoint_v1",
            "role": role.value,
            "manifestHash": manifest_hash,
            "configHash": config_hash,
            "fencingToken": int(fencing_token),
            "progress": dict(progress),
            "writtenAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
        }
        payload["checkpointHash"] = _hash(payload)
        target = self.path_for(role)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, target)
        return payload

    def load(
        self,
        *,
        role: FoundationRole,
        expected_manifest_hash: str,
        expected_config_hash: str,
        expected_fencing_token: int,
    ) -> dict[str, Any]:
        target = self.path_for(role)
        payload = json.loads(target.read_text(encoding="utf-8"))
        checkpoint_hash = str(payload.pop("checkpointHash", ""))
        if checkpoint_hash != _hash(payload):
            raise CheckpointIdentityMismatch("checkpoint_hash_mismatch")
        payload["checkpointHash"] = checkpoint_hash
        expected = {
            "role": FoundationRole(role).value,
            "manifestHash": expected_manifest_hash,
            "configHash": expected_config_hash,
            "fencingToken": int(expected_fencing_token),
        }
        mismatches = [
            key
            for key, value in expected.items()
            if payload.get(key) != value
        ]
        if mismatches:
            raise CheckpointIdentityMismatch(
                "checkpoint_identity_mismatch:" + ",".join(mismatches)
            )
        return payload

    def load_for_resume(
        self,
        *,
        role: FoundationRole,
        expected_manifest_hash: str,
        expected_config_hash: str,
        current_fencing_token: int,
    ) -> dict[str, Any]:
        target = self.path_for(role)
        payload = json.loads(target.read_text(encoding="utf-8"))
        checkpoint_hash = str(payload.pop("checkpointHash", ""))
        if checkpoint_hash != _hash(payload):
            raise CheckpointIdentityMismatch("checkpoint_hash_mismatch")
        payload["checkpointHash"] = checkpoint_hash
        expected = {
            "role": FoundationRole(role).value,
            "manifestHash": expected_manifest_hash,
            "configHash": expected_config_hash,
        }
        mismatches = [
            key
            for key, value in expected.items()
            if payload.get(key) != value
        ]
        if mismatches:
            raise CheckpointIdentityMismatch(
                "checkpoint_identity_mismatch:" + ",".join(mismatches)
            )
        checkpoint_fencing_token = int(payload.get("fencingToken", 0))
        if checkpoint_fencing_token >= int(current_fencing_token):
            raise CheckpointIdentityMismatch(
                "checkpoint_fencing_token_is_not_prior"
            )
        return payload
