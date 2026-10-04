#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression coverage for Swiftplay timing and game-lifetime behavior."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from injection.game.game_monitor import make_game_ended_callback
from state import SharedState
from threads.handlers.swiftplay_handler import SwiftplayHandler


class GameEndedCallbackTests(unittest.TestCase):
    def test_reconnect_is_not_game_end(self):
        state = SimpleNamespace(phase="ChampSelect")
        callback = make_game_ended_callback(state)

        for phase in ("ChampSelect", "GameStart", "InProgress", "Reconnect", "GameStart", "InProgress"):
            state.phase = phase
            self.assertFalse(callback(), phase)

        state.phase = "EndOfGame"
        self.assertTrue(callback())

    def test_dodge_before_inprogress_does_not_fake_end(self):
        state = SimpleNamespace(phase="ChampSelect")
        callback = make_game_ended_callback(state)
        self.assertFalse(callback())
        state.phase = "Lobby"
        self.assertFalse(callback())


class SwiftplayRetryTests(unittest.TestCase):
    @staticmethod
    def make_handler():
        lcu = MagicMock()
        lcu.ok = True
        return SwiftplayHandler(
            lcu,
            SharedState(),
            injection_manager=MagicMock(),
            skin_scraper=MagicMock(),
        )

    def test_empty_tracking_does_not_poison_trigger_state(self):
        handler = self.make_handler()
        self.assertFalse(handler.trigger_swiftplay_injection())
        self.assertFalse(handler._injection_triggered)

    def test_searching_retries_if_first_preparation_was_too_early(self):
        handler = self.make_handler()
        handler.lcu.get.return_value = {"searchState": "Searching"}
        handler.trigger_swiftplay_injection = MagicMock(return_value=False)

        handler.monitor_swiftplay_matchmaking()
        handler.monitor_swiftplay_matchmaking()

        self.assertEqual(handler.trigger_swiftplay_injection.call_count, 2)
        self.assertFalse(handler._injection_triggered)

    def test_invalid_search_resets_prepared_state(self):
        handler = self.make_handler()
        handler._injection_triggered = True
        handler._last_matchmaking_state = "Searching"
        handler.lcu.get.return_value = {"searchState": "Invalid"}

        handler.monitor_swiftplay_matchmaking()

        self.assertFalse(handler._injection_triggered)


if __name__ == "__main__":
    unittest.main()
