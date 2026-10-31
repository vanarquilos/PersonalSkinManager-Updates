#!/usr/bin/env python3
"""Regression contract for vcvars64.bat under Program Files (x86).

Previous: cmd /d /c 'call "C:\\Program Files (x86)\\...\\vcvars64.bat"
    >nul && cl ...' lost the inner quotes and never launched MSVC.
The new compiler must execute a short-name .cmd script and call vcvars
*inside the batch*, where the quoted path is interpreted correctly.
"""
from pathlib import Path
import ast
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/build_psm_cslol_stub.py"


class MsvcBatchWithSpacePathContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SOURCE.read_text("utf-8")
        cls.tree = ast.parse(cls.src)

    def test_python_build_source_remains_parseable(self):
        self.assertIsInstance(self.tree, ast.Module)

    def test_uses_short_local_batch_name_not_nested_cmd_statement(self):
        self.assertIn('batch = working / "build_stub.cmd"', self.src)
        self.assertIn('["cmd.exe", "/d", "/c", batch.name]', self.src)
        self.assertIn("cwd=working", self.src)
        self.assertNotIn('["cmd", "/d", "/c", statement]', self.src)
        self.assertNotIn('["cmd", "/d", "/c", export_cmd]', self.src)

    def test_quoted_vcvars_path_is_called_within_batch(self):
        self.assertIn("batch.write_text(", self.src)
        self.assertIn('f\'call "{vcvars}" >nul\\n\'', self.src)
        self.assertIn('"if errorlevel 1 exit /b 10', self.src)
        self.assertIn('"if errorlevel 1 exit /b 11', self.src)
        self.assertIn('"if errorlevel 1 exit /b 12', self.src)
        self.assertIn("cl /nologo /LD", self.src)
        self.assertIn("dumpbin /nologo /exports", self.src)

    def test_real_pe_exports_still_required_and_no_upstream_dll(self):
        self.assertIn("matched != expected_exports", self.src)
        self.assertIn("export_listing", self.src)
        self.assertIn("cslol_msg_hookproc", self.src)
        self.assertIn("PSM_V105_INERT_CSLOL_STUB", self.src)
        self.assertNotIn("Invoke-WebRequest", self.src)

    def test_failed_qa_retry_is_explicit_and_hash_guarded(self):
        qa = (
            ROOT / "scripts/build_v105_rose_style_frozen_private_qa.ps1"
        ).read_text("ascii")
        self.assertIn("[switch]$ResumeFailedStubBuild", qa)
        self.assertIn('Sha $ModDest', qa)
        self.assertIn('Get-ChildItem -LiteralPath $StubDir -Force', qa)
        self.assertIn('Completed or unexpected output exists; refusing resume:', qa)
        self.assertIn('if (-not $ResumeFailedStubBuild) {', qa)
        self.assertIn('Branch must start with qa/v105-rose-', qa)
        self.assertNotIn('Remove-Item', qa)
        self.assertNotIn('git reset', qa.lower())

    def test_failure_preserves_compiler_diagnostic(self):
        self.assertIn("result.stdout", self.src)
        self.assertIn("result.stderr", self.src)
        self.assertIn("MSVC stub build or export dump failed", self.src)


if __name__ == "__main__":
    unittest.main()
