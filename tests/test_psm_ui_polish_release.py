#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release invariants for the visual-only PSM settings polish."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "Pengu Loader/plugins/PSM-UI-Polish/index.js"


class PsmUiPolishReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PLUGIN.read_text(encoding="utf-8")

    def test_all_existing_v102_sections_keep_original_numbering(self):
        for token in (
            "01 / RUNTIME",
            "02 / STARTUP",
            "03 / GAME",
            "04 / CONTENT",
            "05 / TOOLS",
            "06 / ABOUT",
        ):
            self.assertIn(token, self.source)

    def test_section_icons_are_present(self):
        for icon in ("runtime", "startup", "game", "content", "tools", "about"):
            self.assertIn(f"{icon}:", self.source)
        self.assertIn("psm-core-section-icon", self.source)

    def test_release_ui_does_not_include_client_automation_surface(self):
        self.assertNotIn("psm-client-automation-modal", self.source)
        self.assertNotIn("psm-client-automation-launcher", self.source)
        self.assertNotIn("02 / CLIENT AUTOMATION", self.source)

    def test_polish_is_visual_only(self):
        forbidden = (
            "client-automation-settings-save",
            "client-automation-settings-request",
            "auto_queue_enabled",
            "auto_accept_enabled",
            "auto_pick_enabled",
            "auto_ban_enabled",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)


if __name__ == "__main__":
    unittest.main()
