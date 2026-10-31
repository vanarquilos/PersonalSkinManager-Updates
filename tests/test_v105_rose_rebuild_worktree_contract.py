#!/usr/bin/env python3
"""A rollback checkout must never be reset to prepare new PSM v1.0.5 QA."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/create_v105_rose_rebuild_worktree.ps1"


class RoseRebuildWorktreeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_windows_powershell_51_compatibility(self):
        self.assertTrue(SCRIPT.read_bytes().isascii())

    def test_rollback_branch_is_not_checked_out_or_deleted(self):
        self.assertIn("Preserving original branch:", self.source)
        self.assertIn("rebuild/v1.0.5-rose-compatible", self.source)
        self.assertIn("qa/v105-rose-$Stamp", self.source)
        self.assertIn("git -C $Original worktree add -b", self.source)
        for banned in ("git checkout", "git switch", "git reset", "git clean",
                       "Remove-Item", "Move-Item", "git worktree remove"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, self.source)

    def test_explicit_remote_tracking_ref_fetched(self):
        self.assertIn('"+refs/heads/" + $TargetRef + ":refs/remotes/origin/" + $TargetRef', self.source)
        self.assertIn('"origin/" + $TargetRef', self.source)
        self.assertIn('CheckExit "Create isolated QA worktree"', self.source)

    def test_default_build_is_private_and_no_external_ltk_download(self):
        self.assertIn("build_v105_rose_style_frozen_private_qa.ps1", self.source)
        self.assertIn("-ModToolsFile $ModTools", self.source)
        self.assertIn("[switch]$PrepareOnly", self.source)
        self.assertIn("does NOT bundle LTK", self.source)
        for forbidden in ("Invoke-WebRequest", "Start-BitsTransfer",
                          "ltkp-qa-stage-", "gh release create"):
            self.assertNotIn(forbidden, self.source)


if __name__ == "__main__":
    unittest.main()
