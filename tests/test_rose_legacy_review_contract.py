#!/usr/bin/env python3
"""Source checks for isolated Rose historical compatibility inspection."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REVIEW_SCRIPT = ROOT / "scripts" / "review_rose_ltk_v1281.ps1"


class RoseLegacyReviewContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = REVIEW_SCRIPT.read_text(encoding="utf-8")

    def test_review_script_is_powershell_51_ascii(self):
        self.assertTrue(REVIEW_SCRIPT.read_bytes().isascii())
        self.assertIn('Set-StrictMode -Version Latest', self.script)

    def test_historical_binaries_are_pinned_and_verified(self):
        self.assertIn("9f06802de5d83d6dde3ff1644a1c56049fadf9bb", self.script)
        self.assertIn("b2fc81c6de7bf5b40b81daaf8987706308ed5b33", self.script)
        self.assertIn("0cd0f58530906c3792e3189ea8af1a8f8bc6f264", self.script)
        self.assertIn("git hash-object", self.script)
        self.assertIn("audit_ltk_v1281_compatibility.py", self.script)

    def test_downloads_stay_in_ignored_isolated_audit_directory(self):
        self.assertIn(
            r'installer\candidates\v1.0.5\audit-only-ltk-v1.28.1',
            self.script,
        )
        self.assertIn("No active PSM binaries will be changed or executed", self.script)
        self.assertNotIn("Copy-Item", self.script)
        self.assertNotIn("Start-Process", self.script)
        self.assertNotIn("stage_ltk_v105_test.ps1", self.script)


if __name__ == "__main__":
    unittest.main()
