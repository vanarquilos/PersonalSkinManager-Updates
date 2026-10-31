#!/usr/bin/env python3
"""Existing LTK inventory must never confuse a cutoff with a working skin."""
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from scripts import audit_existing_ltk_pairs_v105 as audit


class ExistingLtkPairsAuditTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / "candidate"
        self.folder.mkdir()
        (self.folder / audit.LTK_PATCHER_HOST).write_bytes(b"host fixture")
        (self.folder / audit.LTK_PATCHER_DLL).write_bytes(b"dll fixture")

    def test_game_build_after_cutoff_is_expired(self):
        with mock.patch.object(audit, "read_dll_eol", return_value=100):
            items = audit.find_pairs([self.root], game_build=101)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "EXPIRED_FOR_INSTALLED_GAME")

    def test_cutoff_not_exceeded_is_not_claimed_working(self):
        with mock.patch.object(audit, "read_dll_eol", return_value=100):
            items = audit.find_pairs([self.root], game_build=100)
        self.assertEqual(items[0]["status"], "CUTOFF_NOT_EXCEEDED")
        self.assertNotIn("WORKING", items[0]["status"])
        self.assertIsNotNone(items[0]["host_sha256"])
        self.assertIsNotNone(items[0]["dll_sha256"])

    def test_unrecognized_cutoff_cannot_be_called_supported(self):
        with mock.patch.object(audit, "read_dll_eol", return_value=None):
            items = audit.find_pairs([self.root], game_build=101)
        self.assertEqual(items[0]["status"], "UNKNOWN_DLL_CUTOFF")

    def test_missing_dll_does_not_pass(self):
        (self.folder / audit.LTK_PATCHER_DLL).unlink()
        self.assertEqual(
            audit.find_pairs([self.root], game_build=100)[0]["status"],
            "INCOMPLETE_OR_LINKED",
        )

    def test_no_root_no_pair_and_no_file_changes(self):
        self.assertEqual(audit.find_pairs([self.root / "missing"], None), [])
        original = (self.folder / audit.LTK_PATCHER_HOST).read_bytes()
        with mock.patch.object(audit, "read_dll_eol", return_value=100):
            audit.find_pairs([self.root], game_build=99)
        self.assertEqual((self.folder / audit.LTK_PATCHER_HOST).read_bytes(), original)

    def test_direct_python_scripts_invocation_adds_project_root(self):
        source = Path(audit.__file__).read_text("utf-8")
        self.assertIn("ROOT = Path(__file__).resolve().parents[1]", source)
        self.assertIn("sys.path.insert(0, str(ROOT))", source)
        self.assertLess(
            source.index("sys.path.insert(0, str(ROOT))"),
            source.index("from injection.tools.patcher import"),
        )

    def test_no_external_execution_download_or_signature_override(self):
        source = Path(audit.__file__).read_text("utf-8")
        for prohibited in (
            "subprocess.", "urllib.", "requests.", "Start-Process",
            "SetWindowsHookEx", "remove signature", "Copy-Item",
        ):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, source)


if __name__ == "__main__":
    import unittest
    unittest.main()
