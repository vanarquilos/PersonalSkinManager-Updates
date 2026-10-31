#!/usr/bin/env python3
"""Safety contracts for the Rose-style v1.0.5 installer rebuild.

The Windows installer should behave like an owned app, not a cleanup tool
that removes another product or user-provided patcher bytes.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INNO = ROOT / "installer.iss"


class RoseRebuildInstallerSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = INNO.read_text(encoding="utf-8-sig")

    def test_user_supplied_ltk_is_not_copied_from_distribution(self):
        self.assertIn("Excludes:", self.source)
        for name in ("ltk_patcher_host.exe", "ltk_patcher_dll.dll", "ltk-user-local.json"):
            with self.subTest(name=name):
                self.assertIn(name, self.source)

    def test_installer_ships_nonbinary_ltk_setup_and_documentation(self):
        self.assertIn(
            'Source: "scripts\\import_user_ltk_v105.ps1"; DestDir: "{app}\\tools"',
            self.source,
        )
        self.assertIn(
            'Source: "releases\\v1.0.5\\USER_LTK_SETUP.md"; DestDir: "{app}\\docs"',
            self.source,
        )
        root = Path(__file__).resolve().parents[1]
        setup = (root / "utils/integration/ltk_onboarding.py").read_text("utf-8")
        self.assertIn("tools\\\\import_user_ltk_v105.ps1", setup)
        self.assertIn("docs\\\\USER_LTK_SETUP.md", setup)
        self.assertIn('Path(sys.executable).resolve().parent / "tools"', setup)

    def test_uninstaller_does_not_delete_user_ltk_folder(self):
        self.assertNotIn("[UninstallDelete]", self.source)
        self.assertNotIn("DelTree(ExpandConstant('{app}')", self.source)
        self.assertNotIn('Name: "{app}\\_internal"', self.source)
        self.assertIn("Inno Setup removes only installed, tracked files", self.source)

    def test_uninstall_cannot_touch_independent_rose_runtime(self):
        self.assertNotIn('"/Delete /TN Rose /F"', self.source)
        self.assertNotIn('"{localappdata}\\Rose\\Pengu Loader\\Pengu Loader.exe";', self.source)
        self.assertIn('"/Delete /TN PersonalSkinManager /F"', self.source)

    def test_app_identity_and_version_are_stable(self):
        self.assertIn('#define MyAppName "Personal Skin Manager"', self.source)
        self.assertIn('#define MyAppVersion "1.0.5"', self.source)
        self.assertIn("AppId={{6832ED9B-6ACC-4455-A12F-476A963952E0}}", self.source)


if __name__ == "__main__":
    unittest.main()
