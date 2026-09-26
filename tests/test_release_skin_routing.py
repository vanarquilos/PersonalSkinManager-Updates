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

    def test_owned_riot_skins_follow_rose_lcu_and_injection_path(self):
        self.assertIn("Force owned skins/chromas via LCU", self.source)
        self.assertIn("self._force_owned_skin(effective_skin_id)", self.source)
        self.assertIn("self.injection_manager.inject_skin_immediately(", self.source)
        self.assertNotIn("no overlay required", self.source)

    def test_unowned_official_skin_routes_through_overlay_runtime(self):
        self.assertIn(
            "Inject if user doesn't own the hovered skin",
            self.source,
        )
        self.assertIn("inject_skin_immediately(", self.source)
        self.assertNotIn(
            "Selected unowned League skin cannot be applied with the current supported runtime.",
            self.source,
        )

    def test_unowned_riot_skin_can_be_used_as_custom_mod_carrier(self):
        self.assertIn("injecting carrier %s + custom mod", self.source)
        self.assertIn("base_skin_name=carrier_name", self.source)
        self.assertNotIn("carrier overlay was not started", self.source)

    def test_category_mods_keep_unowned_skin_carrier(self):
        self.assertIn("base_skin_name_for_injection = name", self.source)
        self.assertIn(
            "injecting skin carrier +",
            self.source,
        )

    def test_runtime_uses_rose_compatible_patcher_flags(self):
        ltk_source = (
            ROOT / "injection/overlay/ltk_host.py"
        ).read_text(encoding="utf-8")
        self.assertIn("LTK_PATCHER_FLAGS = 4", ltk_source)
        self.assertIn("LTK_PATCHER_LOG_LEVEL = 0x10", ltk_source)


if __name__ == "__main__":
    unittest.main()
