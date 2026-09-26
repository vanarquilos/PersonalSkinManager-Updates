#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Source-level invariants for the packaged PSM runtime."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleasePackagingTests(unittest.TestCase):
    def test_app_and_installer_versions_match(self):
        config = (ROOT / "config.py").read_text(encoding="utf-8")
        installer = (ROOT / "installer.iss").read_text(encoding="utf-8-sig")

        app = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', config)
        setup = re.search(r'#define MyAppVersion\s+"([^"]+)"', installer)

        self.assertIsNotNone(app)
        self.assertIsNotNone(setup)
        self.assertEqual(app.group(1), setup.group(1))

    def test_spec_bundles_current_runtime(self):
        spec = (ROOT / "PersonalSkinManager.spec").read_text(encoding="utf-8")
        for path in (
            "injection/tools/mod-tools.exe",
            "injection/tools/ltk_patcher_host.exe",
            "injection/tools/ltk_patcher_dll.dll",
        ):
            self.assertIn(path, spec)
        self.assertIn("'injection.overlay.ltk_host'", spec)

    def test_legacy_cslol_startup_dependency_is_retired(self):
        main = (ROOT / "main/__init__.py").read_text(encoding="utf-8")
        tools = (ROOT / "injection/tools/tools_manager.py").read_text(encoding="utf-8")
        self.assertNotIn("_check_dll_present", main)
        self.assertNotIn("cslol-dll.dll", tools)

    def test_release_runtime_does_not_use_legacy_runoverlay_fallback(self):
        overlay = (ROOT / "injection/overlay/overlay_manager.py").read_text(encoding="utf-8")
        self.assertNotIn("falling back to legacy CSLOL runoverlay", overlay)

    def test_release_verification_is_enabled(self):
        config = (ROOT / "config.py").read_text(encoding="utf-8")
        ltk = (ROOT / "injection/overlay/ltk_host.py").read_text(encoding="utf-8")
        self.assertIn("LTK_ENFORCE_SKINHACK_SCAN = True", config)
        self.assertIn("LTK_DEFAULT_FLAGS = 0", ltk)
        self.assertNotIn("LTK_OPT_OUT_AH_V1", ltk)


if __name__ == "__main__":
    unittest.main()
