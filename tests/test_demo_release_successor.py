from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from alphapilot_control_console.evolution_demo_service import (
    _contract_hash,
    validate_demo_contract,
)
from alphapilot_control_console.demo_release_successor import (
    activate_top100_successors,
    build_top100_successor,
)
from alphapilot_control_console.unified_auto_execution_store import (
    UnifiedAutoExecutionStore,
)


CREATED_AT = datetime(2026, 7, 13, 1, 2, 3, tzinfo=UTC)


def predecessor(index: int) -> dict:
    payload = {
        "schemaVersion": "alphapilot_control_console_demo_v1",
        "demoReleaseId": f"release-top20-{index}",
        "strategyCandidateId": f"strategy-{index}",
        "status": "demo_eligible",
        "releaseMode": "experimental_override",
        "releaseContentHash": f"old-release-hash-{index}",
        "livePromotionAllowed": False,
        "strategy": {
            "familyKey": "breakout",
            "marketDefinition": {
                "timeframe": "1h",
                "universePolicy": {
                    "mode": "okx_usdt_linear_perpetual_full_market",
                    "screeningLimit": 20,
                    "policyVersion": "okx_full_market_policy_v1_top20",
                },
            },
            "forwardSignalPolicy": {
                "policyType": "strategy_family_params_v1",
                "family": "breakout",
                "direction": "long",
                "parameters": {"targetRewardRiskRatio": 2.0},
            },
        },
        "riskEnvelope": {
            "initialEquityUsdt": 1000.0,
            "riskPerTradePercent": 0.25,
            "maxOpenRiskPercent": 1.0,
            "maxOrderNotionalUsdt": 250.0,
            "maxConcurrentPositions": 3,
            "rewardRiskRatio": 2.0,
        },
        "executionBoundary": {
            "environment": "okx_demo_only",
            "automaticDemoExecutionAllowed": True,
            "liveExecutionAllowed": False,
            "withdrawAllowed": False,
            "rawCredentialFieldsAllowed": False,
        },
        "evidence": {"formalBacktestTrades": 220},
    }
    payload["contractHash"] = _contract_hash(payload)
    validate_demo_contract(payload)
    return payload


def write_contract(directory: Path, payload: dict) -> Path:
    path = directory / f"demo_release_contract_{payload['demoReleaseId']}.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


class DemoReleaseSuccessorTests(unittest.TestCase):
    def test_builder_preserves_predecessor_and_creates_valid_top100_identity(self) -> None:
        source = predecessor(1)
        original = copy.deepcopy(source)

        successor = build_top100_successor(source, CREATED_AT)

        self.assertEqual(source, original)
        self.assertNotEqual(successor["demoReleaseId"], source["demoReleaseId"])
        self.assertNotEqual(successor["releaseContentHash"], source["releaseContentHash"])
        self.assertNotEqual(successor["contractHash"], source["contractHash"])
        self.assertEqual(successor["supersedesDemoReleaseId"], source["demoReleaseId"])
        policy = successor["strategy"]["marketDefinition"]["universePolicy"]
        self.assertEqual(policy["screeningLimit"], 100)
        self.assertEqual(policy["policyVersion"], "okx_full_market_policy_v2_top100")
        self.assertEqual(successor["riskEnvelope"], source["riskEnvelope"])
        self.assertEqual(successor["executionBoundary"], source["executionBoundary"])
        self.assertFalse(successor["livePromotionAllowed"])
        validate_demo_contract(successor)

    def test_activation_archives_bytes_retires_only_old_checkpoints_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = root / "active"
            archive = root / "archive"
            active.mkdir()
            originals = [predecessor(1), predecessor(2)]
            original_bytes = {
                payload["demoReleaseId"]: write_contract(active, payload).read_bytes()
                for payload in originals
            }
            db_path = root / "auto.sqlite"
            store = UnifiedAutoExecutionStore(db_path)
            for payload in originals:
                store.save_checkpoint("okx_demo", payload["demoReleaseId"], "1h", "old-close")
            store.save_checkpoint("okx_demo", "unrelated-release", "1h", "keep-close")
            store.close()

            first = activate_top100_successors(
                active,
                archive,
                db_path,
                expected_count=2,
                created_at=CREATED_AT,
            )
            second = activate_top100_successors(
                active,
                archive,
                db_path,
                expected_count=2,
                created_at=CREATED_AT,
            )

            self.assertTrue(first["ok"])
            self.assertTrue(second["alreadyActive"])
            active_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in active.glob("*.json")]
            self.assertEqual(len(active_payloads), 2)
            self.assertTrue(all(row["strategy"]["marketDefinition"]["universePolicy"]["screeningLimit"] == 100 for row in active_payloads))
            manifest_path = Path(first["manifestPath"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["migrations"]), 2)
            for payload in originals:
                archived = manifest_path.parent / f"demo_release_contract_{payload['demoReleaseId']}.json"
                self.assertEqual(archived.read_bytes(), original_bytes[payload["demoReleaseId"]])
                self.assertEqual(
                    hashlib.sha256(archived.read_bytes()).hexdigest(),
                    next(row["predecessorFileSha256"] for row in manifest["migrations"] if row["predecessorDemoReleaseId"] == payload["demoReleaseId"]),
                )
            reopened = UnifiedAutoExecutionStore(db_path)
            for payload in originals:
                self.assertIsNone(reopened.checkpoint("okx_demo", payload["demoReleaseId"], "1h"))
            self.assertEqual(reopened.checkpoint("okx_demo", "unrelated-release", "1h"), "keep-close")
            self.assertEqual(reopened.list_events("okx_demo")[0]["eventType"], "demo_top100_successors_activated")
            reopened.close()

    def test_activation_rolls_back_files_and_database_after_mid_swap_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = root / "active"
            archive = root / "archive"
            active.mkdir()
            originals = [predecessor(1), predecessor(2)]
            original_bytes = {
                payload["demoReleaseId"]: write_contract(active, payload).read_bytes()
                for payload in originals
            }
            db_path = root / "auto.sqlite"
            store = UnifiedAutoExecutionStore(db_path)
            store.save_checkpoint("okx_demo", originals[0]["demoReleaseId"], "1h", "old-close")
            store.close()
            calls = 0

            def fail_mid_swap(source: Path, target: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 4:
                    raise OSError("simulated swap failure")
                source.replace(target)

            with patch(
                "alphapilot_control_console.demo_release_successor._replace_file",
                side_effect=fail_mid_swap,
            ):
                with self.assertRaisesRegex(RuntimeError, "rolled back"):
                    activate_top100_successors(
                        active,
                        archive,
                        db_path,
                        expected_count=2,
                        created_at=CREATED_AT,
                    )

            restored = {
                json.loads(path.read_text(encoding="utf-8"))["demoReleaseId"]: path.read_bytes()
                for path in active.glob("demo_release_contract_*.json")
            }
            self.assertEqual(restored, original_bytes)
            reopened = UnifiedAutoExecutionStore(db_path)
            self.assertEqual(
                reopened.checkpoint("okx_demo", originals[0]["demoReleaseId"], "1h"),
                "old-close",
            )
            reopened.close()


if __name__ == "__main__":
    unittest.main()
