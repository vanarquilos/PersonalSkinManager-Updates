#!/usr/bin/env python3
"""PyInstaller external-process DLL-search isolation regression tests."""
import unittest
from unittest.mock import Mock, patch

from utils.system import frozen_subprocess as target


class FrozenSubprocessTests(unittest.TestCase):
    def test_source_python_is_unchanged(self):
        with patch.object(target.sys, "frozen", False, create=True):
            with patch.object(target.subprocess, "Popen", return_value="source-child") as launch:
                result = target.popen_external(["ltk_patcher_host.exe"], cwd="sample")
        self.assertEqual(result, "source-child")
        launch.assert_called_once_with(["ltk_patcher_host.exe"], cwd="sample")

    def _windows_context(self, old_directory):
        observed = []

        def fake_get(size, buffer):
            if size == 0:
                return len(old_directory) + 1
            buffer.value = old_directory
            return len(old_directory)

        def fake_set(directory):
            observed.append(directory)
            return 1

        kernel = Mock()
        kernel.GetDllDirectoryW = fake_get
        kernel.SetDllDirectoryW = fake_set
        return kernel, observed

    def test_frozen_windows_resets_and_restores_dll_lookup(self):
        original = r"C:\test\_internal"
        kernel, observed = self._windows_context(original)
        with patch.object(target.sys, "platform", "win32"):
            with patch.object(target.sys, "frozen", True, create=True):
                with patch.object(target.sys, "_MEIPASS", original, create=True):
                    with patch.object(target.ctypes, "WinDLL", return_value=kernel, create=True):
                        with patch.object(target.subprocess, "Popen", return_value="child") as launch:
                            result = target.popen_external(["host"], stdin=-1)
        self.assertEqual(result, "child")
        self.assertEqual(observed, [None, original])
        launch.assert_called_once_with(["host"], stdin=-1)

    def test_dll_lookup_restored_when_spawn_fails(self):
        original = r"C:\test\_internal"
        kernel, observed = self._windows_context(original)
        with patch.object(target.sys, "platform", "win32"):
            with patch.object(target.sys, "frozen", True, create=True):
                with patch.object(target.sys, "_MEIPASS", original, create=True):
                    with patch.object(target.ctypes, "WinDLL", return_value=kernel, create=True):
                        with patch.object(target.subprocess, "Popen", side_effect=OSError("spawn failed")):
                            with self.assertRaisesRegex(OSError, "spawn failed"):
                                target.popen_external(["host"])
        self.assertEqual(observed, [None, original])

    def test_frozen_without_bundle_directory_fails_closed(self):
        with patch.object(target.sys, "platform", "win32"):
            with patch.object(target.sys, "frozen", True, create=True):
                with patch.object(target.sys, "_MEIPASS", None, create=True):
                    with self.assertRaisesRegex(RuntimeError, "lacks its PyInstaller"):
                        target.popen_external(["host"])

    def test_ltk_adapter_uses_isolated_spawn(self):
        from pathlib import Path
        host = (Path(__file__).resolve().parents[1] / "injection/overlay/ltk_host.py").read_text("utf-8")
        self.assertIn("from utils.system.frozen_subprocess import popen_external", host)
        self.assertIn("proc = popen_external(", host)


if __name__ == "__main__":
    unittest.main()
