#!/usr/bin/env python3
"""Only an isolated private worktree may reuse original signed source binaries."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_v105_signed_source_parity_private_qa.ps1"


class SignedSourcePrivateFrozenParityContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text("utf-8")

    def test_windows_powershell_51_compatible_source(self):
        self.assertTrue(SCRIPT.read_bytes().isascii())

    def test_requires_isolated_worktree_and_original_checkout(self):
        for marker in (
            'PathType Leaf', 'qa/v105-signed-parity-',
            'ORIGINAL working source checkout', 'Tracked changes found',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)

    def test_pins_original_signed_pair_and_cslol(self):
        for sha in (
            "25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44",
            "4A009619C6DEA691780B2F20CF17E08DE478A78B3F11CD72759DD71C00AD1C90",
            "23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1",
            "6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74",
        ):
            with self.subTest(sha=sha):
                self.assertIn(sha, self.script)

    def test_builder_uses_only_original_ltk_and_cslol_for_private_freeze(self):
        self.assertIn('$env:PSM_RELEASE_LTK_DIR = $SourceTools', self.script)
        self.assertIn('$env:PSM_RELEASE_CSLOL_DIR = $SourceTools', self.script)
        self.assertIn('scripts\\build_pyinstaller.py', self.script)
        self.assertIn('Get-ChildItem -LiteralPath $Dist -Recurse -File', self.script)

    def test_never_suggests_successful_gameplay_or_publication(self):
        self.assertIn('source_skin_rendering = "UNVERIFIED_ON_CURRENT_LEAGUE"', self.script)
        self.assertIn('frozen_skin_rendering = "NOT TESTED"', self.script)
        self.assertIn('public_distribution_approved = $false', self.script)
        self.assertIn('includes_third_party_signed_binary = $true', self.script)
        self.assertNotIn('gh release create', self.script)
        self.assertNotIn('Start-Process', self.script)
        self.assertNotIn('signtool', self.script)

    def test_original_binary_folder_is_never_written_to(self):
        self.assertIn('Copy-Item -LiteralPath (Join-Path $SourceTools "mod-tools.exe") -Destination $ModDest', self.script)
        self.assertNotIn('Copy-Item -Destination $SourceTools', self.script)
        self.assertNotIn('Remove-Item', self.script)
        self.assertNotIn('git reset', self.script.lower())


if __name__ == "__main__":
    unittest.main()
