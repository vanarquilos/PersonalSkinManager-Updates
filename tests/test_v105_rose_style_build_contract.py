#!/usr/bin/env python3
"""Rose-style frozen QA must never ship official user-provided LTK binaries."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_v105_rose_style_frozen_private_qa.ps1"
STUB = ROOT / "native/cslol_stub/psm_cslol_stub.c"
COMPILE = ROOT / "scripts/build_psm_cslol_stub.py"
SPEC = ROOT / "PersonalSkinManager.spec"
PY_BUILD = ROOT / "scripts/build_pyinstaller.py"
INNO = ROOT / "installer.iss"


class RoseStyleBuildContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = BUILD.read_text("utf-8")
        cls.stub = STUB.read_text("utf-8")
        cls.compile = COMPILE.read_text("utf-8")
        cls.spec = SPEC.read_text("utf-8")
        cls.py_build = PY_BUILD.read_text("utf-8")
        cls.inno = INNO.read_text("utf-8-sig")

    def test_powershell_is_ascii(self):
        self.assertTrue(BUILD.read_bytes().isascii())

    def test_default_spec_does_not_bundle_ltk(self):
        self.assertIn("release_ltk_root = None", self.spec)
        self.assertIn("if release_ltk_root is not None:", self.spec)
        self.assertIn("if supplied_ltk:", self.py_build)
        self.assertIn("ltk_patcher_host.exe", self.spec)

    def test_inno_excludes_user_owned_ltk_files_on_upgrade(self):
        for name in ("ltk_patcher_host.exe", "ltk_patcher_dll.dll", "ltk-user-local.json"):
            self.assertIn(name, self.inno)
        self.assertIn("Excludes:", self.inno)

    def test_rose_style_qa_build_never_bundles_ltk(self):
        for term in (
            "qa/v105-rose-", "user_provided_ltk_bundled = $false",
            "PSM_RELEASE_LTK_DIR", "PSM_RELEASE_CSLOL_DIR",
            "ltk_patcher_host.exe", "ltk_patcher_dll.dll",
            "public_distribution_approved = $false",
        ):
            self.assertIn(term, self.build)
        self.assertIn('SetEnvironmentVariable("PSM_RELEASE_LTK_DIR", $null, "Process")', self.build)
        self.assertNotIn("build_all.py", self.build)
        self.assertNotIn("gh release create", self.build)

    def test_owned_stub_has_only_fail_closed_exports(self):
        self.assertIn("non-functional compatibility exports", self.stub)
        self.assertIn("cslol_init(void)", self.stub)
        self.assertIn("cslol_hook(", self.stub)
        self.assertIn("return psm_unsupported;", self.stub)
        self.assertIn("return NULL;", self.stub)
        self.assertNotIn("SetWindowsHookEx", self.stub)
        self.assertNotIn("DisableAntiCheat", self.stub)

    def test_owned_stub_matches_all_eight_original_cslol_exports(self):
        # Verified against the upload cslol-dll(1).dll (SHA-256
        # 4A009619C6DEA691780B2F20CF17E08DE478A78B3F11CD72759DD71C00AD1C90)
        # and LeagueToolkit/cslol-manager's public cslol-api.h.
        for export in (
            "cslol_find", "cslol_hook", "cslol_init", "cslol_log_pull",
            "cslol_msg_hookproc", "cslol_set_config", "cslol_set_flags",
            "cslol_set_log_level",
        ):
            with self.subTest(export=export):
                self.assertIn(export + "(", self.stub)
        self.assertIn("PSM_EXPORT intptr_t cslol_msg_hookproc(", self.stub)
        self.assertIn("PSM_EXPORT const char* cslol_set_flags(unsigned int flags)", self.stub)
        self.assertNotIn("unsigned long long flags", self.stub)
        self.assertIn("return 0;", self.stub)

    def test_stub_compilation_checks_real_pe_export_table(self):
        self.assertIn("dumpbin /nologo /exports", self.compile)
        self.assertIn("MSVC dumpbin export validation did not run", self.compile)
        self.assertIn("PSM stub ABI mismatch", self.compile)
        self.assertIn("cslol_msg_hookproc", self.compile)
        self.assertIn('r"^\\s*\\d+\\s+', self.compile)
        self.assertNotIn('r"^\\\\s*', self.compile)

    def test_stub_build_stays_in_isolated_directory(self):
        self.assertIn("PSM_LOCAL_STUB_OUTPUT_DIR", self.compile)
        self.assertIn("EMPTY isolated output directory", self.compile)
        self.assertIn("PSM_V105_INERT_CSLOL_STUB", self.compile)
        self.assertIn("public_distribution_approved", self.compile)
        self.assertNotIn("github.com/LeagueToolkit", self.compile)


if __name__ == "__main__":
    unittest.main()
