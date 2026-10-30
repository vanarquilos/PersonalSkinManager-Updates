#!/usr/bin/env python3
"""Prevent source or packaged PSM startup from implicitly forcing elevation."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V105LaunchPrivilegeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initialization = (ROOT / "main/core/initialization.py").read_text(encoding="utf-8")
        cls.spec = (ROOT / "PersonalSkinManager.spec").read_text(encoding="utf-8")
        cls.inno = (ROOT / "installer.iss").read_text(encoding="utf-8-sig")
        cls.config = (ROOT / "config.py").read_text(encoding="utf-8")

    def test_core_initialization_does_not_force_admin_relaunch(self):
        self.assertNotIn("ensure_admin_rights()", self.initialization)
        self.assertNotIn("request_admin_elevation()", self.initialization)
        self.assertIn("is_admin()", self.initialization)
        self.assertIn("PSM launch privilege:", self.initialization)

    def test_frozen_executable_and_postinstall_launch_do_not_require_admin(self):
        self.assertIn("uac_admin=False", self.spec)
        self.assertIn("runasoriginaluser", self.inno)
        self.assertNotIn("Verb: runas", self.inno)
        self.assertIn("LTK_ELEVATE_INJECTOR = False", self.config)

    def test_installer_may_still_require_admin_for_installation_only(self):
        self.assertIn("PrivilegesRequired=admin", self.inno)
        self.assertNotIn("uac_admin=True", self.spec)


if __name__ == "__main__":
    unittest.main()
