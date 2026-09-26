#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release invariants for supported skin/mod routing."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRIGGER = ROOT / "threads/handlers/injection_trigger.py"
SPECIAL_CASES = ROOT / "ui/chroma/special_cases.py"
SELECTION_HANDLER = ROOT / "ui/chroma/selection_handler.py"
ZIP_RESOLVER = ROOT / "injection/mods/zip_resolver.py"


class ReleaseSkinRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TRIGGER.read_text(encoding="utf-8")
        cls.special_cases = SPECIAL_CASES.read_text(encoding="utf-8")
        cls.selection_handler = SELECTION_HANDLER.read_text(encoding="utf-8")
        cls.zip_resolver = ZIP_RESOLVER.read_text(encoding="utf-8")

    def test_owned_riot_skins_use_lcu_without_overlay(self):
        self.assertIn("Owned Riot skin/chroma selected via LCU;", self.source)
        self.assertIn("no overlay required", self.source)

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

    def test_kaisa_forms_use_explicit_local_archives(self):
        self.assertIn("def get_kaisa_forms", self.special_cases)
        self.assertIn("Uzi Kaisa Form 1.zip", self.special_cases)
        self.assertIn("Uzi Kaisa Form 2.zip", self.special_cases)
        self.assertIn(
            "self._handle_kaisa_form_selection(chroma_id, chroma_name)",
            self.selection_handler,
        )
        self.assertIn(
            'injection_source = selected_form_path or name',
            self.source,
        )
        self.assertIn(
            "Resolved local form/mod archive",
            self.zip_resolver,
        )

    def test_runtime_verification_stays_enabled(self):
        ltk_source = (
            ROOT / "injection/overlay/ltk_host.py"
        ).read_text(encoding="utf-8")
        self.assertIn("LTK_DEFAULT_FLAGS = 0", ltk_source)


if __name__ == "__main__":
    unittest.main()
