"""Regression tests for LTK's supported, user-consented file-open handoff.

These tests run without Windows, League, LTK binaries, network or game processes.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from utils.integration import ltk_manager_handoff as handoff


class OfficialLtkFileHandoffTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manager = self.root / "LTK Manager" / "ltk-manager.exe"
        self.manager.parent.mkdir()
        self.manager.write_bytes(b"test-only-placeholder")
        self.mod = self.root / "My Custom Skin.fantome"
        self.mod.write_bytes(b"test-only-placeholder")

    def test_detection_finds_localappdata_installed_manager(self):
        actual = handoff.find_manager({"LOCALAPPDATA": str(self.root)})
        self.assertEqual(actual, self.manager.resolve())

    def test_detection_does_not_execute_anything(self):
        with mock.patch.object(handoff.subprocess, "Popen") as popen:
            self.assertEqual(
                handoff.find_manager({"LOCALAPPDATA": str(self.root)}),
                self.manager.resolve(),
            )
            popen.assert_not_called()

    def test_import_refuses_silent_requests(self):
        called = []
        with self.assertRaisesRegex(handoff.ModHandoffError, "confirmation"):
            handoff.request_custom_mod_import(
                self.mod, manager_exe=self.manager, launcher=called.append
            )
        self.assertFalse(called)

    def test_import_uses_argv_not_shell_and_never_claims_rendering(self):
        args = []
        def launch(argv, **kwargs):
            args.append((argv, kwargs))
        with mock.patch.object(handoff.sys, "platform", "win32"):
            result = handoff.request_custom_mod_import(
                self.mod, manager_exe=self.manager,
                confirmed_by_user=True, launcher=launch,
            )
        self.assertEqual(result, "IMPORT_REQUESTED_NOT_VERIFIED")
        self.assertEqual(
            args[0][0], [str(self.manager.resolve()), str(self.mod.resolve())]
        )
        self.assertEqual(args[0][1], {"cwd": str(self.manager.parent.resolve())})

    def test_reject_executable_as_mod(self):
        malicious = self.root / "bad.exe"
        malicious.write_bytes(b"dummy")
        with mock.patch.object(handoff.sys, "platform", "win32"):
            with self.assertRaisesRegex(handoff.ModHandoffError, "Only local"):
                handoff.request_custom_mod_import(
                    malicious, confirmed_by_user=True,
                    manager_exe=self.manager, launcher=lambda *a, **kw: None,
                )

    def test_reject_missing_mod(self):
        with mock.patch.object(handoff.sys, "platform", "win32"):
            with self.assertRaisesRegex(handoff.ModHandoffError, "does not exist"):
                handoff.request_custom_mod_import(
                    self.root / "missing.modpkg", confirmed_by_user=True,
                    manager_exe=self.manager, launcher=lambda *a, **kw: None,
                )

    def test_accepts_modpkg(self):
        modpkg = self.root / "test.modpkg"
        modpkg.write_bytes(b"dummy")
        called = []
        def launch(argv, **kw):
            called.append(argv)
        with mock.patch.object(handoff.sys, "platform", "win32"):
            status = handoff.request_custom_mod_import(
                modpkg, confirmed_by_user=True,
                manager_exe=self.manager, launcher=launch,
            )
        self.assertEqual(status, "IMPORT_REQUESTED_NOT_VERIFIED")
        self.assertEqual(len(called), 1)

    def test_open_manager_requires_consent(self):
        called = []
        with self.assertRaises(handoff.ModHandoffError):
            handoff.request_open_manager(
                manager_exe=self.manager, launcher=called.append
            )
        self.assertFalse(called)

    def test_open_manager_launches_only_manager_not_patcher(self):
        called = []
        def launch(argv, **kw):
            called.append(argv)
        with mock.patch.object(handoff.sys, "platform", "win32"):
            status = handoff.request_open_manager(
                confirmed_by_user=True, manager_exe=self.manager,
                launcher=launch,
            )
        self.assertEqual(status, "MANAGER_OPEN_REQUESTED_NOT_VERIFIED")
        self.assertEqual(called, [[str(self.manager.resolve())]])

    def test_reject_manager_executable_name_mismatch(self):
        impostor = self.root / "not-manager.exe"
        impostor.write_bytes(b"placeholder")
        with mock.patch.object(handoff.sys, "platform", "win32"):
            with self.assertRaisesRegex(handoff.ModHandoffError, "executable not found"):
                handoff.request_open_manager(
                    confirmed_by_user=True, manager_exe=impostor,
                    launcher=lambda *a, **kw: None,
                )

    def test_no_runtime_injection_or_host_verification_bypass(self):
        code = (Path(__file__).resolve().parents[1] /
                "utils/integration/ltk_manager_handoff.py").read_text("utf-8")
        self.assertIn("IMPORT_REQUESTED_NOT_VERIFIED", code)
        self.assertNotIn("ltk_patcher_host.exe", code)
        self.assertNotIn("ltk_patcher_dll.dll", code)
        self.assertNotIn("SetWindowsHookEx", code)
