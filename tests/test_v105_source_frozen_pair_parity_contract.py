#!/usr/bin/env python3
"""No-install diagnostic confirms source vs frozen LTK pairs using hashes only."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "scripts/check_v105_source_frozen_pair_parity.ps1"


class SourceFrozenPairParityContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = FILE.read_text("utf-8")

    def test_script_is_powershell_51_ascii(self):
        self.assertTrue(FILE.read_bytes().isascii())

    def test_all_four_binary_inputs_are_compared_without_copy(self):
        for name in (
            "mod-tools.exe", "cslol-dll.dll", "ltk_patcher_host.exe",
            "ltk_patcher_dll.dll",
        ):
            with self.subTest(name=name):
                self.assertIn(name, self.code)
        self.assertIn("Get-FileHash -LiteralPath", self.code)
        for mutation in ("Copy-Item", "Move-Item", "Remove-Item", "Set-Content",
                         "Start-Process", "Invoke-WebRequest", "SetDllDirectoryW"):
            with self.subTest(mutation=mutation):
                self.assertNotIn(mutation, self.code)

    def test_frozen_default_missing_ltk_is_not_called_a_success(self):
        self.assertIn("SOURCE_ONLY", self.code)
        self.assertIn("DIFFERENT", self.code)
        self.assertIn("IDENTICAL", self.code)
        self.assertIn("default Rose-style builds require separate", self.code)
        self.assertIn("do NOT prove game hooking, skin rendering", self.code)


if __name__ == "__main__":
    unittest.main()
