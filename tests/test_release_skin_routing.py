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

    def test_unowned_official_skin_path_fails_closed(self):
        self.assertIn(
            "Current runtime verification does not permit this official-skin substitution",
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
