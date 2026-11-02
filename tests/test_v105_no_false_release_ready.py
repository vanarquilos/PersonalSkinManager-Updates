#!/usr/bin/env python3
"""v1.0.5 compilation is never evidence of working in-game skins or approval."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QAReleaseReportingContracts(unittest.TestCase):
    def test_build_all_does_not_invite_unverified_public_distribution(self):
        source = (ROOT / "scripts/build_all.py").read_text(encoding="utf-8-sig")
        self.assertIn("PRIVATE QA ONLY - DO NOT PUBLISH OR DISTRIBUTE THIS BUILD", source)
        self.assertIn("User-provided LTK host/DLL is NOT bundled.", source)
        self.assertNotIn('print("  • For distribution:")', source)
        self.assertNotIn('print(f"    Share:', source)

    def test_inno_compiler_reports_qa_not_skin_ready(self):
        source = (ROOT / "scripts/create_installer.py").read_text(encoding="utf-8-sig")
        self.assertIn("LOCAL QA INSTALLER BUILT - NOT A VERIFIED PUBLIC RELEASE", source)
        self.assertIn("The official LTK host/DLL pair is NOT included.", source)
        self.assertIn("In-game skin rendering, security/rights", source)
        self.assertNotIn('print("Installer Ready!")', source)

    def test_private_builder_reports_unverified_gameplay(self):
        source = (
            ROOT / "scripts/build_v105_rose_style_frozen_private_qa.ps1"
        ).read_text(encoding="ascii")
        self.assertIn('gameplay_skin_rendering = "NOT_TESTED"', source)
        self.assertIn("user_provided_ltk_bundled = $false", source)
        self.assertIn("public_distribution_approved = $false", source)


if __name__ == "__main__":
    unittest.main()
