from __future__ import annotations

import unittest

from alphapilot_control_console.demo_latency_observability import build_latency_stage_metrics


class DemoLatencyObservabilityTests(unittest.TestCase):
    def test_builds_non_negative_stage_metrics_from_iso_timestamps(self) -> None:
        result = build_latency_stage_metrics(
            close_received_at="2026-07-13T00:00:00+00:00",
            evaluation_started_at="2026-07-13T00:00:00.200000+00:00",
            arbitration_started_at="2026-07-13T00:00:00.900000+00:00",
            arbitration_finished_at="2026-07-13T00:00:01.100000+00:00",
            risk_started_at="2026-07-13T00:00:01.200000+00:00",
            risk_finished_at="2026-07-13T00:00:01.300000+00:00",
            order_ready_at="2026-07-13T00:00:01.400000+00:00",
            order_sent_at="2026-07-13T00:00:01.500000+00:00",
            exchange_response_at="2026-07-13T00:00:01.800000+00:00",
        )

        self.assertEqual(result["closeToEvaluationMs"], 200.0)
        self.assertEqual(result["arbitrationMs"], 200.0)
        self.assertEqual(result["riskMs"], 100.0)
        self.assertEqual(result["orderSendMs"], 100.0)
        self.assertEqual(result["exchangeResponseMs"], 300.0)
        self.assertEqual(result["closeToOrderSendMs"], 1500.0)

    def test_missing_order_timestamps_remain_null(self) -> None:
        result = build_latency_stage_metrics(
            close_received_at="2026-07-13T00:00:00+00:00",
            evaluation_started_at="2026-07-13T00:00:00.100000+00:00",
        )

        self.assertIsNone(result["orderSendMs"])
        self.assertIsNone(result["exchangeResponseMs"])
        self.assertIsNone(result["closeToOrderSendMs"])

    def test_builds_v55_exchange_lifecycle_metrics(self) -> None:
        result = build_latency_stage_metrics(
            bar_close_exchange_ts="2026-07-13T00:00:00+00:00",
            market_event_received_ts="2026-07-13T00:00:00.100000+00:00",
            signal_completed_ts="2026-07-13T00:00:00.400000+00:00",
            risk_completed_ts="2026-07-13T00:00:00.500000+00:00",
            order_intent_durable_ts="2026-07-13T00:00:00.550000+00:00",
            order_send_ts="2026-07-13T00:00:00.650000+00:00",
            gateway_in_time="2026-07-13T00:00:00.660000+00:00",
            gateway_out_time="2026-07-13T00:00:00.700000+00:00",
            exchange_order_created_ts="2026-07-13T00:00:00.800000+00:00",
            first_fill_ts="2026-07-13T00:00:00.900000+00:00",
            final_fill_ts="2026-07-13T00:00:01+00:00",
        )

        self.assertEqual(result["marketDataLagMs"], 100.0)
        self.assertEqual(result["signalComputeMs"], 300.0)
        self.assertEqual(result["riskDecisionMs"], 100.0)
        self.assertEqual(result["signalToOrderSendMs"], 250.0)
        self.assertEqual(result["gatewayProcessingMs"], 40.0)
        self.assertEqual(result["exchangeAckMs"], 150.0)
        self.assertEqual(result["fillWaitMs"], 100.0)
        self.assertEqual(result["endToEndMs"], 1000.0)


if __name__ == "__main__":
    unittest.main()
