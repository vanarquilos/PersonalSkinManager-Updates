#!/usr/bin/env python3
import unittest
from unittest.mock import patch

from injection.overlay.ltk_host import (
    LTK_DEFAULT_FLAGS,
    LTK_PATCHER_FLAGS,
    LTK_PATCHER_LOG_LEVEL,
    LTK_PATCHER_DEBUG_LOG_LEVEL,
    _runtime_log_level,
    _league_game_process_running,
    _should_stop_after_callback,
    _skin_redirect_not_observed,
    LtkHostResult,
    _parse_stdout,
)


class LtkHostProtocolTests(unittest.TestCase):
    def test_runtime_matches_rose_patcher_configuration(self):
        self.assertEqual(LTK_PATCHER_FLAGS, 0)
        self.assertEqual(LTK_DEFAULT_FLAGS, 0)
        self.assertEqual(LTK_PATCHER_LOG_LEVEL, 0x10)

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

    def test_waiting_is_not_a_false_attach_confirmation(self):
        result = LtkHostResult()
        _parse_stdout("status 1.0 waiting scanning for game", result)
        self.assertFalse(result.attached)
        _parse_stdout("status 1.1 injected dll attached", result)
        self.assertTrue(result.attached)
        _parse_stdout("status 1.2 waiting awaiting game exit", result)
        self.assertEqual(result.last_state, "waiting")
        self.assertTrue(result.attached)


    def test_overlay_verification_and_redirection_are_observed(self):
        result = LtkHostResult()
        with patch("injection.overlay.ltk_host.log") as log:
            _parse_stdout(
                "dll 5.5 100 200 INFO ltk_patcher_dll::verify: overlay verified 1 wad(s)",
                result,
            )
            _parse_stdout(
                "dll 5.6 100 200 DEBUG ltk_patcher_dll::fsov: redirected wad: "
                "DATA/FINAL/Champions/Example.wad.client",
                result,
            )
        self.assertEqual(result.verified_wads, 1)
        self.assertEqual(result.redirected_wads, 1)
        log.info.assert_any_call(
            "[INJECT][ltk-host] overlay verified %d WAD(s)", 1
        )
        log.info.assert_any_call(
            "[INJECT][ltk-host] WAD redirection observed"
        )
        self.assertNotIn("Example.wad.client", str(log.info.call_args_list))

    def test_missing_verification_log_is_unknown_not_zero(self):
        result = LtkHostResult()
        _parse_stdout("status 1.0 injected dll attached", result)
        self.assertTrue(result.attached)
        self.assertIsNone(result.verified_wads)
        self.assertEqual(result.redirected_wads, 0)

    def test_explicit_zero_verified_wads_is_distinguishable(self):
        result = LtkHostResult()
        _parse_stdout(
            "dll 5.5 100 200 INFO ltk_patcher_dll::verify: overlay verified 0 wad(s)",
            result,
        )
        self.assertEqual(result.verified_wads, 0)


    def test_upstream_init_done_confirms_overlay_not_just_attach(self):
        result = LtkHostResult()
        _parse_stdout("status 1.0 injected dll attached", result)
        self.assertTrue(result.attached)
        self.assertFalse(result.overlay_initialized)
        _parse_stdout(
            "dll 2.0 100 200 INFO ltk_patcher_dll::entry: init done", result
        )
        self.assertTrue(result.overlay_initialized)
        self.assertIsNone(result.failure)

    def test_ltk_host_verification_refusal_is_terminal_and_sanitized(self):
        result = LtkHostResult()
        with patch("injection.overlay.ltk_host.report_issue") as reported:
            _parse_stdout(
                "dll 5.0 100 200 ERROR ltk_patcher_dll::verify: "
                "host verification failed, refusing overlay: "
                "[VRF00000008] (19480,ltk-manager.exe)",
                result,
            )
        self.assertEqual(result.failure, "LTK host verification refused the overlay")
        self.assertEqual(reported.call_args.args[0], "LTK_HOST_VERIFICATION_FAILED")
        self.assertNotIn("VRF", str(reported.call_args))
        self.assertNotIn("19480", str(reported.call_args))

    def test_lazy_wad_rejection_is_a_hard_failure(self):
        result = LtkHostResult()
        _parse_stdout(
            "dll 5.0 100 200 ERROR ltk_patcher_dll::verify: "
            "lazy verification failed, not overlaying: "
            "wad data/final/champions/example.wad.client: invalid signature",
            result,
        )
        self.assertIsNotNone(result.failure)
        self.assertIn("verification", result.failure)

    def test_failed_hook_is_a_hard_failure(self):
        result = LtkHostResult()
        _parse_stdout(
            "dll 5.0 100 200 ERROR ltk_patcher_dll::entry: "
            "failed to install overlay hook",
            result,
        )
        self.assertIsNotNone(result.failure)
        self.assertIn("hook", result.failure)

    def test_wad_scan_error_is_failure_not_a_transient_warning(self):
        result = LtkHostResult()
        _parse_stdout(
            "dll 5.0 100 200 ERROR ltk_patcher_dll::verify: "
            "WAD scan failed status with c000003e for example.wad.client",
            result,
        )
        self.assertIsNotNone(result.failure)

    def test_wad_scan_warn_remains_nonfatal(self):
        result = LtkHostResult()
        _parse_stdout(
            "dll 5.0 100 200 WARN ltk_patcher_dll::verify: "
            "WAD scan failed c0000229 for example.wad.client",
            result,
        )
        self.assertIsNone(result.failure)


    def test_ltk_debug_events_enabled_in_local_source_mode_only(self):
        self.assertEqual(LTK_PATCHER_DEBUG_LOG_LEVEL, 0x20)
        with patch("injection.overlay.ltk_host.sys.argv", ["main.py", "--dev", "--debug", "--logs"]):
            with patch("injection.overlay.ltk_host.sys.frozen", False, create=True):
                self.assertEqual(_runtime_log_level(), 0x20)

    def test_ltk_release_mode_keeps_info_logging(self):
        with patch("injection.overlay.ltk_host.sys.argv", ["PersonalSkinManager.exe", "--debug"]):
            with patch("injection.overlay.ltk_host.sys.frozen", True, create=True):
                self.assertEqual(_runtime_log_level(), 0x10)
        with patch("injection.overlay.ltk_host.sys.argv", ["main.py"]):
            with patch("injection.overlay.ltk_host.sys.frozen", False, create=True):
                self.assertEqual(_runtime_log_level(), 0x10)


    def test_rose_lifecycle_keeps_host_when_client_exits_but_game_runs(self):
        with patch(
            "injection.overlay.ltk_host._league_game_process_running",
            return_value=True,
        ):
            self.assertFalse(_should_stop_after_callback(True))
            self.assertFalse(_should_stop_after_callback(False))

    def test_rose_lifecycle_stops_only_after_game_process_exits(self):
        with patch(
            "injection.overlay.ltk_host._league_game_process_running",
            return_value=False,
        ):
            self.assertTrue(_should_stop_after_callback(True))
            self.assertFalse(_should_stop_after_callback(False))

    def test_rose_lifecycle_detects_both_league_game_exe_names(self):
        from types import SimpleNamespace

        for exe_name in (
            "League of Legends.exe",
            "League of Legends (TM) Client.exe",
        ):
            with self.subTest(exe=exe_name):
                with patch("injection.overlay.ltk_host.psutil") as mock_psutil:
                    mock_psutil.process_iter.return_value = [
                        SimpleNamespace(info={"name": "LeagueClientUx.exe"}),
                        SimpleNamespace(info={"name": exe_name}),
                    ]
                    self.assertTrue(_league_game_process_running())
        with patch("injection.overlay.ltk_host.psutil") as mock_psutil:
            mock_psutil.process_iter.return_value = [
                SimpleNamespace(info={"name": "LeagueClientUx.exe"})
            ]
            self.assertFalse(_league_game_process_running())

    def test_rose_lifecycle_unknown_process_falls_back_to_stop_callback(self):
        with patch("injection.overlay.ltk_host.psutil", None):
            self.assertFalse(_league_game_process_running())
            self.assertTrue(_should_stop_after_callback(True))


    def test_attached_initialized_without_wad_is_not_confirmed_skin(self):
        result = LtkHostResult()
        result.attached = True
        result.overlay_initialized = True
        result.redirected_wads = 0
        self.assertTrue(_skin_redirect_not_observed(result))

    def test_real_redirection_clears_false_success_verdict(self):
        result = LtkHostResult()
        result.attached = True
        result.overlay_initialized = True
        result.redirected_wads = 1
        self.assertFalse(_skin_redirect_not_observed(result))

    def test_unattached_session_is_not_mislabeled_missing_skin(self):
        result = LtkHostResult()
        result.attached = False
        result.overlay_initialized = False
        self.assertFalse(_skin_redirect_not_observed(result))


if __name__ == "__main__":
    unittest.main()
