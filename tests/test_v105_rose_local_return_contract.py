#!/usr/bin/env python3
"""Guard the last source-tested Rose local rollback workflow."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "return_to_rose_local_v105.ps1"
LEGACY = ROOT / "scripts" / "use_rose_legacy_runtime_local.ps1"


class RoseLocalReturnContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = WRAPPER.read_text(encoding="utf-8")
        cls.legacy = LEGACY.read_text(encoding="utf-8")

    def test_wrapper_is_portable_ascii_ps51(self):
        self.assertTrue(WRAPPER.read_bytes().isascii())

    def test_scoped_to_explicit_local_rollback_branch(self):
        self.assertIn('fix/v1.0.5-rose-local-rollback', self.script)
        self.assertIn('79150ea9fafd99f4665d2d196435301b12345205', self.script)
        self.assertIn('ValidateSet("Prepare", "Status", "Run")', self.script)

    def test_working_signed_pair_is_preserved(self):
        self.assertIn('if ($SignedAlready)', self.script)
        self.assertIn('keeping files unchanged', self.script)
        self.assertIn('Get-PairStatus $Source', self.script)
        self.assertIn('Get-PairStatus $Pinned', self.script)
        self.assertIn('Get-AuthenticodeSignature', self.script)
        self.assertIn('23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1', self.script)
        self.assertIn('6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74', self.script)

    def test_mutations_delegated_to_original_backup_and_restore_workflow(self):
        self.assertIn('-Action Activate -LeagueGameDir $LeagueGameDir', self.script)
        self.assertIn('PRIVATE_SOURCE_QA_ONLY', self.legacy)
        self.assertIn('original_sha256 = $Hashes', self.legacy)
        self.assertIn('Backup retained under:', self.legacy)
        self.assertNotIn('Copy-Item', self.script)
        self.assertNotIn('Remove-Item', self.script)
        self.assertNotIn('signtool', self.script)

    def test_source_only_no_distribution(self):
        self.assertIn('run_live_qa.ps1', self.script)
        self.assertIn('PRIVATE LOCAL SOURCE QA ONLY', self.script)
        self.assertNotIn('publish_v105_prerelease.ps1', self.script)
        self.assertNotIn('build_v105_distribution_candidate.ps1', self.script)
        self.assertNotIn('Start-Process -FilePath $Installer', self.script)

    def test_no_forced_kill_of_processes(self):
        self.assertIn('Get-Process', self.script)
        self.assertNotIn('Stop-Process', self.script)
        self.assertIn('Close installed/source PSM', self.script)


if __name__ == "__main__":
    unittest.main()
