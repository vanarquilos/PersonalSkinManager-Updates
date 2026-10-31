#!/usr/bin/env python3
"""v1.0.5 LTK expiry is the root-cause diagnostic, not two generic errors."""
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from injection.tools.tools_manager import ToolsManager

ROOT = Path(__file__).resolve().parents[1]


class LtkExpiryTroubleshootingTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / "mod-tools.exe").write_bytes(b"test-fixture")
        (self.folder / "ltk_patcher_host.exe").write_bytes(b"test-host-fixture")
        (self.folder / "ltk_patcher_dll.dll").write_bytes(b"test-dll-fixture")
        self.manager = ToolsManager(self.folder)

    def _status(self, *, expired=False, missing=None):
        return SimpleNamespace(
            host=self.folder / "ltk_patcher_host.exe",
            dll=self.folder / "ltk_patcher_dll.dll",
            missing=missing or [],
            eol=1791072000,  # 2026-10-04 UTC
            expired_for=lambda _: expired,
        )

    def test_newer_league_build_shows_one_actionable_ltk_error(self):
        with (
            mock.patch("injection.tools.tools_manager.check_ltk_patcher",
                       return_value=self._status(expired=True)),
            mock.patch("injection.tools.tools_manager.read_game_build",
                       return_value=1792195200),
            mock.patch("injection.tools.tools_manager.report_issue") as report,
        ):
            self.assertFalse(self.manager.check_tools_available(self.folder))
        self.assertEqual(self.manager.last_failure_code, "LTK_PATCHER_EOL")
        report.assert_called_once()
        kwargs = report.call_args.kwargs
        self.assertEqual(report.call_args.args[0], "LTK_PATCHER_EOL")
        self.assertIn("Replace BOTH LTK host and DLL", kwargs["hint"])
        self.assertIn("2026", kwargs["hint"])
        self.assertIn("Do not reuse the expired pair", kwargs["hint"])

    def test_incomplete_pair_reports_missing_not_expiry(self):
        with (
            mock.patch("injection.tools.tools_manager.check_ltk_patcher",
                       return_value=self._status(expired=True, missing=["invalid pair"])),
            mock.patch("injection.tools.tools_manager.report_issue") as report,
        ):
            self.assertFalse(self.manager.check_tools_available(self.folder))
        self.assertEqual(self.manager.last_failure_code, "LTK_PATCHER_MISSING")
        self.assertEqual(report.call_args.args[0], "LTK_PATCHER_MISSING")

    def test_good_pair_clears_previous_failure_code(self):
        with (
            mock.patch("injection.tools.tools_manager.check_ltk_patcher",
                       return_value=self._status(expired=True)),
            mock.patch("injection.tools.tools_manager.read_game_build",
                       return_value=1792195200),
            mock.patch("injection.tools.tools_manager.report_issue"),
        ):
            self.assertFalse(self.manager.check_tools_available(self.folder))
        self.assertEqual(self.manager.last_failure_code, "LTK_PATCHER_EOL")

        with mock.patch("injection.tools.tools_manager.check_ltk_patcher",
                        return_value=self._status(expired=False)):
            self.assertTrue(self.manager.check_tools_available(self.folder))
        self.assertIsNone(self.manager.last_failure_code)

    def test_legacy_double_error_strings_are_not_emitted_by_current_branch(self):
        tools_source = (ROOT / "injection/tools/tools_manager.py").read_text("utf-8")
        manager_source = (ROOT / "injection/core/manager.py").read_text("utf-8")
        self.assertNotIn(
            "PSM cannot apply skins: the bundled LTK runtime does not support this League build.",
            tools_source,
        )
        self.assertNotIn(
            "Injection unavailable: the current runtime cannot be used with this League build.",
            manager_source,
        )
        self.assertIn("LTK patcher outdated:", tools_source)

    def test_injection_manager_does_not_duplicate_root_error(self):
        content = (ROOT / "injection/core/manager.py").read_text("utf-8")
        self.assertIn('"last_failure_code", None', content)
        self.assertIn("if not failure:", content)
        self.assertIn("ToolsManager has already reported the specific cause", content)


if __name__ == "__main__":
    import unittest
    unittest.main()
