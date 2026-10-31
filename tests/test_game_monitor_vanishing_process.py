#!/usr/bin/env python3
"""Ensure stale League processes cannot stop the launch monitor."""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from injection.game import game_monitor


class GameMonitorVanishingProcessTests(unittest.TestCase):
    def test_exiting_process_does_not_block_monitor_in_both_paths(self):
        for path in ("immediate", "regular"):
            with self.subTest(path=path):
                gone = Mock()
                gone.info = {"name": "League of Legends.exe", "pid": 456}
                gone.status.side_effect = game_monitor.NoSuchProcess(456)
                gone.suspend.side_effect = game_monitor.NoSuchProcess(456)

                suspended = [False]
                live = Mock()
                live.info = {"name": "League of Legends.exe", "pid": 123}
                live.status.side_effect = (
                    lambda: game_monitor.STATUS_STOPPED if suspended[0] else "running"
                )
                live.suspend.side_effect = lambda: suspended.__setitem__(0, True)
                live.resume.side_effect = lambda: suspended.__setitem__(0, False)
                polls = [0]

                def processes(*_args):
                    polls[0] += 1
                    return [] if path == "regular" and polls[0] <= 10 else [gone, live]

                fake_psutil = SimpleNamespace(
                    process_iter=processes,
                    Process=lambda pid: gone if pid == 456 else live,
                )
                monitor = game_monitor.GameMonitor(lambda: 60)
                self.addCleanup(monitor.stop)

                with (
                    patch.object(game_monitor, "psutil", fake_psutil),
                    patch.object(game_monitor, "PSUTIL_AVAILABLE", True),
                    patch.object(game_monitor, "ENABLE_GAME_SUSPENSION", True),
                ):
                    monitor.start()
                    try:
                        ready = threading.Event()
                        for _ in range(150):
                            if monitor.get_suspended_game_process() is live:
                                ready.set()
                                break
                            ready.wait(0.01)
                        self.assertTrue(ready.is_set(), "Monitor stopped at the stale game")
                        self.assertTrue(monitor._monitor_active)
                        live.suspend.assert_called_once()
                    finally:
                        monitor.stop()
                        if monitor._monitor_thread:
                            monitor._monitor_thread.join(timeout=3)
                    self.assertFalse(suspended[0], "Monitor left the game suspended")


if __name__ == "__main__":
    unittest.main()
