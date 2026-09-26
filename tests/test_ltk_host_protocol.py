#!/usr/bin/env python3
import unittest

from injection.overlay.ltk_host import LtkHostResult, _parse_stdout


class LtkHostProtocolTests(unittest.TestCase):
    def test_late_join_is_a_hard_failure(self):
        result = LtkHostResult()
        _parse_stdout(
            "dll 4.20 1234 5678 ERROR ltk_patcher_dll::entry: joined too late",
            result,
        )
        self.assertIsNotNone(result.failure)
        self.assertIn("started before", result.failure)

    def test_opted_out_wad_warning_does_not_fail_session(self):
        result = LtkHostResult()
        _parse_stdout(
            "dll 5.53 1234 5678 WARN ltk_patcher_dll::verify: "
            "AH wad scan failed c0000229 for aphelios (opted out)",
            result,
        )
        self.assertIsNone(result.failure)

    def test_injected_and_waiting_confirm_attach(self):
        result = LtkHostResult()
        _parse_stdout("status 1.0 injected dll attached", result)
        self.assertTrue(result.attached)
        _parse_stdout("status 1.1 waiting awaiting game exit", result)
        self.assertEqual(result.last_state, "waiting")


if __name__ == "__main__":
    unittest.main()
