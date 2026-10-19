#!/usr/bin/env python3
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from injection.overlay.overlay_manager import OverlayManager
from threads.utilities.loadout_ticker import LoadoutTicker


class CountdownPrearmTests(unittest.TestCase):
    def _ticker(self):
        state = SimpleNamespace(
            stop=False,
            current_ticker=4,
            phase="FINALIZATION",
            loadout_countdown_active=True,
            loadout_t0=time.monotonic(),
            loadout_left0_ms=0,
            last_remain_ms=0,
            skin_write_ms=300,
            last_hover_written=False,
            locked_champ_id=69,
            hovered_champ_id=69,
        )
        manager = MagicMock()
        ticker = LoadoutTicker(
            SimpleNamespace(session={}),
            state,
            hz=100,
            fallback_ms=0,
            ticker_id=4,
            injection_manager=manager,
            skin_scraper=None,
        )
        ticker.skin_name_resolver = MagicMock()
        ticker.injection_trigger = MagicMock()
        return state, manager, ticker

    def test_countdown_prearms_scanner_before_final_trigger(self):
        state, manager, ticker = self._ticker()
        ticker.skin_name_resolver.resolve_injection_name.return_value = "skin_69009"

        def mark_committed(*_args, **_kwargs):
            state.last_hover_written = True

        ticker.injection_trigger.trigger_injection.side_effect = mark_committed
        ticker.run()

        manager.start_patcher_in_background.assert_called_once()
        manager.discard_early_patcher.assert_not_called()

    def test_countdown_without_injection_discards_scanner(self):
        _state, manager, ticker = self._ticker()
        ticker.skin_name_resolver.resolve_injection_name.return_value = None

        ticker.run()

        manager.start_patcher_in_background.assert_called_once()
        manager.discard_early_patcher.assert_called_once()


class OverlayEarlyScannerTests(unittest.TestCase):
    def _manager(self, root: Path):
        tools = root / "tools"
        mods = root / "mods"
        game = root / "game"
        tools.mkdir()
        mods.mkdir()
        game.mkdir()
        return OverlayManager(tools, mods, game)

    def test_alive_prearmed_session_is_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = self._manager(Path(tmp))
            session = MagicMock()
            session.proc.poll.return_value = None

            with patch(
                "injection.overlay.ltk_host.start_ltk_patcher_host",
                return_value=session,
            ) as start:
                manager.start_patcher_early()
                manager.start_patcher_early()

            start.assert_called_once()
            self.assertIs(manager._take_early_patcher(), session)
            self.assertIsNone(manager._take_early_patcher())

    def test_dead_prearmed_session_is_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = self._manager(Path(tmp))
            dead = MagicMock()
            dead.proc.poll.return_value = 1
            replacement = MagicMock()
            replacement.proc.poll.return_value = None

            with (
                patch(
                    "injection.overlay.ltk_host.start_ltk_patcher_host",
                    side_effect=[dead, replacement],
                ) as start,
                patch(
                    "injection.overlay.ltk_host.abort_ltk_patcher_host"
                ) as abort,
            ):
                manager.start_patcher_early()
                manager.start_patcher_early()

            self.assertEqual(start.call_count, 2)
            abort.assert_called_once_with(dead)
            self.assertIs(manager._take_early_patcher(), replacement)

    def test_discard_stops_unused_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = self._manager(Path(tmp))
            session = MagicMock()
            session.proc.poll.return_value = None

            with (
                patch(
                    "injection.overlay.ltk_host.start_ltk_patcher_host",
                    return_value=session,
                ),
                patch(
                    "injection.overlay.ltk_host.abort_ltk_patcher_host"
                ) as abort,
            ):
                manager.start_patcher_early()
                manager.discard_early_patcher()

            abort.assert_called_once_with(session)
            self.assertIsNone(manager._take_early_patcher())


if __name__ == "__main__":
    unittest.main()
