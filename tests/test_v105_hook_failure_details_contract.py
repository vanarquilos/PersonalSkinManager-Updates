#!/usr/bin/env python3
"""Read-only, timestamp-gated sanitized hook failure classifier contract."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "inspect_v105_hook_failure_details.ps1"


class FrozenHookFailureDetailContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = AUDIT.read_text(encoding="utf-8")

    def test_powershell_51_ascii(self):
        self.assertTrue(AUDIT.read_bytes().isascii())

    def test_requires_explicit_test_start_and_strict_timestamp_parsing(self):
        self.assertIn("[Parameter(Mandatory = $true)][datetime]$SinceLocal", self.source)
        self.assertIn("[datetime]::ParseExact", self.source)
        self.assertIn('$Stamp -lt $SinceLocal.AddSeconds(-2)', self.source)

    def test_hook_error_code_is_extracted_not_full_raw_lines(self):
        self.assertIn("SetWindowsHookEx failed", self.source)
        self.assertIn("NO_NUMERIC_CODE", self.source)
        self.assertIn('Samples (timestamp, category, code only)', self.source)
        self.assertNotIn('Write-Host $Line', self.source)

    def test_differentiates_launcher_overlay_and_host(self):
        for label in (
            "Launcher startup", "Host verification errors", "Host attached",
            "Overlay preparation", "DLL overlay initialized", "WAD redirection"
        ):
            with self.subTest(label=label):
                self.assertIn(label, self.source)

    def test_never_mutates_or_injects(self):
        for action in (
            "Set-Content", "Out-File", "Add-Content", "Copy-Item",
            "Move-Item", "Remove-Item", "Start-Process", "Invoke-Expression",
            "gh release create",
        ):
            with self.subTest(action=action):
                self.assertNotIn(action, self.source)


if __name__ == "__main__":
    unittest.main()
