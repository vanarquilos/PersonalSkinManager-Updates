#!/usr/bin/env python3
"""Source QA is allowed only with verifiable, inherited unsigned runtime identity."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_v105_elevated_source_pair_qa.ps1"


class ElevatedSourcePairQaContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = RUNNER.read_text("utf-8")

    def test_compatible_with_windows_powershell(self):
        self.assertTrue(RUNNER.read_bytes().isascii())

    def test_requires_admin_before_environment_override(self):
        self.assertIn("[Security.Principal.WindowsBuiltInRole]::Administrator", self.script)
        self.assertIn("Start an Administrator PowerShell FIRST", self.script)
        self.assertLess(self.script.index("Security.Principal.WindowsBuiltInRole]::Administrator"),
                        self.script.index("$env:PSM_LTK_QA_RUNTIME_DIR ="))

    def test_pins_original_and_unsigned_file_identity(self):
        for sha in (
            "23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1",
            "6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74",
            "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9",
            "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29",
        ):
            self.assertIn(sha, self.script)

    def test_probes_real_patcher_selector_from_same_python_source(self):
        self.assertIn('from injection.tools.patcher import (', self.script)
        self.assertIn("check_ltk_patcher(Path(\"injection/tools\"))", self.script)
        self.assertIn('Source QA override inherited: True', self.script)
        self.assertIn("Selected LTK provenance verification failed", self.script)
        self.assertIn('if label != expected:', self.script)
        self.assertIn('if status.host.parent.resolve() !=', self.script)

    def test_runs_python_source_without_self_elevation(self):
        self.assertIn('python ".\\main.py" --dev --debug --logs', self.script)
        self.assertNotIn("Start-Process", self.script)
        self.assertNotIn("ShellExecuteW", self.script)
        self.assertNotIn("runas", self.script)

    def test_does_not_modify_vendor_files_or_publish(self):
        for token in (
            "Copy-Item", "Move-Item", "Remove-Item", "Set-Content", "Out-File",
            "Invoke-WebRequest", "signtool", "git reset", "gh release create",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, self.script)

    def test_restores_inherited_override_after_gameplay(self):
        self.assertIn("finally {", self.script)
        self.assertIn('[Environment]::SetEnvironmentVariable("PSM_LTK_QA_RUNTIME_DIR", $Previous, "Process")', self.script)


if __name__ == "__main__":
    unittest.main()
