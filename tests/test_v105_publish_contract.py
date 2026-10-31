#!/usr/bin/env python3
"""Fail-closed checks for a GitHub v1.0.5 pre-release (never stable)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PreReleasePublicationContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.publish = (ROOT / "scripts/publish_v105_prerelease.ps1").read_text("utf-8")
        cls.notes = (ROOT / "releases/v1.0.5/GITHUB_PRERELEASE_NOTES.md").read_text("utf-8")

    def test_windows_powershell_source_is_ascii(self):
        self.assertTrue((ROOT / "scripts/publish_v105_prerelease.ps1").read_bytes().isascii())

    def test_publish_requires_positive_post_install_gameplay_verification(self):
        for flag in (
            "ConfirmedCleanInstall",
            "ConfirmedPackagedPracticeTool",
            "ConfirmedPackagedSwiftplay",
            "ConfirmedSecondMatch",
            "Publish",
        ):
            self.assertIn("[switch]$" + flag, self.publish)
        self.assertIn("RELEASE CANDIDATE - NOT PUBLISHED", self.publish)
        self.assertIn("official_vendor_signatures_removed", self.publish)
        self.assertIn("source_commit -ne $Head", self.publish)
        self.assertIn("Hash -ne [string]$Audit.sha256", self.publish)

    def test_old_elevated_candidate_cannot_be_published(self):
        self.assertIn('$Audit.launch_profile -ne "asInvoker"', self.publish)
        self.assertIn("Legacy or unreviewed release candidate", self.publish)
        self.assertIn("ConfirmedPackagedPracticeTool", self.publish)
        self.assertIn("ConfirmedPackagedSwiftplay", self.publish)
        self.assertIn("ConfirmedSecondMatch", self.publish)

    def test_github_release_is_prerelease_and_non_destructive(self):
        self.assertIn("gh release create $Tag $Published", self.publish)
        self.assertIn("--prerelease", self.publish)
        self.assertIn("gh release view $Tag", self.publish)
        self.assertNotIn("stable/manifest.json", self.publish)
        self.assertNotIn("gh release delete", self.publish)
        self.assertIn("Stable update manifest is unchanged", self.publish)

    def test_public_notes_include_third_party_license_and_risk(self):
        self.assertIn("LTK Patcher License", self.notes)
        self.assertIn("pre-release", self.notes.lower())
        self.assertIn("https://github.com/vanarquilos/PersonalSkinManager-Updates/issues", self.notes)


if __name__ == "__main__":
    unittest.main()
