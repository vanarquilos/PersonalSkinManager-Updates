#!/usr/bin/env python3
"""Offline unit tests for the read-only historical LTK identity auditor."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import audit_ltk_v1281_compatibility as audit


class LegacyLtkCompatibilityAuditTests(unittest.TestCase):
    def test_git_blob_fingerprint_matches_git_format(self):
        self.assertEqual(
            audit.git_blob_sha1(b"hello"),
            "b6fc4c620b67d95f953a5c1c1230aaab5db5a1b0",
        )

    def test_missing_candidate_files_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(audit, "read_game_build", return_value=100):
                with patch.object(audit, "read_dll_eol", return_value=200):
                    report = audit.inspect(root / "missing", root / "game")
            self.assertFalse(report["passes_identity_and_build_timestamp_checks"])
            self.assertEqual(len(report["problems"]), 2)

    def test_synthetic_candidate_only_passes_matching_identity_and_cutoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = root / "candidate"
            candidate.mkdir()
            host = b"fake-host"
            dll = b"fake-dll"
            (candidate / "ltk_patcher_host.exe").write_bytes(host)
            (candidate / "ltk_patcher_dll.dll").write_bytes(dll)
            expected = {
                "ltk_patcher_host.exe": {
                    "bytes": len(host),
                    "git_blob": audit.git_blob_sha1(host),
                },
                "ltk_patcher_dll.dll": {
                    "bytes": len(dll),
                    "git_blob": audit.git_blob_sha1(dll),
                },
            }
            with (
                patch.object(audit, "EXPECTED", expected),
                patch.object(audit, "read_game_build", return_value=100),
                patch.object(audit, "read_dll_eol", return_value=200),
            ):
                report = audit.inspect(candidate, root / "game")
                self.assertTrue(report["passes_identity_and_build_timestamp_checks"])
                self.assertTrue(all(
                    v["official_git_blob_matches"]
                    for v in report["binary_checks"].values()
                ))
                with patch.object(audit, "read_game_build", return_value=300):
                    expired = audit.inspect(candidate, root / "game")
                self.assertFalse(expired["passes_identity_and_build_timestamp_checks"])

    def test_unknown_cutoff_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with (
                patch.object(audit, "read_game_build", return_value=100),
                patch.object(audit, "read_dll_eol", return_value=None),
            ):
                report = audit.inspect(root, root / "game")
            self.assertFalse(report["passes_identity_and_build_timestamp_checks"])
            self.assertIn("Candidate DLL build cutoff unavailable", report["problems"])


if __name__ == "__main__":
    unittest.main()
