#!/usr/bin/env python3
"""Regression checks for v1.0.5 distribution provenance and packaging guards."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DistributionCandidateContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = (ROOT / "scripts/build_v105_distribution_candidate.ps1").read_text(encoding="utf-8")
        cls.spec = (ROOT / "PersonalSkinManager.spec").read_text(encoding="utf-8")
        cls.pyinstaller = (ROOT / "scripts/build_pyinstaller.py").read_text(encoding="utf-8")
        cls.inno = (ROOT / "installer.iss").read_text(encoding="utf-8-sig")

    def test_windows_powershell_51_ascii(self):
        self.assertTrue(
            (ROOT / "scripts/build_v105_distribution_candidate.ps1").read_bytes().isascii()
        )

    def test_distribution_patcher_override_only_targets_ltk_pair(self):
        self.assertIn("PSM_RELEASE_LTK_DIR", self.spec)
        self.assertIn("PSM_RELEASE_LTK_DIR", self.pyinstaller)
        self.assertIn("injection/tools/mod-tools.exe", self.spec)
        self.assertIn("release_ltk_root / 'ltk_patcher_host.exe'", self.spec)
        self.assertIn("release_ltk_root / 'ltk_patcher_dll.dll'", self.spec)
        self.assertIn("release_ltk_root = Path('injection/tools')", self.spec)
        self.assertIn("required_runtime_files()", self.pyinstaller)

    def test_verified_vendor_signatures_removed_from_copies_only(self):
        self.assertIn("audit_ltk_v1281_compatibility.py", self.build)
        self.assertIn("Copy-Item -LiteralPath $Source -Destination $Target", self.build)
        self.assertIn("& $SignTool remove /s $Target", self.build)
        self.assertIn("Get-AuthenticodeSignature", self.build)
        self.assertIn('(Get-AuthenticodeSignature -LiteralPath $Target).Status -ne "NotSigned"', self.build)
        self.assertIn("release-unsigned-ltk", self.build)
        self.assertIn("PSM_RELEASE_LTK_DIR", self.build)
        self.assertNotIn("gh release create", self.build)

    def test_installer_is_local_only_and_hash_checked(self):
        self.assertIn("RELEASE CANDIDATE - NOT PUBLISHED", self.build)
        self.assertIn("practice_tool_packaged_skin_render", self.build)
        self.assertIn("swiftplay_packaged_skin_render", self.build)
        self.assertIn("installer checksum mismatch", self.build.lower())
        self.assertIn("original upstream", self.build.lower())
        self.assertIn("1.0.5", self.inno)

    def test_active_working_source_runtime_is_preserved_and_never_packaged(self):
        self.assertIn("_v105_rose_legacy_local_state.json", self.build)
        self.assertIn("preserving it during RC packaging", self.build)
        self.assertIn("Private test state exists, but the active", self.build)
        self.assertIn("release-unsigned-ltk", self.build)
        self.assertIn("Private runtime state or signing material was bundled", self.build)
        self.assertNotIn("Restore the active historical runtime", self.build)


if __name__ == "__main__":
    unittest.main()
