from __future__ import annotations

import importlib.util
import unittest

import alphapilot_control_console.strategy_optimization as optimization


class StrategyOptimizationModuleTests(unittest.TestCase):
    def test_targeted_optimization_module_exists(self) -> None:
        self.assertIsNotNone(
            importlib.util.find_spec(
                "alphapilot_control_console.strategy_optimization"
            ),
            "targeted strategy optimization module is missing",
        )

    def test_data_integrity_blocker_recommends_data_repair_without_parameter_guess(self) -> None:
        builder = getattr(optimization, "build_optimization_context", None)
        self.assertTrue(callable(builder), "optimization context builder is missing")
        item = {
            "displayName": "Alpha191 加密因子观察策略",
            "stage": "backtest",
            "failure": {
                "category": "data_integrity",
                "summary": "data_snapshot_id_missing",
                "suggestions": ["Bind a registered snapshot."],
            },
            "optimizationContext": {
                "sourceKind": "workflow_version",
                "parentStrategyVersionId": "version-1",
                "definition": {"timeframe": "4h", "targetR": 2.0},
                "parameters": {
                    "overlayId": "alpha191",
                    "targetRMultiple": 2.0,
                    "horizonBars": 24,
                },
            },
        }

        context = builder(item)

        self.assertEqual(context["recommendationMode"], "data_repair")
        self.assertFalse(context["canAutoPropose"])
        self.assertEqual(context["changedFields"], [])
        self.assertEqual(context["proposedParameters"], context["baseParameters"])
        self.assertIn("补齐", context["recommendations"][0])

    def test_weak_validation_tightens_existing_quality_parameter_only(self) -> None:
        builder = getattr(optimization, "build_optimization_context", None)
        self.assertTrue(callable(builder), "optimization context builder is missing")
        item = {
            "displayName": "空头上影拒绝",
            "currentStage": "demo_trial",
            "optimizationContext": {
                "sourceKind": "legacy_catalog",
                "legacyStrategyId": "legacy-short-1",
                "definition": {
                    "family": "short_rejection",
                    "direction": "short",
                    "timeframe": "1h",
                    "targetR": 2.0,
                },
                "parameters": {
                    "volume_min": 1.2,
                    "rsi_high": 60,
                    "stop_atr": 1.0,
                    "max_hold": 12,
                    "targetRMultiple": 2.0,
                },
                "metrics": {"profitFactor": 1.4, "maxDrawdownR": 8.0},
                "validationMetrics": {"profitFactor": 0.95},
            },
        }

        context = builder(item)

        self.assertEqual(context["recommendationMode"], "parameter_quality")
        self.assertTrue(context["canAutoPropose"])
        self.assertEqual(context["proposedParameters"]["volume_min"], 1.3)
        self.assertEqual(context["proposedParameters"]["targetRMultiple"], 2.0)
        self.assertIn("volume_min", [row["key"] for row in context["changedFields"]])
        self.assertNotIn("stop_atr", [row["key"] for row in context["changedFields"]])

    def test_high_drawdown_shortens_existing_holding_parameter(self) -> None:
        builder = getattr(optimization, "build_optimization_context", None)
        self.assertTrue(callable(builder), "optimization context builder is missing")
        item = {
            "displayName": "低波突破",
            "currentStage": "local_simulation_running",
            "optimizationContext": {
                "sourceKind": "legacy_catalog",
                "legacyStrategyId": "legacy-long-1",
                "definition": {
                    "family": "squeeze_breakout",
                    "direction": "long",
                    "timeframe": "1d",
                    "targetR": 2.0,
                },
                "parameters": {
                    "minVolumeRatio": 1.1,
                    "maxHoldBars": 16,
                    "targetRewardRiskRatio": 2.0,
                },
                "metrics": {"profitFactor": 1.25, "maxDrawdownPct": 20.0},
            },
        }

        context = builder(item)

        self.assertEqual(context["proposedParameters"]["maxHoldBars"], 13)
        self.assertIn("maxHoldBars", [row["key"] for row in context["changedFields"]])

    def test_submission_rejects_unchanged_or_below_two_r_parameters(self) -> None:
        validator = getattr(optimization, "validate_optimization_parameters", None)
        self.assertTrue(callable(validator), "optimization validator is missing")
        definition = {"targetR": 2.0}
        base = {"volume_min": 1.2, "targetRMultiple": 2.0}

        with self.assertRaisesRegex(ValueError, "optimized_parameters_unchanged"):
            validator(definition, base, dict(base))
        with self.assertRaisesRegex(ValueError, "minimum_target_r_is_2"):
            validator(
                definition,
                base,
                {"volume_min": 1.3, "targetRMultiple": 1.5},
            )

        validated = validator(
            definition,
            base,
            {"volume_min": 1.3, "targetRMultiple": 2.0},
        )
        self.assertEqual(validated["volume_min"], 1.3)


if __name__ == "__main__":
    unittest.main()
