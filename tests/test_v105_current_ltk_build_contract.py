#!/usr/bin/env python3
"""Static safety invariants for current LTK private v1.0.5 packaging."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "scripts/prepare_v105_current_ltk_private_qa.ps1"
FREEZE = ROOT / "scripts/build_v105_current_ltk_frozen_private_qa.ps1"
HOST = ROOT / "injection/overlay/ltk_host.py"
PATCHER = ROOT / "injection/tools/patcher.py"


class CurrentLtkPrivateBuildContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepare = PREPARE.read_text("utf-8")
        cls.freeze = FREEZE.read_text("utf-8")
        cls.host = HOST.read_text("utf-8")
        cls.patcher = PATCHER.read_text("utf-8")

    def test_powershell_51_ascii(self):
        self.assertTrue(PREPARE.read_bytes().isascii())
        self.assertTrue(FREEZE.read_bytes().isascii())

    def test_current_qa_manifest_has_protection_fields(self):
        for text in ("schema = 1", 'runtime_origin = "official-bundled"',
                     "host_protocol = 3", "public_distribution_approved = $false"):
            with self.subTest(text=text):
                self.assertIn(text, self.prepare)
        self.assertIn("PSM_V105_PRIVATE_QA_ONLY", self.prepare)
        self.assertIn('runtime_origin": "official-bundled"', self.patcher)

    def test_vendor_enforcement_is_not_disabled(self):
        self.assertIn("LTK_PATCHER_FLAGS = 0", self.host)
        self.assertIn("LTK_MODERN_QA_FLAGS = 0", self.host)
        self.assertIn('config flags {selected_flags}', self.host)
        self.assertIn("vendor default flags", self.host)
        self.assertNotIn("LTK_PATCHER_FLAGS = 4", self.host)

    def test_private_builder_rejects_published_and_old_pairs(self):
        for text in ("qa/v105-current-ltk-", "public_distribution_approved",
                     "OldBadHost", "OldBadDll", "current-ltk-frozen-private-qa.json",
                     "NOT TESTED", "do NOT upload"):
            with self.subTest(text=text):
                self.assertIn(text, self.freeze)

    def test_builder_confines_vendor_binaries_to_new_worktree(self):
        self.assertIn('Join-Path $Root ".git"', self.freeze)
        self.assertIn("-PathType Leaf", self.freeze)
        self.assertIn('Copy-Item -LiteralPath $ModToolsFile -Destination $Dest', self.freeze)
        self.assertIn('PSM_RELEASE_LTK_DIR', self.freeze)
        self.assertIn('PSM_RELEASE_CSLOL_DIR', self.freeze)
        self.assertNotIn("Copy-Item -LiteralPath $Files[", self.freeze)
        self.assertNotIn("gh release create", self.freeze)
        self.assertNotIn("scripts\\build_all.py", self.freeze)

    def test_hashes_signed_source_not_publicly_repackaged(self):
        self.assertIn("Get-AuthenticodeSignature", self.prepare)
        self.assertIn("Get-FileHash", self.prepare)
        self.assertIn("Get-FileHash", self.freeze)
        self.assertIn("frozen private qa build complete", self.freeze.lower())


if __name__ == "__main__":
    unittest.main()
