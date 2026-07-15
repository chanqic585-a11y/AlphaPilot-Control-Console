from __future__ import annotations

import copy
import time
import unittest

from alphapilot_control_console.shadow_observer import record_shadow_scan_nonblocking


class ShadowObserverExecutionIsolationTests(unittest.TestCase):
    def test_success_failure_and_timeout_never_mutate_demo_scan(self) -> None:
        contract = {"demoReleaseId": "release-1"}
        scan = {"signals": [{"candidateId": "candidate-1"}], "rejections": []}
        original = copy.deepcopy(scan)

        cases = (
            (lambda *_args, **_kwargs: {"writtenCount": 1}, "completed"),
            (lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk")), "warning"),
            (lambda *_args, **_kwargs: time.sleep(0.2), "warning"),
        )
        for writer, expected_status in cases:
            with self.subTest(expected_status=expected_status):
                result = record_shadow_scan_nonblocking(
                    contract,
                    scan,
                    observed_at="2026-07-15T00:00:00+00:00",
                    source_event_hash="event-hash",
                    demo_instrument_ids=set(),
                    writer=writer,
                    timeout_seconds=0.01,
                )
                self.assertEqual(result["status"], expected_status)
                self.assertEqual(scan, original)
                self.assertTrue(result["executionUnaffected"])


if __name__ == "__main__":
    unittest.main()
