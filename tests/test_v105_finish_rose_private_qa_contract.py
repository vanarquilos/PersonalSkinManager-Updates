#!/usr/bin/env python3
"""One-command recovery may touch ONLY the previously failed isolated QA."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/finish_v105_rose_private_qa.ps1"


class FinishRosePrivateQAContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = SCRIPT.read_text(encoding="ascii")

    def test_windows_powershell_ascii_and_original_branch_is_preserved(self):
        self.assertTrue(SCRIPT.read_bytes().isascii())
        self.assertIn("Original branch preserved:", self.s)
        self.assertIn("qa/v105-rose-", self.s)
        for forbidden in ("git checkout", "git reset", "git clean", "Remove-Item", "Invoke-WebRequest"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.s)

    def test_retries_only_reviewed_previous_stub_failure(self):
        for expected in (
            "PSM-v105-Rose-Rebuild-20261031-132306",
            "25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44",
            "Expected empty failed-stub output directory not found.",
            "Partial dist exists without QA report",
            "Status", "merge --ff-only",
            "-ResumeFailedStubBuild",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.s)

    def test_never_calls_skin_success_or_public_release(self):
        self.assertIn("gameplay_skin_rendering", self.s)
        self.assertIn("public_distribution_approved", self.s)
        self.assertIn("No official LTK pair bundled", self.s)
        self.assertNotIn("gh release create", self.s)


if __name__ == "__main__":
    unittest.main()
