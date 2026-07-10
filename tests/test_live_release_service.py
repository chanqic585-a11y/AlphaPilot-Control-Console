from __future__ import annotations

import hashlib
import json
import unittest

from alphapilot_control_console.live_release_service import validate_live_release_export


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def valid_export() -> dict:
    release = {
        "schemaVersion": "live_release_contract_v1",
        "executionBoundary": {
            "environment": "okx_live_canary_only",
            "manualReleaseApprovalRequired": True,
            "mechanicalExecutionAllowed": True,
            "withdrawAllowed": False,
            "rawCredentialStorageAllowed": False,
        },
        "protectionPolicy": {
            "attachedTakeProfitRequired": True,
            "attachedStopLossRequired": True,
            "minimumRewardRiskRatio": 2.0,
            "privateStateReconciliationRequired": True,
            "restartRecoveryRequired": True,
            "unknownStatePausesEntries": True,
            "killSwitchRequired": True,
        },
    }
    return {
        "schemaVersion": "alphapilot_live_release_v1",
        "liveReleaseId": "release-1",
        "liveReleaseHash": hashlib.sha256(canonical(release).encode("utf-8")).hexdigest(),
        "status": "live_canary_approved",
        "release": release,
    }


class LiveReleaseServiceTests(unittest.TestCase):
    def test_valid_release_is_accepted(self) -> None:
        validate_live_release_export(valid_export())

    def test_checksum_or_withdraw_boundary_is_rejected(self) -> None:
        wrong_hash = valid_export()
        wrong_hash["liveReleaseHash"] = "wrong"
        with self.assertRaises(ValueError):
            validate_live_release_export(wrong_hash)
        withdraw = valid_export()
        withdraw["release"]["executionBoundary"]["withdrawAllowed"] = True
        withdraw["liveReleaseHash"] = hashlib.sha256(canonical(withdraw["release"]).encode("utf-8")).hexdigest()
        with self.assertRaises(PermissionError):
            validate_live_release_export(withdraw)


if __name__ == "__main__":
    unittest.main()
