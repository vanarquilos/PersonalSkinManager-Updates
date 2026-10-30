#!/usr/bin/env python3
"""Static no-mutation tests for the source-to-installed LTK parity audit."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "inspect_v105_installed_parity.ps1"


class InstalledParityAuditContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_powershell_51_ascii(self):
        self.assertTrue(SCRIPT.read_bytes().isascii())

    def test_explicit_source_staging_and_installed_paths(self):
        for name in ("SourceToolsDir", "UnsignedLtkDir", "InstalledDir", "InstalledIdentity"):
            with self.subTest(name=name):
                self.assertIn(name, self.source)

    def test_all_four_runtime_binaries(self):
        for name in ("mod-tools.exe", "cslol-dll.dll", "ltk_patcher_host.exe", "ltk_patcher_dll.dll"):
            with self.subTest(name=name):
                self.assertIn(name, self.source)

    def test_both_pyinstaller_layouts_checked(self):
        self.assertIn("_internal\\injection\\tools", self.source)
        self.assertIn("injection\\tools", self.source)
        self.assertIn("Duplicate installed copies", self.source)

    def test_compares_exact_original_unsigned_qa_pair(self):
        self.assertIn("5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9", self.source)
        self.assertIn("B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29", self.source)
        self.assertIn("installed matches unsigned source QA bytes", self.source)

    def test_does_not_assume_installed_identity(self):
        self.assertIn('InstalledIdentity = "Unknown"', self.source)
        self.assertIn("may be the WORKING private version", self.source)
        self.assertIn('HistoricalUnsignedFailed', self.source)
        self.assertIn("old failed unsigned installation", self.source)

    def test_never_claims_skin_render_or_public_release_approval(self):
        self.assertIn("not a packaged QA pass", self.source)
        self.assertIn("No public release approved", self.source)
        self.assertIn("Shared Rose logs cannot be attributed", self.source)

    def test_read_only_static_contract(self):
        for command in (
            "Remove-Item", "Copy-Item", "Move-Item", "Set-Content", "Out-File",
            "Add-Content", "Start-Process", "Invoke-WebRequest",
            "Set-AuthenticodeSignature", "signtool", "gh release create",
            "git reset", "git clean",
        ):
            with self.subTest(command=command):
                self.assertNotIn(command, self.source)


if __name__ == "__main__":
    unittest.main()
