from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.demo_engineering_smoke_contract import (
    build_demo_engineering_smoke_contract,
    build_v41_v45_engineering_smoke_approval_overlay,
    build_v41_v45_engineering_smoke_contract,
    validate_demo_engineering_smoke_contract,
    validate_v41_v45_engineering_smoke_contract,
)


class DemoEngineeringSmokeContractTests(unittest.TestCase):
    def test_builds_deterministic_hash_addressed_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            first = build_demo_engineering_smoke_contract(
                createdAt="2026-07-15T00:00:00+00:00",
                outputDir=output_dir,
            )
            path = output_dir / f"{first['releaseHash']}.json"
            before = path.read_bytes()
            second = build_demo_engineering_smoke_contract(
                createdAt="2026-07-15T00:00:00+00:00",
                outputDir=output_dir,
            )

            self.assertEqual(first, second)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(json.loads(before.decode("utf-8")), first)
            self.assertTrue(first["releaseId"].startswith("demo-engineering-smoke-"))
            self.assertEqual(first["demoPurpose"], "engineering_smoke")
            self.assertEqual(first["evidenceClass"], "demo_engineering_smoke")

    def test_rejects_any_capability_that_could_qualify_or_promote_a_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            contract = build_demo_engineering_smoke_contract(
                createdAt="2026-07-15T00:00:00+00:00",
                outputDir=Path(temporary),
            )
        forbidden = {
            "strategyQualification": True,
            "promotionEligible": True,
            "forwardPerformanceEligible": True,
            "liveExecutionAllowed": True,
            "withdrawAllowed": True,
            "maximumConcurrentPositions": 2,
            "maximumAttempts": 0,
            "minimumOrderOnly": False,
            "environment": "live",
        }
        for field, value in forbidden.items():
            with self.subTest(field=field):
                changed = {**contract, field: value}
                with self.assertRaises((ValueError, PermissionError)):
                    validate_demo_engineering_smoke_contract(changed)

    def test_rejects_contract_with_changed_content_or_sensitive_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            contract = build_demo_engineering_smoke_contract(
                createdAt="2026-07-15T00:00:00+00:00",
                outputDir=Path(temporary),
            )
        changed = {**contract, "maximumAttempts": 2}
        with self.assertRaises(ValueError):
            validate_demo_engineering_smoke_contract(changed)
        with self.assertRaises(ValueError):
            validate_demo_engineering_smoke_contract({**contract, "apiKey": "forbidden"})

    def test_builds_v41_v45_exact_instrument_contract(self) -> None:
        instrument = {
            "instId": "BTC-USDT-SWAP",
            "tickSz": "0.1",
            "lotSz": "0.01",
            "minSz": "0.01",
            "ctVal": "0.01",
            "ctType": "linear",
            "state": "live",
        }
        first = build_v41_v45_engineering_smoke_contract(
            createdAt="2026-07-20T00:00:00+00:00",
            instrument=instrument,
            accountMode="multi-currency",
            positionMode="net_mode",
        )
        second = build_v41_v45_engineering_smoke_contract(
            createdAt="2026-07-20T00:00:00+00:00",
            instrument=instrument,
            accountMode="multi-currency",
            positionMode="net_mode",
        )

        self.assertEqual(first, second)
        self.assertEqual(first["maximumSize"], instrument["minSz"])
        self.assertEqual(first["maximumConcurrentPositions"], 1)
        self.assertEqual(first["maximumOpenPositions"], 1)
        self.assertFalse(first["releaseQualification"])
        self.assertFalse(first["strategyQualification"])
        self.assertEqual(first["xSimulatedTrading"], "1")
        self.assertEqual(len(first["contractHash"]), 64)
        validate_v41_v45_engineering_smoke_contract(first)

    def test_v41_v45_contract_rejects_tampering_and_sensitive_fields(self) -> None:
        contract = build_v41_v45_engineering_smoke_contract(
            createdAt="2026-07-20T00:00:00+00:00",
            instrument={
                "instId": "BTC-USDT-SWAP",
                "tickSz": "0.1",
                "lotSz": "0.01",
                "minSz": "0.01",
                "ctVal": "0.01",
                "ctType": "linear",
                "state": "live",
            },
            accountMode="multi-currency",
            positionMode="net_mode",
        )
        with self.assertRaises(ValueError):
            validate_v41_v45_engineering_smoke_contract({**contract, "maximumSize": "1"})
        with self.assertRaises(ValueError):
            validate_v41_v45_engineering_smoke_contract({**contract, "apiSecret": "forbidden"})

    def test_v41_v45_approval_requires_exact_process_hash(self) -> None:
        contract = build_v41_v45_engineering_smoke_contract(
            createdAt="2026-07-20T00:00:00+00:00",
            instrument={
                "instId": "BTC-USDT-SWAP",
                "tickSz": "0.1",
                "lotSz": "0.01",
                "minSz": "0.01",
                "ctVal": "0.01",
                "ctType": "linear",
                "state": "live",
            },
            accountMode="multi-currency",
            positionMode="net_mode",
        )
        overlay = build_v41_v45_engineering_smoke_approval_overlay(
            contract,
            environment={
                "ALPHAPILOT_ENGINEERING_SMOKE_APPROVED": contract["contractHash"],
            },
        )
        self.assertEqual(overlay["status"], "approved")
        self.assertEqual(overlay["approvedContractHash"], contract["contractHash"])
        self.assertTrue(overlay["processOnly"])
        self.assertNotIn("apiKey", json.dumps(overlay))

        with self.assertRaises(PermissionError):
            build_v41_v45_engineering_smoke_approval_overlay(contract, environment={})
        with self.assertRaises(PermissionError):
            build_v41_v45_engineering_smoke_approval_overlay(
                contract,
                environment={"ALPHAPILOT_ENGINEERING_SMOKE_APPROVED": "wrong"},
            )


if __name__ == "__main__":
    unittest.main()
