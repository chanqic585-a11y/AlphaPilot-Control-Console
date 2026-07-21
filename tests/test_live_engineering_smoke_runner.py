from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from alphapilot_control_console.live_engineering_smoke_runner import (
    run_approved_live_engineering_smoke,
    select_live_smoke_instrument,
)


class LiveEngineeringSmokeRunnerTests(unittest.TestCase):
    def test_selection_prefers_eligible_liquid_major_with_bounded_minimum_notional(self) -> None:
        instruments = [
            {
                "instId": "BTC-USDT-SWAP",
                "state": "live",
                "ctType": "linear",
                "settleCcy": "USDT",
                "tickSz": "0.1",
                "lotSz": "1",
                "minSz": "1",
                "ctVal": "0.01",
            },
            {
                "instId": "ETH-USDT-SWAP",
                "state": "live",
                "ctType": "linear",
                "settleCcy": "USDT",
                "tickSz": "0.01",
                "lotSz": "0.01",
                "minSz": "0.01",
                "ctVal": "0.1",
            },
        ]
        tickers = [
            {"instId": "BTC-USDT-SWAP", "bidPx": "100000", "askPx": "100001"},
            {"instId": "ETH-USDT-SWAP", "bidPx": "3500", "askPx": "3501"},
        ]

        instrument, quote = select_live_smoke_instrument(
            instruments,
            tickers,
            maximum_notional_usdt=10,
        )

        self.assertEqual(instrument["instId"], "ETH-USDT-SWAP")
        self.assertEqual(quote["bidPx"], "3500")

    def test_selection_rejects_non_linear_or_unavailable_instruments(self) -> None:
        with self.assertRaises(RuntimeError):
            select_live_smoke_instrument(
                [{
                    "instId": "ETH-USDT-SWAP",
                    "state": "suspend",
                    "ctType": "linear",
                    "settleCcy": "USDT",
                    "tickSz": "0.01",
                    "lotSz": "0.01",
                    "minSz": "0.01",
                    "ctVal": "0.1",
                }],
                [{"instId": "ETH-USDT-SWAP", "bidPx": "3500", "askPx": "3501"}],
                maximum_notional_usdt=10,
            )

    @patch("alphapilot_control_console.live_engineering_smoke_runner.run_live_engineering_smoke")
    @patch("alphapilot_control_console.live_engineering_smoke_runner._public_tickers")
    @patch("alphapilot_control_console.live_engineering_smoke_runner._public_instruments")
    def test_runner_intersects_public_metadata_with_account_eligible_instruments(
        self,
        public_instruments,
        public_tickers,
        run_smoke,
    ) -> None:
        class Client:
            @staticmethod
            def get_account_instruments(_: str) -> dict:
                return {"code": "0", "data": [{"instId": "ETH-USDT-SWAP"}]}

        public_instruments.return_value = [
            {
                "instId": "ETH-USDT-SWAP",
                "state": "live",
                "ctType": "linear",
                "settleCcy": "USDT",
                "tickSz": "0.01",
                "lotSz": "0.01",
                "minSz": "0.01",
                "ctVal": "0.1",
            },
            {
                "instId": "SOL-USDT-SWAP",
                "state": "live",
                "ctType": "linear",
                "settleCcy": "USDT",
                "tickSz": "0.001",
                "lotSz": "0.01",
                "minSz": "0.01",
                "ctVal": "1",
            },
        ]
        public_tickers.return_value = [
            {"instId": "ETH-USDT-SWAP", "bidPx": "3500", "askPx": "3501"},
            {"instId": "SOL-USDT-SWAP", "bidPx": "150", "askPx": "151"},
        ]
        run_smoke.return_value = {"status": "completed_canceled_and_reconciled"}

        result = run_approved_live_engineering_smoke(
            client=Client(),
            contract={"maximumNotionalUsdt": 10},
            approval={"actor": "user_explicit"},
            result_path=Path("result.json"),
            attempt_path=Path("attempt.json"),
        )

        self.assertEqual(result["status"], "completed_canceled_and_reconciled")
        self.assertEqual(run_smoke.call_args.kwargs["instrument"]["instId"], "ETH-USDT-SWAP")


if __name__ == "__main__":
    unittest.main()
