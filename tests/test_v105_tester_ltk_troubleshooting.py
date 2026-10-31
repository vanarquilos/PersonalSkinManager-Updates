#!/usr/bin/env python3
"""Regression tests for the original source tester screenshot's two LTK errors."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, mock

from injection.tools.tools_manager import ToolsManager
from utils.core import issue_reporter


class TesterLtkTroubleshootingRegressionTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tools = Path(self.temp.name) / "tools"
        self.tools.mkdir()
        for name in ("mod-tools.exe", "ltk_patcher_host.exe", "ltk_patcher_dll.dll"):
            (self.tools / name).write_bytes(b"test-fixture")
        self.manager = ToolsManager(self.tools)

    def _status(self, *, expired):
        return SimpleNamespace(
            host=self.tools / "ltk_patcher_host.exe",
            dll=self.tools / "ltk_patcher_dll.dll",
            missing=[],
            eol=1792310400,
            expired_for=lambda _: expired,
        )

    def test_outdated_patcher_reports_one_specific_error(self):
        with (
            mock.patch("injection.tools.tools_manager.check_ltk_patcher", return_value=self._status(expired=True)),
            mock.patch("injection.tools.tools_manager.read_game_build", return_value=1793406452),
            mock.patch("injection.tools.tools_manager.clear_issue"),
            mock.patch("injection.tools.tools_manager.report_issue") as issue,
        ):
            self.assertFalse(self.manager.check_tools_available(self.tools))
        self.assertEqual(self.manager.last_failure_code, "LTK_PATCHER_EOL")
        issue.assert_called_once()
        self.assertEqual(issue.call_args.args[0], "LTK_PATCHER_EOL")
        self.assertIn("2026-10", issue.call_args.kwargs["hint"])
        self.assertIn("Obtain a newer", issue.call_args.kwargs["hint"])

    def test_correct_pair_clears_earlier_failure(self):
        with (
            mock.patch("injection.tools.tools_manager.check_ltk_patcher", return_value=self._status(expired=True)),
            mock.patch("injection.tools.tools_manager.read_game_build", return_value=1793406452),
            mock.patch("injection.tools.tools_manager.report_issue"),
            mock.patch("injection.tools.tools_manager.clear_issue"),
        ):
            self.assertFalse(self.manager.check_tools_available(self.tools))
        self.assertEqual(self.manager.last_failure_code, "LTK_PATCHER_EOL")

        with (
            mock.patch("injection.tools.tools_manager.check_ltk_patcher", return_value=self._status(expired=False)),
            mock.patch("injection.tools.tools_manager.clear_issue") as cleared,
        ):
            self.assertTrue(self.manager.check_tools_available(self.tools))
        self.assertIsNone(self.manager.last_failure_code)
        self.assertEqual(cleared.call_count, 2)

    def test_old_troubleshooting_messages_removed_without_erasing_new_one(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "rose_diagnostics.txt"
            path.write_text(
                "Oct 31 12:37 | PSM cannot apply skins: the bundled LTK runtime does not support this League build.\n"
                "Fix: old advice\n"
                "Oct 31 12:37 | Injection unavailable: the current runtime cannot be used with this League build.\n"
                "Fix: generic advice\n"
                "Oct 31 12:38 | LTK patcher outdated: its DLL does not support this League build.\n"
                "Fix: current advice\n",
                encoding="utf-8",
            )
            with mock.patch.object(issue_reporter, "_issues_path", return_value=path):
                self.assertTrue(issue_reporter.clear_issue("INJECTION_RUNTIME_UNAVAILABLE"))
                self.assertTrue(issue_reporter.clear_issue("LTK_PATCHER_EOL", legacy_only=True))
            new_text = path.read_text("utf-8")
            self.assertNotIn("bundled LTK runtime", new_text)
            self.assertNotIn("Injection unavailable", new_text)
            self.assertIn("LTK patcher outdated", new_text)
            self.assertIn("current advice", new_text)

    def test_injection_manager_uses_tools_failure_without_double_error(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "injection/core/manager.py").read_text("utf-8")
        self.assertIn('"last_failure_code", None', source)
        self.assertIn("if not failure:", source)
        self.assertNotIn(
            "Injection unavailable: the current runtime cannot be used with this League build.",
            source,
        )


if __name__ == "__main__":
    import unittest
    unittest.main()
