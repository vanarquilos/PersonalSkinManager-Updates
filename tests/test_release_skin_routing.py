#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release invariants for supported skin/mod routing."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRIGGER = ROOT / "threads/handlers/injection_trigger.py"


class ReleaseSkinRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TRIGGER.read_text(encoding="utf-8")

    def test_owned_riot_skins_use_lcu_without_overlay(self):
        self.assertIn(
            "Owned Riot skin/chroma selected via LCU; no overlay required",
            self.source,
        )

    def test_unowned_official_skin_routes_through_overlay_runtime(self):
        self.assertIn(
            'Route an unowned official skin/chroma through the current Rose-style overlay flow.',
            self.source,
        )
        self.assertIn("inject_skin_immediately(", self.source)
        self.assertNotIn(
            "Selected unowned League skin cannot be applied with the current supported runtime.",
            self.source,
        )

    def test_unowned_riot_skin_is_not_used_as_custom_mod_carrier(self):
        self.assertIn("carrier overlay was not started", self.source)
        self.assertNotIn("injecting carrier %s + custom mod", self.source)

    def test_non_skin_mods_can_run_without_unowned_riot_skin_carrier(self):
        self.assertIn(
            "using base skin and injecting custom content only",
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
