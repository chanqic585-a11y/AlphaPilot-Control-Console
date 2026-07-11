from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alphapilot_control_console.demo_override_release import (
    DEMO_OVERRIDE_CONFIRMATION,
    authorize_demo_override,
)
from alphapilot_control_console.evolution_demo_service import validate_demo_contract
from alphapilot_control_console.risk_profile_store import default_profile


def lifecycle_item(*, trade_count: int = 42, target_r: float = 2.0) -> dict:
    return {
        "strategyId": "strategy-1",
        "displayName": "Strategy 1",
        "metrics": {"tradeCount": trade_count, "closedSamples": 0},
        "optimizationContext": {
            "definition": {
                "schemaVersion": "strategy_workflow_definition_v1",
                "family": "breakout",
                "direction": "long_research",
                "timeframe": "1d",
                "targetR": target_r,
            },
            "parameters": {
                "atrMultiplier": 2.0,
                "targetRewardRiskRatio": target_r,
                "maxHoldBars": 16,
                "minVolumeRatio": 1.2,
                "rsiMin": 50,
                "rsiMax": 76,
                "breakoutMultiplier": 0.998,
            },
        },
    }


def risk_record() -> dict:
    return {
        "riskProfileId": "risk-profile-1",
        "contentHash": "risk-hash-1",
        "profile": default_profile("okx_demo"),
    }


class DemoOverrideReleaseTests(unittest.TestCase):
    def test_override_requires_reason_and_exact_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_reason = authorize_demo_override(
                lifecycle_item(),
                reason="",
                confirmation=DEMO_OVERRIDE_CONFIRMATION,
                contract_dir=Path(directory),
                risk_profile_record=risk_record(),
                audit_writer=lambda *_args: {},
            )
            wrong_confirmation = authorize_demo_override(
                lifecycle_item(),
                reason="需要开始 Demo 前向验证",
                confirmation="OK",
                contract_dir=Path(directory),
                risk_profile_record=risk_record(),
                audit_writer=lambda *_args: {},
            )

        self.assertFalse(missing_reason["ok"])
        self.assertIn("override_reason_required", missing_reason["blockers"])
        self.assertFalse(wrong_confirmation["ok"])
        self.assertIn("override_confirmation_mismatch", wrong_confirmation["blockers"])

    def test_override_cannot_bypass_formal_backtest_or_two_r(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            no_backtest = authorize_demo_override(
                lifecycle_item(trade_count=0),
                reason="Demo research",
                confirmation=DEMO_OVERRIDE_CONFIRMATION,
                contract_dir=Path(directory),
                risk_profile_record=risk_record(),
                audit_writer=lambda *_args: {},
            )
            low_r = authorize_demo_override(
                lifecycle_item(target_r=1.5),
                reason="Demo research",
                confirmation=DEMO_OVERRIDE_CONFIRMATION,
                contract_dir=Path(directory),
                risk_profile_record=risk_record(),
                audit_writer=lambda *_args: {},
            )

        self.assertIn("formal_backtest_evidence_missing", no_backtest["blockers"])
        self.assertIn("target_r_below_2r", low_r["blockers"])

    def test_override_creates_idempotent_demo_only_contract_and_audit(self) -> None:
        audits: list[tuple[str, dict]] = []

        def audit_writer(event_type: str, payload: dict) -> dict:
            audits.append((event_type, payload))
            return {"eventType": event_type, "payload": payload}

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            first = authorize_demo_override(
                lifecycle_item(),
                reason="先在 OKX Demo 验证全市场筛选",
                confirmation=DEMO_OVERRIDE_CONFIRMATION,
                contract_dir=target,
                risk_profile_record=risk_record(),
                audit_writer=audit_writer,
            )
            second = authorize_demo_override(
                lifecycle_item(),
                reason="先在 OKX Demo 验证全市场筛选",
                confirmation=DEMO_OVERRIDE_CONFIRMATION,
                contract_dir=target,
                risk_profile_record=risk_record(),
                audit_writer=audit_writer,
            )

            self.assertTrue(Path(first["contractPath"]).exists())

        self.assertTrue(first["ok"])
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["contract"]["demoReleaseId"], second["contract"]["demoReleaseId"])
        validate_demo_contract(first["contract"])
        self.assertEqual(first["contract"]["releaseMode"], "experimental_override")
        self.assertFalse(first["contract"]["livePromotionAllowed"])
        self.assertEqual(first["contract"]["executionBoundary"]["environment"], "okx_demo_only")
        self.assertFalse(first["contract"]["executionBoundary"]["liveExecutionAllowed"])
        market = first["contract"]["strategy"]["marketDefinition"]
        self.assertEqual(market["universePolicy"]["mode"], "okx_usdt_linear_perpetual_full_market")
        self.assertEqual(audits[0][0], "demo_override_release_authorized")
        self.assertTrue(audits[0][1]["liveExecutionAllowed"] is False)


if __name__ == "__main__":
    unittest.main()
