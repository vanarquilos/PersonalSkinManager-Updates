#!/usr/bin/env python3
"""Prove unsigned-source QA cannot silently test the signed source pair."""
from pathlib import Path
import unittest
from unittest.mock import patch

from injection.overlay import ltk_host


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/test_v105_isolated_ltk_source.ps1"


class SourceRuntimeProvenanceTests(unittest.TestCase):
    def test_provenance_labels_actual_unsigned_hashes(self):
        host = Path("qa/ltk_patcher_host.exe")
        dll = Path("qa/ltk_patcher_dll.dll")
        expected = ltk_host.LTK_QA_UNSIGNED_SHA256
        with patch.object(ltk_host, "_hash_file", side_effect=lambda p: expected[p.name]):
            self.assertEqual(ltk_host._qa_runtime_identity(host, dll), "unsigned-qa-pair")

    def test_provenance_labels_original_signed_hashes(self):
        host = Path("source/ltk_patcher_host.exe")
        dll = Path("source/ltk_patcher_dll.dll")
        expected = ltk_host.LTK_QA_ORIGINAL_SHA256
        with patch.object(ltk_host, "_hash_file", side_effect=lambda p: expected[p.name]):
            self.assertEqual(ltk_host._qa_runtime_identity(host, dll), "signed-original-pair")

    def test_provenance_labels_unknown_or_unreadable_pair(self):
        host = Path("qa/ltk_patcher_host.exe")
        dll = Path("qa/ltk_patcher_dll.dll")
        with patch.object(ltk_host, "_hash_file", return_value="X" * 64):
            self.assertEqual(ltk_host._qa_runtime_identity(host, dll), "other-pair")
        with patch.object(ltk_host, "_hash_file", side_effect=OSError("unreadable")):
            self.assertEqual(ltk_host._qa_runtime_identity(host, dll), "unreadable")

    def test_source_qa_requires_admin_before_runtime_override(self):
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("WindowsBuiltInRole]::Administrator", script)
        self.assertIn("Reopen PowerShell as Administrator", script)
        self.assertLess(script.index("WindowsBuiltInRole]::Administrator"),
                        script.index("$env:PSM_LTK_QA_RUNTIME_DIR = $Selected"))

    def test_provenance_is_a_local_debug_log_only(self):
        source = (ROOT / "injection/overlay/ltk_host.py").read_text(encoding="utf-8")
        self.assertIn('if "--debug" in sys.argv:', source)
        self.assertIn("QA runtime identity: pair=%s, override_present=%s, parent_frozen=%s", source)
        self.assertNotIn("signing verification bypass", source)


if __name__ == "__main__":
    unittest.main()
