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

    def test_v105_is_local_test_candidate_only(self):
        config = (ROOT / "config.py").read_text(encoding="utf-8")
        installer = (ROOT / "installer.iss").read_text(encoding="utf-8-sig")
        script = (ROOT / "scripts/prepare_v1_0_5_test.ps1").read_text(encoding="utf-8")
        audit = (ROOT / "scripts/audit_runtime_v105.py").read_text(encoding="utf-8")

        self.assertIn('APP_VERSION = "1.0.5"', config)
        self.assertIn('#define MyAppVersion "1.0.5"', installer)
        self.assertIn('#define MyAppVersionInfo "1.0.5.0"', installer)
        self.assertIn("PersonalSkinManager_Setup_v1.0.5-TEST.exe", script)
        self.assertIn("candidate-manifest.json", script)
        self.assertIn("scripts\\audit_runtime_v105.py", script.replace("/", "\\"))
        self.assertNotIn("gh release create", script.lower())
        self.assertNotIn("stable/manifest.json", script)
        self.assertIn("sha256", audit)
        self.assertIn("read_game_build", audit)

    def test_windows_powershell_51_candidate_scripts_are_ascii(self):
        # Windows PowerShell 5.1 reads UTF-8 without a BOM using the local
        # Windows ANSI codepage. Characters such as em dashes can corrupt
        # quoted strings and make the entire script fail to parse.
        for relative in (
            "scripts/diagnose_no_skin_v105.ps1",
            "scripts/prepare_v1_0_5_test.ps1",
        ):
            with self.subTest(script=relative):
                raw = (ROOT / relative).read_bytes()
                self.assertTrue(raw.isascii(), f"{relative} must be ASCII-only")

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

    def test_release_runtime_matches_rose_1_3_1_patcher_mode(self):
        config = (ROOT / "config.py").read_text(encoding="utf-8")
        ltk = (ROOT / "injection/overlay/ltk_host.py").read_text(encoding="utf-8")
        self.assertIn("LTK_ENFORCE_SKINHACK_SCAN = False", config)
        self.assertIn("LTK_PATCHER_FLAGS = 4", ltk)
        self.assertIn("LTK_PATCHER_LOG_LEVEL = 0x10", ltk)

    def test_ltk_eol_is_checked_against_the_installed_game_build(self):
        patcher = (ROOT / "injection/tools/patcher.py").read_text(encoding="utf-8")
        tools = (ROOT / "injection/tools/tools_manager.py").read_text(encoding="utf-8")
        ltk = (ROOT / "injection/overlay/ltk_host.py").read_text(encoding="utf-8")
        injector = (ROOT / "injection/core/injector.py").read_text(encoding="utf-8")

        self.assertIn("def expired_for(self, game_dir", patcher)
        self.assertIn("def read_game_build(game_dir", patcher)
        self.assertIn("patcher.expired_for(game_dir)", tools)
        self.assertIn("patcher.expired_for(game_dir)", ltk)
        self.assertIn("check_tools_available(self.game_dir)", injector)
        self.assertNotIn("return self.eol is not None and time.time() > self.eol", patcher)


    def test_swiftplay_uses_retryable_regular_runtime_lifecycle(self):
        swift = (ROOT / "threads/handlers/swiftplay_handler.py").read_text(encoding="utf-8")
        phase = (ROOT / "threads/handlers/phase_handler.py").read_text(encoding="utf-8")
        ws = (ROOT / "threads/websocket/websocket_event_handler.py").read_text(encoding="utf-8")

        self.assertIn("make_game_ended_callback(self.state)", swift)
        self.assertIn("will retry while Searching", swift)
        self.assertIn("self._overlay_done = False", swift)
        self.assertIn("def start_swiftplay_overlay_async", swift)
        self.assertIn("Swiftplay overlay worker already active", swift)
        self.assertLess(
            swift.index("Swiftplay overlay worker already active"),
            swift.index("if not self.state.swiftplay_extracted_mods:", swift.index("def start_swiftplay_overlay_async")),
        )
        self.assertIn('start_swiftplay_overlay_async("ChampSelect")', phase)
        self.assertIn('start_swiftplay_overlay_async("GameStart")', phase)
        self.assertIn('start_swiftplay_overlay_async("InProgress")', phase)
        self.assertIn('"WS-ChampSelect"', ws)
        self.assertNotIn("self.swiftplay_handler._injection_triggered = True", phase)

        rose_ui = (ROOT / "Pengu Loader/plugins/ROSE-UI/index.js").read_text(encoding="utf-8")
        self.assertIn("function syncSwiftplayBanners()", rose_ui)
        self.assertIn("syncSwiftplayBanners();", rose_ui)
        self.assertIn(".quick-play-skin-select-component .thumbnail-wrapper.active-skin", rose_ui)


if __name__ == "__main__":
    unittest.main()
