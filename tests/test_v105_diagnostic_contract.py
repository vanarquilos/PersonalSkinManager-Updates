#!/usr/bin/env python3
"""Source checks for the read-only Windows no-skin diagnostic report."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC = ROOT / "scripts" / "diagnose_no_skin_v105.ps1"


class V105DiagnosticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DIAGNOSTIC.read_text(encoding="utf-8-sig")

    def test_powershell_51_source_is_ascii_and_does_not_expose_raw_logs(self):
        self.assertTrue(DIAGNOSTIC.read_bytes().isascii())
        self.assertIn('This report contains only known failure markers and hashes', self.source)
        self.assertIn('Share this report rather than full League Client logs', self.source)
        self.assertIn('$summary | Set-Content', self.source)
        self.assertNotIn('$lines | Set-Content', self.source)

    def test_vendor_host_verification_has_separate_terminal_classification(self):
        self.assertIn('"LTK host verification refused"', self.source)
        self.assertIn('$Counts["LTK host verification refused"] -gt 0', self.source)
        self.assertIn('never bypass verification.', self.source)

    def test_builder_failure_is_scoped_to_last_selected_skin(self):
        self.assertIn('$lastSkinIndex = -1', self.source)
        self.assertIn('Using skin file:', self.source)
        self.assertIn('$attemptLines = @($lines[$lastSkinIndex..($lines.Count - 1)])', self.source)
        self.assertIn('$builderOutcome = "unknown"', self.source)
        self.assertIn('$builderOutcome -eq "failed"', self.source)
        self.assertIn('$Markers["WAD header validation failed"]', self.source)
        self.assertNotIn('error.*mkoverlay', self.source)


if __name__ == "__main__":
    unittest.main()
