from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.demo_engineering_smoke_contract import (
    build_demo_engineering_smoke_contract,
    validate_demo_engineering_smoke_contract,
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


if __name__ == "__main__":
    unittest.main()
