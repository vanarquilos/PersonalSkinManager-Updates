#!/usr/bin/env python3
"""Guards for the opt-in and reversible legacy LTK source-QA workflow."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "scripts" / "use_rose_legacy_runtime_local.ps1"
RELEASE = ROOT / "scripts" / "prepare_v1_0_5_test.ps1"
STAGING = ROOT / "scripts" / "stage_ltk_v105_test.ps1"


class LegacyRuntimeLocalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = RUNTIME.read_text(encoding="utf-8")
        cls.release = RELEASE.read_text(encoding="utf-8")
        cls.staging = STAGING.read_text(encoding="utf-8")

    def test_powershell_51_safe_ascii_source(self):
        self.assertTrue(RUNTIME.read_bytes().isascii())

    def test_activation_requires_official_identity_and_current_league_build(self):
        self.assertIn("audit_ltk_v1281_compatibility.py", self.script)
        self.assertIn("if ($LASTEXITCODE -ne 0)", self.script)
        self.assertIn('Join-Path $Root "installer\\candidates\\v1.0.5\\audit-only-ltk-v1.28.1"', self.script)
        self.assertIn("Close PSM, League gameplay", self.script)
        self.assertIn('source_tag = "v1.28.1"', self.script)
        self.assertNotIn("Invoke-WebRequest", self.script)

    def test_rollback_record_written_before_activation(self):
        self.assertIn('ValidateSet("Activate", "Restore", "Status")', self.script)
        self.assertIn("original_sha256 = $Hashes", self.script)
        self.assertIn("PRIVATE_SOURCE_QA_ONLY", self.script)
        record = self.script.index("$State | ConvertTo-Json -Depth 5 | Set-Content")
        changed = self.script.index("Copy-Item -LiteralPath (Join-Path $Candidate $Name)")
        self.assertLess(record, changed)
        self.assertIn('if ($Action -eq "Restore")', self.script)
        self.assertIn("Restored the original local LTK host/DLL pair.", self.script)
        self.assertIn('if ($Action -eq "Status")', self.script)
        self.assertIn("Active PSM host/DLL pair matches", self.script)
        self.assertIn("already active; keeping your working setup", self.script)

    def test_release_and_staging_block_active_legacy_session(self):
        key = "_v105_rose_legacy_local_state.json"
        self.assertIn(key, self.script)
        self.assertIn(key, self.release)
        self.assertIn(key, self.staging)
        self.assertIn("use build_v105_distribution_candidate.ps1", self.release)
        self.assertIn("Do not overwrite it with v1.30.1 staging", self.staging)

    def test_no_binary_modification_or_verification_override(self):
        self.assertNotIn("Set-AuthenticodeSignature", self.script)
        self.assertNotIn("signtool", self.script)
        self.assertNotIn("patch bytes", self.script.lower())
        self.assertIn("No DLL modification or impersonation", self.script)


if __name__ == "__main__":
    unittest.main()
