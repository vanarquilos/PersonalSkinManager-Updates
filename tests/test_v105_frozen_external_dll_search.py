#!/usr/bin/env python3
"""Frozen Windows external-child-process DLL search regression tests."""
from pathlib import Path
from unittest import TestCase, mock

from utils.core import external_process


ROOT = Path(__file__).resolve().parents[1]


class ExternalProcessDllSearchTests(TestCase):
    def test_normal_python_launch_has_no_dll_directory_changes(self):
        with (
            mock.patch.object(external_process.sys, "platform", "win32"),
            mock.patch.object(external_process.sys, "frozen", False, create=True),
            mock.patch.object(external_process.subprocess, "Popen", return_value="child") as p,
        ):
            self.assertEqual(external_process.popen_external(["some.exe"], cwd="tools"), "child")
        p.assert_called_once_with(["some.exe"], cwd="tools")

    def test_frozen_windows_restores_default_for_child_and_bundled_after(self):
        values = []
        class Kernel:
            def SetDllDirectoryW(self, value):
                values.append(("dll", value))
                return True

        def spawn(*args, **kwargs):
            values.append(("spawn", args[0]))
            return "child"

        with (
            mock.patch.object(external_process.sys, "platform", "win32"),
            mock.patch.object(external_process.sys, "frozen", True, create=True),
            mock.patch.object(external_process.sys, "_MEIPASS", r"C:\QA\_internal", create=True),
            mock.patch.object(external_process.ctypes, "windll", mock.Mock(kernel32=Kernel()), create=True),
            mock.patch.object(external_process.subprocess, "Popen", side_effect=spawn),
        ):
            self.assertEqual(external_process.popen_external(["mod-tools.exe"]), "child")
        self.assertEqual(
            values,
            [("dll", None), ("spawn", ["mod-tools.exe"]), ("dll", r"C:\QA\_internal")],
        )

    def test_restore_happens_when_spawning_fails(self):
        values = []
        class Kernel:
            def SetDllDirectoryW(self, value):
                values.append(value)
                return True
        with (
            mock.patch.object(external_process.sys, "platform", "win32"),
            mock.patch.object(external_process.sys, "frozen", True, create=True),
            mock.patch.object(external_process.sys, "_MEIPASS", r"C:\QA\_internal", create=True),
            mock.patch.object(external_process.ctypes, "windll", mock.Mock(kernel32=Kernel()), create=True),
            mock.patch.object(external_process.subprocess, "Popen", side_effect=OSError("failed")),
        ):
            with self.assertRaises(OSError):
                external_process.popen_external(["ltk_patcher_host.exe"])
        self.assertEqual(values, [None, r"C:\QA\_internal"])

    def test_missing_meipass_fails_closed(self):
        with (
            mock.patch.object(external_process.sys, "platform", "win32"),
            mock.patch.object(external_process.sys, "frozen", True, create=True),
            mock.patch.object(external_process.sys, "_MEIPASS", None, create=True),
            mock.patch.object(external_process.subprocess, "Popen") as p,
        ):
            with self.assertRaisesRegex(RuntimeError, "Frozen Windows"):
                external_process.popen_external(["some.exe"])
        p.assert_not_called()

    def test_uses_wrapper_for_ltk_and_mod_tools_without_changing_protocol(self):
        host = (ROOT / "injection/overlay/ltk_host.py").read_text("utf-8")
        manager = (ROOT / "injection/overlay/overlay_manager.py").read_text("utf-8")
        self.assertIn("from utils.core.external_process import popen_external", host)
        self.assertIn("proc = popen_external(", host)
        self.assertIn("cwd=str(host_exe.parent)", host)
        self.assertIn("LTK_PATCHER_FLAGS = 4", host)
        self.assertIn("from utils.core.external_process import popen_external", manager)
        self.assertEqual(manager.count("popen_external(cmd,"), 3)
        self.assertNotIn("subprocess.Popen(cmd,", manager)


if __name__ == "__main__":
    import unittest
    unittest.main()
