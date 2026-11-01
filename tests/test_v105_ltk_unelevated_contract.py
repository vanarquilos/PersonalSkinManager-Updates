#!/usr/bin/env python3
"""Official delivered LTK runtime executes from normal-user PSM, never admin."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ModernLtkUnelevatedContracts(unittest.TestCase):
    def test_frozen_exe_does_not_force_elevation(self):
        spec = (ROOT / "PersonalSkinManager.spec").read_text("utf-8")
        self.assertIn("uac_admin=False", spec)
        self.assertNotIn("uac_admin=True", spec)

    def test_source_start_does_not_relaunch_self_as_administrator(self):
        init = (ROOT / "main/core/initialization.py").read_text("utf-8")
        self.assertNotIn("ensure_admin_rights()", init)
        self.assertIn("if is_admin():", init)
        self.assertIn("require normal", init)

    def test_ltk_child_stops_before_launch_under_admin(self):
        code = (ROOT / "injection/overlay/ltk_host.py").read_text("utf-8")
        start = code.index("def start_ltk_patcher_host(")
        guard = code.index('if sys.platform == "win32" and is_admin():', start)
        launch = code.index("proc = popen_external(", start)
        self.assertLess(guard, launch)
        self.assertIn('"LTK_ADMIN_CONTEXT"', code)
        self.assertIn("not Run as administrator", code)

    def test_autostart_does_not_elevate_app_implicitly(self):
        admin = (ROOT / "utils/system/admin_utils.py").read_text("utf-8")
        self.assertIn("'/RL', 'LIMITED'", admin)
        self.assertNotIn("'/RL', 'HIGHEST'", admin)


if __name__ == "__main__":
    unittest.main()
