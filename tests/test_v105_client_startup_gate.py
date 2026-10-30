#!/usr/bin/env python3
"""LCU WebSocket startup cannot hang the main PSM UI loop."""
import unittest

from main.core.client_startup_gate import wait_for_client_websocket


class ClientStartupGateTests(unittest.TestCase):
    def test_delayed_websocket_activates_only_after_real_connection(self):
        t = [0.0]
        calls = []
        worked = wait_for_client_websocket(
            is_connected=lambda: t[0] >= 0.75,
            is_thread_alive=lambda: True,
            should_stop=lambda: False,
            on_ready=lambda: calls.append("activate"),
            on_waiting=lambda: calls.append("waiting"),
            on_thread_exit=lambda: calls.append("died"),
            poll_seconds=0.25,
            notice_seconds=0.5,
            monotonic=lambda: t[0],
            sleep=lambda n: t.__setitem__(0, t[0] + n),
        )
        self.assertTrue(worked)
        self.assertEqual(calls, ["waiting", "activate"])

    def test_stop_does_not_activate_client(self):
        t = [0.0]
        calls = []
        worked = wait_for_client_websocket(
            is_connected=lambda: False,
            is_thread_alive=lambda: True,
            should_stop=lambda: t[0] >= 0.5,
            on_ready=lambda: calls.append("activate"),
            on_waiting=lambda: calls.append("waiting"),
            on_thread_exit=lambda: calls.append("died"),
            poll_seconds=0.25,
            monotonic=lambda: t[0],
            sleep=lambda n: t.__setitem__(0, t[0] + n),
        )
        self.assertFalse(worked)
        self.assertEqual(calls, [])

    def test_dead_websocket_worker_reports_without_activation(self):
        calls = []
        worked = wait_for_client_websocket(
            is_connected=lambda: False,
            is_thread_alive=lambda: False,
            should_stop=lambda: False,
            on_ready=lambda: calls.append("activate"),
            on_waiting=lambda: calls.append("waiting"),
            on_thread_exit=lambda: calls.append("died"),
            sleep=lambda n: self.fail("Should not poll dead worker"),
        )
        self.assertFalse(worked)
        self.assertEqual(calls, ["died"])

    def test_stop_is_checked_again_before_starting_integration(self):
        checks = iter((False, True))
        calls = []
        worked = wait_for_client_websocket(
            is_connected=lambda: True,
            is_thread_alive=lambda: True,
            should_stop=lambda: next(checks),
            on_ready=lambda: calls.append("activate"),
            on_waiting=lambda: None,
            on_thread_exit=lambda: None,
        )
        self.assertFalse(worked)
        self.assertEqual(calls, [])

    def test_main_loop_starts_without_waiting_for_websocket(self):
        from pathlib import Path
        main = (Path(__file__).resolve().parents[1] / "main/__init__.py").read_text("utf-8")
        self.assertIn("wait_for_client_websocket(", main)
        self.assertIn("client_startup_thread.start()", main)
        self.assertNotIn("while not t_ws.connection.is_connected", main)
        self.assertLess(main.index("client_startup_thread.start()"), main.index("run_main_loop(state, skin_scraper)"))


if __name__ == "__main__":
    unittest.main()
