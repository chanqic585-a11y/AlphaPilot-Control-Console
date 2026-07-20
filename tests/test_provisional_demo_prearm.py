from __future__ import annotations

import unittest

from alphapilot_control_console.provisional_demo_prearm import (
    TARGET_INSTRUMENTS,
    build_private_read_audit,
)
from alphapilot_control_console.strategy_validation_hashing import stable_hash


class FakeClient:
    site = "global"
    base_url = "https://www.okx.com"

    def synchronize_server_time(self):
        return {"roundTripMilliseconds": 12, "offsetMilliseconds": 3}

    def get_account_config(self):
        return {
            "code": "0",
            "data": [
                {
                    "uid": "uid-sensitive-value",
                    "acctLv": "2",
                    "posMode": "net_mode",
                }
            ],
        }

    def get_account_instruments(self, instrumentType="SWAP"):
        return {
            "code": "0",
            "data": [
                {
                    "instId": instrument,
                    "instType": "SWAP",
                    "settleCcy": "USDT",
                    "state": "live",
                }
                for instrument in TARGET_INSTRUMENTS
            ],
        }

    def get_balance(self, currency="USDT"):
        return {
            "code": "0",
            "data": [
                {"details": [{"ccy": "USDT", "eq": "balance-sensitive-value"}]}
            ],
        }

    def get_positions(self, instrumentType="SWAP"):
        return {"code": "0", "data": []}

    def get_open_orders(self):
        return {"code": "0", "data": []}

    def get_fills(self, limit=100):
        return {"code": "0", "data": []}


class ProvisionalDemoPreArmTests(unittest.TestCase):
    def test_private_read_audit_is_complete_and_redacted(self) -> None:
        audit = build_private_read_audit(
            FakeClient(),
            expected_instruments=TARGET_INSTRUMENTS,
            expected_intersection_hash=stable_hash(
                list(TARGET_INSTRUMENTS), "demo_execution_intersection"
            ),
            generated_at="2026-07-20T00:00:00Z",
        )

        self.assertEqual(audit["status"], "verified")
        self.assertTrue(audit["privateReadVerified"])
        self.assertEqual(audit["verifiedInstrumentCount"], 5)
        self.assertEqual(audit["verifiedInstruments"], list(TARGET_INSTRUMENTS))
        self.assertTrue(audit["credentialsRetained"] is False)
        self.assertTrue(audit["signatureHeadersRetained"] is False)
        self.assertNotIn("uid-sensitive-value", str(audit))
        self.assertNotIn("balance-sensitive-value", str(audit))
        self.assertNotIn("eq", audit["balanceRead"])


if __name__ == "__main__":
    unittest.main()
