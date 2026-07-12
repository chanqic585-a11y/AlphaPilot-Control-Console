from __future__ import annotations

import unittest

from alphapilot_control_console.exchange_connectors.public_exchange_registry import (
    _normalize_symbol,
)


class PublicExchangeRegistryTests(unittest.TestCase):
    def test_okx_swap_instrument_id_is_idempotent(self) -> None:
        self.assertEqual(
            _normalize_symbol("ETH-USDT-SWAP")["okx"],
            "ETH-USDT-SWAP",
        )

    def test_common_eth_usdt_formats_share_one_okx_instrument_id(self) -> None:
        for symbol in ("ETH", "ETHUSDT", "ETH/USDT", "ETH-USDT"):
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    _normalize_symbol(symbol)["okx"],
                    "ETH-USDT-SWAP",
                )


if __name__ == "__main__":
    unittest.main()
