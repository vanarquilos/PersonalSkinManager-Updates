#!/usr/bin/env python3
"""Regression checks for the isolated v1.0.5 public-path LOCAL-ONLY builder."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_v105_public_path_local_test.ps1"
PREFLIGHT = ROOT / "scripts" / "preflight_v105_public_candidate.ps1"
SPEC = ROOT / "PersonalSkinManager.spec"
PYINSTALLER = ROOT / "scripts" / "build_pyinstaller.py"


class PublicPathLocalInstallerContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = BUILD.read_text("utf-8")
        cls.preflight = PREFLIGHT.read_text("utf-8")
        cls.spec = SPEC.read_text("utf-8")
        cls.pyinstaller = PYINSTALLER.read_text("utf-8")

    def test_powershell_51_files_are_ascii(self):
        self.assertTrue(BUILD.read_bytes().isascii())
        self.assertTrue(PREFLIGHT.read_bytes().isascii())

    def test_four_runtime_files_explicitly_required(self):
        for name in ("mod-tools.exe", "cslol-dll.dll", "ltk_patcher_host.exe", "ltk_patcher_dll.dll"):
            for part in (self.builder, self.preflight):
                self.assertIn(name, part)
        self.assertIn("cslol-dll.dll", self.spec)
        self.assertIn("cslol-dll.dll", self.pyinstaller)
        self.assertIn("PSM_RELEASE_CSLOL_DIR", self.spec)
        self.assertIn("PSM_RELEASE_CSLOL_DIR", self.pyinstaller)
        self.assertIn("PSM_RELEASE_LTK_DIR", self.builder)

    def test_isolation_guards_protect_the_original_worktree(self):
        self.assertIn("Test-Path -LiteralPath $GitMarker -PathType Leaf", self.builder)
        self.assertIn("LINKED GIT WORKTREE", self.builder)
        self.assertIn("Refusing to overwrite mod-tools.exe", self.builder)
        self.assertIn("Refusing to replace existing build output", self.builder)
        self.assertNotIn("git reset", self.builder.lower())
        self.assertNotIn("git clean", self.builder.lower())
        self.assertNotIn("Remove-Item", self.builder)

    def test_signing_and_known_failure_gates(self):
        for content in (self.builder, self.preflight):
            self.assertIn("SetWindowsHookEx", content)
            self.assertIn("5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9", content)
            self.assertIn("B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29", content)
            self.assertIn("TimeStamperCertificate", content)
            self.assertIn("league", content.lower())
        self.assertIn('CSLOL.Status -ne "Valid"', self.builder)
        self.assertIn("SignerCertificate", self.builder)

    def test_explicit_all_component_integrity_verification(self):
        self.assertIn("foreach ($Name in $Inputs.Keys)", self.builder)
        self.assertIn("Get-ChildItem -LiteralPath $Dist", self.builder)
        self.assertIn("Packaged $Name differs from audited input", self.builder)
        self.assertIn("package_sha256", self.builder)
        self.assertIn("source_commit", self.builder)

    def test_local_test_only_no_github_publication(self):
        self.assertIn("LOCAL WINDOWS TEST ONLY - NOT PUBLICATION APPROVED", self.builder)
        self.assertIn("public_distribution_approved = $false", self.builder)
        self.assertIn('license_content_enforcement_review = "PENDING"', self.builder)
        self.assertNotIn("gh release create", self.builder)
        self.assertNotIn("stable/manifest.json", self.builder)
        self.assertNotIn("gh release create", self.preflight)


if __name__ == "__main__":
    unittest.main()
