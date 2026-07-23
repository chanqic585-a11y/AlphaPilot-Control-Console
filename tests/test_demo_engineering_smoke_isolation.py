from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alphapilot_control_console.demo_engineering_smoke_contract import (
    build_demo_engineering_smoke_contract,
)
from alphapilot_control_console.demo_engineering_smoke_service import (
    DEMO_ENGINEERING_SMOKE_STORE_PATH,
    STRATEGY_EVIDENCE_STORE_PATHS,
    run_demo_engineering_smoke,
)
from tests.test_demo_engineering_smoke_service import SuccessfulClient, runtime_identity, universe


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DemoEngineeringSmokeIsolationTests(unittest.TestCase):
    def test_smoke_changes_only_its_isolated_ledger_and_never_strategy_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            strategy_ledger = root / "strategy_evidence.json"
            smoke_ledger = root / "engineering_smoke.sqlite"
            strategy_snapshot = {
                "closedStrategyTrades": 17,
                "profitFactor": 1.42,
                "winRate": 0.53,
                "promotionEvidenceCount": 4,
                "immutableReleaseCount": 2,
                "liveCandidateCount": 0,
            }
            strategy_ledger.write_text(
                json.dumps(strategy_snapshot, sort_keys=True),
                encoding="utf-8",
            )
            before_digest = _digest(strategy_ledger)
            contract = build_demo_engineering_smoke_contract(
                createdAt="2026-07-15T00:00:00+00:00",
                outputDir=root / "contracts",
            )

            with patch(
                "alphapilot_control_console.demo_engineering_smoke_service.STRATEGY_EVIDENCE_STORE_PATHS",
                frozenset({strategy_ledger.resolve()}),
            ):
                result = run_demo_engineering_smoke(
                    client=SuccessfulClient(),
                    contract=contract,
                    universe=universe(),
                    deterministicTrigger=True,
                    storePath=smoke_ledger,
                    runtimeIdentity=runtime_identity(contract),
                )

            self.assertEqual(result["status"], "completed")
            self.assertFalse(result["strategyQualification"])
            self.assertFalse(result["promotionEligible"])
            self.assertFalse(result["forwardPerformanceEligible"])
            self.assertEqual(_digest(strategy_ledger), before_digest)
            self.assertEqual(
                json.loads(strategy_ledger.read_text(encoding="utf-8")),
                strategy_snapshot,
            )
            self.assertTrue(smoke_ledger.exists())

    def test_smoke_fails_before_order_when_store_path_is_a_strategy_evidence_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            forbidden = root / "strategy.sqlite"
            client = SuccessfulClient()
            contract = build_demo_engineering_smoke_contract(
                createdAt="2026-07-15T00:00:00+00:00",
                outputDir=root / "contracts",
            )

            with patch(
                "alphapilot_control_console.demo_engineering_smoke_service.STRATEGY_EVIDENCE_STORE_PATHS",
                frozenset({forbidden.resolve()}),
            ):
                with self.assertRaisesRegex(PermissionError, "strategy evidence"):
                    run_demo_engineering_smoke(
                        client=client,
                        contract=contract,
                        universe=universe(),
                        deterministicTrigger=True,
                        storePath=forbidden,
                    )

            self.assertEqual(client.placeCalls, [])
            self.assertFalse(forbidden.exists())

    def test_production_strategy_evidence_paths_never_include_smoke_store(self) -> None:
        resolved = {Path(path).resolve() for path in STRATEGY_EVIDENCE_STORE_PATHS}
        self.assertNotIn(DEMO_ENGINEERING_SMOKE_STORE_PATH.resolve(), resolved)


if __name__ == "__main__":
    unittest.main()
