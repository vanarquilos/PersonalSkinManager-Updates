#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic invariants for the final PSM settings/control-surface polish."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "Pengu Loader/plugins/PSM-UI-Polish/index.js"


class PsmUiPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PLUGIN.read_text(encoding="utf-8")

    def test_all_main_settings_sections_receive_icons(self):
        for token in (
            "01 / RUNTIME",
            "02 / STARTUP",
            "03 / GAME",
            "04 / CONTENT",
            "05 / TOOLS",
            "06 / ABOUT",
        ):
            self.assertIn(token, self.source)
        self.assertIn("psm-core-section-icon", self.source)

    def test_client_automation_is_numbered_after_main_settings(self):
        self.assertIn("07 / CLIENT AUTOMATION", self.source)

    def test_matchmaking_layout_is_reordered_into_coherent_rows(self):
        self.assertIn("psm-ca-final-matchmaking", self.source)
        for control_id in (
            "#psm-ca-queue-search",
            "#psm-ca-auto-queue",
            "#psm-ca-auto-requeue",
            "#psm-ca-primary-position",
            "#psm-ca-secondary-position",
            "#psm-ca-auto-accept",
            "#psm-ca-accept-delay",
        ):
            self.assertIn(control_id, self.source)

    def test_protect_ally_intents_is_grouped_with_ban_priority(self):
        self.assertIn("#psm-ca-protect-ally", self.source)
        self.assertIn("#psm-ca-ban-input", self.source)
        self.assertIn("psm-ca-inline-protect", self.source)

    def test_control_surface_uses_consistent_switch_and_sticky_actions(self):
        self.assertIn('input[type="checkbox"]', self.source)
        self.assertIn("position:sticky", self.source)
        self.assertIn("psm-ca-actions", self.source)


if __name__ == "__main__":
    unittest.main()
