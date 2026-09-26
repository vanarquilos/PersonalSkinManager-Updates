#!/usr/bin/env python3
import unittest
from unittest.mock import patch

from injection.overlay.ltk_host import LTK_DEFAULT_FLAGS, LtkHostResult, _parse_stdout


class LtkHostProtocolTests(unittest.TestCase):
    def test_release_runtime_keeps_verification_enabled(self):
        self.assertEqual(LTK_DEFAULT_FLAGS, 0)

    def test_late_join_is_a_hard_failure(self):
        result = LtkHostResult()
        _parse_stdout(
            "dll 4.20 1234 5678 ERROR ltk_patcher_dll::entry: joined too late",
            result,
        )
        self.assertIsNotNone(result.failure)
        self.assertIn("started before", result.failure)

    def test_end_of_life_is_a_hard_failure(self):
        result = LtkHostResult()
        _parse_stdout(
            "dll 1.20 1234 5678 ERROR ltk_patcher_dll::entry: "
            "end of life reached, please update: 2026-09-30",
            result,
        )
        self.assertIsNotNone(result.failure)
        self.assertIn("end-of-life", result.failure)

    def test_exited_status_is_not_terminal_for_reconnects(self):
        result = LtkHostResult()
        _parse_stdout("status 1.0 injected dll attached", result)
        self.assertTrue(result.attached)
        _parse_stdout("status 2.0 exited game process closed", result)
        self.assertEqual(result.last_state, "exited")
        self.assertTrue(result.attached)
        self.assertIsNone(result.failure)

    def test_wad_scan_warning_waits_for_final_verdict(self):
        result = LtkHostResult()
        _parse_stdout(
            "dll 5.53 1234 5678 WARN ltk_patcher_dll::verify: "
            "WAD scan failed c0000229 for aphelios",
            result,
        )
        self.assertIsNone(result.failure)

    def test_overlay_verification_rejection_is_a_hard_failure(self):
        result = LtkHostResult()
        with patch("injection.overlay.ltk_host.report_issue"):
            _parse_stdout(
                "dll 5.57 1234 5678 ERROR ltk_patcher_dll::verify: "
                "overlay verification failed, disabling overlay",
                result,
            )
        self.assertIsNotNone(result.failure)

    def test_injected_and_waiting_confirm_attach(self):
        result = LtkHostResult()
        _parse_stdout("status 1.0 injected dll attached", result)
        self.assertTrue(result.attached)
        _parse_stdout("status 1.1 waiting awaiting game exit", result)
        self.assertEqual(result.last_state, "waiting")


if __name__ == "__main__":
    unittest.main()
