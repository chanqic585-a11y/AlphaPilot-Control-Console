from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alphapilot_control_console.execution_runtime_lease import (
    ExecutionRuntimeLeaseStore,
)


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 22, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value


class ExecutionRuntimeLeaseTests(unittest.TestCase):
    def test_only_one_order_authority_can_hold_an_environment_lease(self) -> None:
        clock = MutableClock()
        with tempfile.TemporaryDirectory() as directory:
            store = ExecutionRuntimeLeaseStore(
                Path(directory) / "lease.sqlite",
                now_factory=clock,
            )
            try:
                claim = store.acquire(
                    environment="okx_live",
                    owner_id="live-strategy-runtime",
                    ttl_seconds=30,
                )
                store.assert_authority(claim)

                with self.assertRaises(PermissionError):
                    store.acquire(
                        environment="okx_live",
                        owner_id="live-engineering-smoke",
                        ttl_seconds=30,
                    )

                projection = store.projection("okx_live")
                self.assertEqual(projection["ownerId"], "live-strategy-runtime")
                self.assertNotIn(claim.token, str(projection))
                self.assertEqual(len(projection["tokenHash"]), 64)
            finally:
                store.close()

    def test_expired_lease_can_be_replaced_and_stale_claim_is_rejected(self) -> None:
        clock = MutableClock()
        with tempfile.TemporaryDirectory() as directory:
            store = ExecutionRuntimeLeaseStore(
                Path(directory) / "lease.sqlite",
                now_factory=clock,
            )
            try:
                stale = store.acquire(
                    environment="okx_demo",
                    owner_id="old-runtime",
                    ttl_seconds=10,
                )
                clock.value += timedelta(seconds=11)
                current = store.acquire(
                    environment="okx_demo",
                    owner_id="new-runtime",
                    ttl_seconds=30,
                )

                with self.assertRaises(PermissionError):
                    store.assert_authority(stale)
                store.assert_authority(current)
            finally:
                store.close()

    def test_release_requires_the_process_only_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ExecutionRuntimeLeaseStore(Path(directory) / "lease.sqlite")
            try:
                claim = store.acquire(
                    environment="okx_live",
                    owner_id="runtime",
                    ttl_seconds=30,
                )
                store.release(claim)
                self.assertIsNone(store.projection("okx_live"))
                with self.assertRaises(PermissionError):
                    store.assert_authority(claim)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
