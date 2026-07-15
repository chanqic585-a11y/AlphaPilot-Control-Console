from __future__ import annotations

import unittest

from alphapilot_control_console.demo_instrument_identity import (
    CanonicalDemoInstrument,
    canonicalize_demo_instrument,
    same_demo_contract,
    to_okx_inst_id,
)


class DemoInstrumentIdentityTests(unittest.TestCase):
    def test_canonicalizes_okx_and_ccxt_usdt_swap_identifiers(self) -> None:
        expected = CanonicalDemoInstrument(
            instId="BTC-USDT-SWAP",
            baseCurrency="BTC",
            quoteCurrency="USDT",
            settleCurrency="USDT",
            instrumentType="SWAP",
        )

        self.assertEqual(canonicalize_demo_instrument("BTC-USDT-SWAP"), expected)
        self.assertEqual(canonicalize_demo_instrument("btc/usdt:usdt"), expected)
        self.assertEqual(canonicalize_demo_instrument(" btc_usdt_swap "), expected)
        self.assertEqual(to_okx_inst_id("btc/usdt:usdt"), "BTC-USDT-SWAP")

    def test_canonicalizes_an_okx_private_instrument_row(self) -> None:
        value = {
            "instId": "eth-usdt-swap",
            "instType": "swap",
            "baseCcy": "eth",
            "quoteCcy": "usdt",
            "settleCcy": "usdt",
        }

        result = canonicalize_demo_instrument(value)

        self.assertEqual(result.instId, "ETH-USDT-SWAP")
        self.assertEqual(result.baseCurrency, "ETH")
        self.assertTrue(same_demo_contract(value, "ETH/USDT:USDT"))

    def test_rejects_non_usdt_perpetual_and_malformed_identifiers(self) -> None:
        invalid = (
            "BTC-USDT",
            "BTC-USDC-SWAP",
            "BTC-USD-SWAP",
            "BTC-USDT-260925",
            "BTC-USDT-OPTION",
            "BTC",
            "",
        )

        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    canonicalize_demo_instrument(value)

    def test_rejects_private_rows_with_missing_or_conflicting_identity(self) -> None:
        invalid = (
            {"instId": "BTC-USDT-SWAP", "instType": "SWAP"},
            {
                "instId": "BTC-USDT-SWAP",
                "instType": "SPOT",
                "baseCcy": "BTC",
                "quoteCcy": "USDT",
                "settleCcy": "USDT",
            },
            {
                "instId": "BTC-USDT-SWAP",
                "instType": "SWAP",
                "baseCcy": "ETH",
                "quoteCcy": "USDT",
                "settleCcy": "USDT",
            },
            {
                "instId": "BTC-USDT-SWAP",
                "instType": "SWAP",
                "baseCcy": "BTC",
                "quoteCcy": "USDT",
                "settleCcy": "USD",
            },
        )

        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    canonicalize_demo_instrument(value)

    def test_same_contract_returns_false_for_invalid_values(self) -> None:
        self.assertFalse(same_demo_contract("BTC-USDT-SWAP", "BTC-USDT"))
        self.assertFalse(same_demo_contract("BTC-USDT-SWAP", "ETH-USDT-SWAP"))


if __name__ == "__main__":
    unittest.main()
