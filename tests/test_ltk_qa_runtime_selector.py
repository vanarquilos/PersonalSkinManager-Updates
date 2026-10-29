#!/usr/bin/env python3
"""Source-only A/B LTK selection. Never permits unreviewed runtime files."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from injection.tools import patcher


class LtkQaRuntimeSelectorTests(unittest.TestCase):
    def test_default_uses_the_original_tools_directory(self):
        with patch.dict(os.environ, {}, clear=True):
            selected, errors = patcher._resolve_qa_runtime(Path("injection/tools"))
        self.assertEqual(selected, Path("injection/tools"))
        self.assertEqual(errors, [])

    def test_absolute_verified_pair_selected_without_replacing_originals(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for name in (patcher.LTK_PATCHER_HOST, patcher.LTK_PATCHER_DLL):
                (folder / name).write_bytes(name.encode("ascii"))
            values = {name: patcher._hash_file(folder / name) for name in
                      (patcher.LTK_PATCHER_HOST, patcher.LTK_PATCHER_DLL)}
            with patch.dict(os.environ, {patcher.LTK_QA_RUNTIME_DIR_ENV: temporary}):
                with patch.object(patcher, "LTK_QA_ORIGINAL_SHA256", values):
                    selected, errors = patcher._resolve_qa_runtime(Path("source/tools"))
                    status = patcher.check_ltk_patcher(Path("source/tools"))
            self.assertEqual(selected, folder)
            self.assertEqual(errors, [])
            self.assertEqual(status.host, folder / patcher.LTK_PATCHER_HOST)
            self.assertEqual(status.dll, folder / patcher.LTK_PATCHER_DLL)
            self.assertEqual(status.missing, [])

    def test_mismatched_pair_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for name in (patcher.LTK_PATCHER_HOST, patcher.LTK_PATCHER_DLL):
                (folder / name).write_bytes(b"unknown binary")
            with patch.dict(os.environ, {patcher.LTK_QA_RUNTIME_DIR_ENV: temporary}):
                status = patcher.check_ltk_patcher(Path("source/tools"))
            self.assertIn("reviewed pair", status.missing[0])

    def test_incomplete_pair_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / patcher.LTK_PATCHER_HOST).write_bytes(b"placeholder")
            with patch.dict(os.environ, {patcher.LTK_QA_RUNTIME_DIR_ENV: temporary}):
                status = patcher.check_ltk_patcher(Path("source/tools"))
            self.assertIn("incomplete", status.missing[0])

    def test_relative_override_fails_closed(self):
        with patch.dict(os.environ, {patcher.LTK_QA_RUNTIME_DIR_ENV: "relative/ltk"}):
            status = patcher.check_ltk_patcher(Path("source/tools"))
        self.assertIn("invalid local QA runtime", status.missing[0])

    def test_host_runs_from_selected_ltk_directory(self):
        root = Path(__file__).resolve().parents[1]
        host_source = (root / "injection/overlay/ltk_host.py").read_text(encoding="utf-8")
        self.assertIn("cwd=str(host_exe.parent)", host_source)
        self.assertNotIn("cwd=str(tools_dir)", host_source)


if __name__ == "__main__":
    unittest.main()
