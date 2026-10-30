#!/usr/bin/env python3
"""Contract tests: local frozen parity QA cannot be a public installer build."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "scripts/build_v105_frozen_parity_private_qa.ps1"


class FrozenParityPrivateQaContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = FROZEN.read_text(encoding="utf-8")

    def test_legacy_powershell_compatibility(self):
        self.assertTrue(FROZEN.read_bytes().isascii())

    def test_all_four_inputs_are_hash_pinned(self):
        for sha in (
            "25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44",
            "4A009619C6DEA691780B2F20CF17E08DE478A78B3F11CD72759DD71C00AD1C90",
            "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9",
            "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29",
        ):
            self.assertIn(sha, self.script)

    def test_only_runs_in_isolated_linked_worktree(self):
        self.assertIn("LINKED GIT WORKTREE", self.script)
        self.assertIn('Test-Path -LiteralPath (Join-Path $Root ".git") -PathType Leaf', self.script)
        self.assertIn('release/v105-public-installer-staging', self.script)
        self.assertIn("Local mod-tools.exe exists in this worktree; refusing to overwrite.", self.script)
        self.assertNotIn("git reset", self.script.lower())
        self.assertNotIn("git clean", self.script.lower())

    def test_never_runs_inno_or_installs_application(self):
        self.assertIn('scripts\\build_pyinstaller.py', self.script)
        self.assertNotIn('scripts\\build_all.py', self.script)
        self.assertNotIn('scripts\\create_installer.py', self.script)
        self.assertNotIn('ISCC', self.script)
        self.assertNotIn("Start-Process", self.script)
        self.assertNotIn("gh release create", self.script)
        self.assertNotIn("Program Files\\Personal Skin Manager", self.script)
        self.assertNotIn("Remove-Item", self.script)

    def test_uses_independent_ltk_and_cslol_paths(self):
        self.assertIn("PSM_RELEASE_LTK_DIR", self.script)
        self.assertIn("PSM_RELEASE_CSLOL_DIR", self.script)
        self.assertIn("UnsignedLtkDir", self.script)
        self.assertIn("CslolDir", self.script)
        self.assertIn("finally {", self.script)

    def test_frozen_files_are_rehashed_and_singleton(self):
        self.assertIn("Get-ChildItem -LiteralPath $Dist -File -Recurse", self.script)
        self.assertIn("Expected exactly one packaged $Name", self.script)
        self.assertIn("SHA-256 does not match reviewed local QA source", self.script)
        self.assertIn("exe_sha256", self.script)
        self.assertIn("relative_location", self.script)

    def test_public_distribution_status_is_explicit_no_go(self):
        self.assertIn('purpose = "LOCAL PRIVATE FROZEN PARITY TEST ONLY"', self.script)
        self.assertIn("contains_third_party_signed_cslol = $true", self.script)
        self.assertIn("public_redistribution_approved = $false", self.script)
        self.assertIn('frozen_app_visible_skin = "NOT TESTED"', self.script)
        self.assertIn('installed_candidate_visible_skin = "NOT TESTED"', self.script)


if __name__ == "__main__":
    unittest.main()
