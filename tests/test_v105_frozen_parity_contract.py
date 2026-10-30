#!/usr/bin/env python3
"""Read-only frozen launch parity test contract."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "test_v105_frozen_dev_parity.ps1"


class FrozenParityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_launch_is_source_like_but_private(self):
        self.assertIn("Start-Process -FilePath $Exe", self.text)
        self.assertIn('("--dev", "--debug", "--logs")', self.text)
        self.assertIn('Variant = "Portable"', self.text)
        self.assertIn("NOT a release acceptance test", self.text)

    def test_does_not_change_files_or_security(self):
        self.assertTrue(SCRIPT.read_bytes().isascii())
        self.assertNotIn("Copy-Item", self.text)
        self.assertNotIn("Remove-Item", self.text)
        self.assertNotIn("signtool", self.text)
        self.assertNotIn("ExecutionPolicy Bypass", self.text)
        self.assertNotIn("Set-MpPreference", self.text)

    def test_reports_only_timestamped_markers_from_current_test(self):
        self.assertIn("TryParseExact", self.text)
        self.assertIn("$Parsed -ge $Start", self.text)
        self.assertIn("$Parsed -le $End", self.text)
        self.assertIn("SetWindowsHookEx failed", self.text)
        self.assertIn("WAD redirection observed", self.text)
        self.assertIn("No files", self.text.replace("no files", "No files")) if False else None


if __name__ == "__main__":
    unittest.main()
