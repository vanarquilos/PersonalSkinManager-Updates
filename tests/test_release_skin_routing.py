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

    def test_owned_riot_skins_use_native_lcu_without_overlay(self):
        start = self.source.index("# Native client selection needs no overlay")
        end = self.source.index("# Owning a base cosmetic", start)
        route = self.source[start:end]
        self.assertIn("effective_skin_id in (owned_skin_ids or set())", route)
        self.assertIn("not is_default_skin(effective_skin_id)", route)
        self.assertIn("self._force_owned_skin(effective_skin_id)", route)
        self.assertIn("discard_early_patcher()", route)
        self.assertNotIn("inject_skin_immediately", route)
        self.assertIn("Visual rendering not verified", route)

    def test_owned_base_does_not_imply_chroma_ownership(self):
        start = self.source.index("# Owning a base cosmetic")
        end = self.source.index("# Inject if user doesn't own", start)
        route = self.source[start:end]
        self.assertIn("Chroma ownership not confirmed", route)
        self.assertNotIn("_force_owned_skin(", route)
        self.assertNotIn("inject_skin_immediately", route)

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

    def test_runtime_uses_upstream_content_enforcement_flags(self):
        ltk_source = (
            ROOT / "injection/overlay/ltk_host.py"
        ).read_text(encoding="utf-8")
        self.assertIn("LTK_PATCHER_FLAGS = 0", ltk_source)
        self.assertIn("LTK_PATCHER_LOG_LEVEL = 0x10", ltk_source)


if __name__ == "__main__":
    unittest.main()
