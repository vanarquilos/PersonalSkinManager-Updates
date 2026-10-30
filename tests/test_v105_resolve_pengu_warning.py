#!/usr/bin/env python3
"""Old installed-client warning should not appear as an active Rose rollback error."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.resolve_stale_pengu_warning import (
    LEGACY_TIMESTAMP, LEGACY_MESSAGE, is_matching_issue,
    plan_removal, resolve_issue,
)


class ResolveStalePenguWarningTests(unittest.TestCase):
    def test_only_the_specific_old_issue_is_matched(self):
        self.assertTrue(is_matching_issue(f"{LEGACY_TIMESTAMP} | {LEGACY_MESSAGE}\n"))
        self.assertFalse(is_matching_issue(f"Oct 30 18:29 | {LEGACY_MESSAGE}\n"))
        self.assertFalse(is_matching_issue(f"{LEGACY_TIMESTAMP} | LTK patcher host failed.\n"))

    def test_filter_removes_adjacent_fix_only(self):
        original = [
            "Oct 30 11:45 | Other warning.\n",
            "Fix: Preserve this hint.\n",
            f"{LEGACY_TIMESTAMP} | {LEGACY_MESSAGE}\n",
            "Fix: Inspect the PSM/Pengu activation logs and installation permissions.\n",
            "Oct 30 11:47 | New failure.\n",
            "Fix: Still important.\n",
        ]
        result, count = plan_removal(original)
        self.assertEqual(count, 1)
        self.assertEqual(result, original[:2] + original[4:])

    def test_dry_run_does_not_modify_files(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "rose_diagnostics.txt"
            content = f"{LEGACY_TIMESTAMP} | {LEGACY_MESSAGE}\r\n"
            file.write_bytes(content.encode("utf-8"))
            n, backup = resolve_issue(file, apply=False)
            self.assertEqual(n, 1)
            self.assertIsNone(backup)
            self.assertEqual(file.read_bytes(), content.encode("utf-8"))
            self.assertEqual(list(Path(d).glob("rose_diagnostics.backup-*")), [])

    def test_applied_cleanup_creates_exact_backup_preserves_other_records(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "rose_diagnostics.txt"
            other = "Oct 30 11:50 | LTK runtime is incompatible.\r\n"
            original = (f"{LEGACY_TIMESTAMP} | {LEGACY_MESSAGE}\r\n"
                        "Fix: Inspect earlier Pengu activation logs.\r\n"
                        + other)
            file.write_bytes(original.encode("utf-8"))
            with patch("scripts.resolve_stale_pengu_warning.is_psm_active", return_value=False):
                n, backup = resolve_issue(file, apply=True)
            self.assertEqual(n, 1)
            self.assertIsNotNone(backup)
            self.assertEqual(backup.read_bytes(), original.encode("utf-8"))
            self.assertEqual(file.read_bytes(), other.encode("utf-8"))
            n, backup_again = resolve_issue(file, apply=True)
            self.assertEqual(n, 0)
            self.assertIsNone(backup_again)

    def test_active_psm_refuses_any_change(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "rose_diagnostics.txt"
            original = f"{LEGACY_TIMESTAMP} | {LEGACY_MESSAGE}\n"
            file.write_text(original, encoding="utf-8")
            with patch("scripts.resolve_stale_pengu_warning.is_psm_active", return_value=True):
                with self.assertRaisesRegex(RuntimeError, "Close PSM"):
                    resolve_issue(file, apply=True)
            self.assertEqual(file.read_text(encoding="utf-8"), original)
            self.assertEqual(list(Path(d).glob("rose_diagnostics.backup-*")), [])


if __name__ == "__main__":
    unittest.main()
