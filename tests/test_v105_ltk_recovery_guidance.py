#!/usr/bin/env python3
"""LTK startup recovery and diagnostic cleanup must reflect real compatibility."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, mock

from utils.integration import ltk_onboarding
from utils.core import issue_reporter


class LtkRecoveryGuidanceTests(TestCase):
    def test_expired_patcher_reports_compatibility_without_bypass(self):
        status = SimpleNamespace(
            missing=[], eol=1791072000,
            expired_for=lambda game_dir: True,
        )
        with (
            mock.patch.object(ltk_onboarding, "check_ltk_patcher", return_value=status),
            mock.patch.object(ltk_onboarding, "read_game_build", return_value=1792195200),
        ):
            text = ltk_onboarding.explain_ltk_runtime_problem(
                Path("c:/fake/tools"), Path("c:/fake/league")
            )
        self.assertIn("TOO OLD", text)
        self.assertIn("Replace BOTH LTK host and DLL", text)
        self.assertIn("Rebuilding PSM with this old", text)
        self.assertIn("Do not disable game security checks", text)

    def test_missing_pair_has_actionable_message(self):
        status = SimpleNamespace(missing=["missing file"], expired_for=lambda _: False)
        with mock.patch.object(ltk_onboarding, "check_ltk_patcher", return_value=status):
            text = ltk_onboarding.explain_ltk_runtime_problem(Path("fake"))
        self.assertIn("missing or failed integrity verification", text)

    def test_compatible_pair_keeps_startup_quiet(self):
        status = SimpleNamespace(missing=[], expired_for=lambda _: False)
        with mock.patch.object(ltk_onboarding, "check_ltk_patcher", return_value=status):
            self.assertIsNone(ltk_onboarding.explain_ltk_runtime_problem(Path("fake")))

    def test_legacy_migration_keeps_current_message_and_dedupe(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rose_diagnostics.txt"
            path.write_text(
                "Oct 31 03:38 | PSM cannot apply skins: the bundled LTK runtime does not support this League build.\\n"
                "Fix: old instructions\\n"
                "Oct 31 03:39 | LTK patcher outdated: this League build is newer than the selected DLL.\\n"
                "Fix: current instructions\\n",
                encoding="utf-8",
            )
            key = (
                "LTK_PATCHER_EOL|LTK patcher outdated: "
                "this League build is newer than the selected DLL."
            )
            with (
                mock.patch.object(issue_reporter, "_issues_path", return_value=path),
                mock.patch.dict(issue_reporter._LAST, {key: 123.0}, clear=True),
            ):
                self.assertTrue(
                    issue_reporter.clear_issue("LTK_PATCHER_EOL", legacy_only=True)
                )
                self.assertEqual(issue_reporter._LAST[key], 123.0)
            content = path.read_text("utf-8")
            self.assertNotIn("bundled LTK runtime", content)
            self.assertNotIn("old instructions", content)
            self.assertIn("LTK patcher outdated", content)
            self.assertIn("current instructions", content)

    def test_expiry_cleanup_removes_both_legacy_and_new_messages(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rose_diagnostics.txt"
            path.write_text(
                "Oct 31 03:38 | PSM cannot apply skins: the bundled LTK runtime does not support this League build.\n"
                "Fix: replace DLL\n"
                "Oct 31 03:38 | Injection unavailable: the current runtime cannot be used with this League build.\n"
                "Fix: fix runtime\n"
                "Oct 31 03:39 | LTK patcher outdated: this League build is newer than the selected DLL.\n"
                "Fix: update patcher\n"
                "Oct 31 03:40 | Other unrelated issue.\n",
                encoding="utf-8",
            )
            with mock.patch.object(issue_reporter, "_issues_path", return_value=path):
                self.assertTrue(issue_reporter.clear_issue("LTK_PATCHER_EOL"))
                self.assertTrue(issue_reporter.clear_issue("INJECTION_RUNTIME_UNAVAILABLE"))
            remaining = path.read_text(encoding="utf-8")
            self.assertNotIn("LTK patcher", remaining)
            self.assertNotIn("Injection unavailable", remaining)
            self.assertNotIn("Fix:", remaining)
            self.assertIn("Other unrelated issue.", remaining)


if __name__ == "__main__":
    import unittest
    unittest.main()
