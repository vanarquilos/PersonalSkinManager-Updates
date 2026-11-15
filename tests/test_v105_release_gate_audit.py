#!/usr/bin/env python3
"""Release-candidate audit never promotes a source/test build to a public release."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import hashlib
import json

from scripts import report_v105_release_gates as gates


class V105ReleaseAuditTests(TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.qa = Path(temp.name) / "qa"
        self.qa.mkdir()
        self.exe = self.qa / gates.EXE
        self.report = self.qa / gates.REPORT
        self.exe.parent.mkdir(parents=True)
        self.report.parent.mkdir(parents=True)
        self.exe.write_bytes(b"local-private-test")
        self.manifest = {
            "version": "1.0.5",
            "purpose": "ROSE_STYLE_USER_SUPPLIED_LTK_PRIVATE_QA",
            "user_provided_ltk_bundled": False,
            "cslol_source": "PSM_OWNED_INERT_STUB",
            "gameplay_skin_rendering": "NOT_TESTED",
            "public_distribution_approved": False,
            "exe_sha256": hashlib.sha256(self.exe.read_bytes()).hexdigest(),
        }
        self.report.write_text(json.dumps(self.manifest), encoding="utf-8")
        self.league = Path(temp.name) / "League"
        self.ltk = Path(temp.name) / "OfficialPair"
        self.ltk.mkdir()
        (self.ltk / gates.LTK_PATCHER_HOST).write_bytes(b"host")
        (self.ltk / gates.LTK_PATCHER_DLL).write_bytes(b"dll")

    def test_matching_exe_and_new_cutoff_still_cannot_claim_public_release(self):
        with (
            mock.patch.object(gates, "read_game_build", return_value=100),
            mock.patch.object(gates, "read_dll_eol", return_value=101),
        ):
            result = gates.inspect(self.qa, self.league, self.ltk)
        self.assertTrue(result["private_build_verified"])
        self.assertTrue(result["runtime_cutoff_eligible"])
        self.assertEqual(result["public_release"], "NO_GO")
        self.assertFalse(result["checks"]["github_actions_ci"]["passed"])
        self.assertFalse(result["checks"]["visible_skin_in_game"]["passed"])

    def test_expired_dll_is_rejected_even_when_exe_hash_valid(self):
        with (
            mock.patch.object(gates, "read_game_build", return_value=102),
            mock.patch.object(gates, "read_dll_eol", return_value=101),
        ):
            result = gates.inspect(self.qa, self.league, self.ltk)
        self.assertFalse(result["runtime_cutoff_eligible"])
        self.assertEqual(result["public_release"], "NO_GO")

    def test_no_runtime_is_honest_no_go(self):
        with mock.patch.object(gates, "read_game_build", return_value=102):
            result = gates.inspect(self.qa, self.league)
        self.assertFalse(result["checks"]["ltk_host_and_dll"]["passed"])
        self.assertFalse(result["runtime_cutoff_eligible"])

    def test_manifest_cannot_be_public(self):
        self.manifest["public_distribution_approved"] = True
        self.report.write_text(json.dumps(self.manifest), encoding="utf-8")
        with mock.patch.object(gates, "read_game_build", return_value=100):
            result = gates.inspect(self.qa, self.league)
        self.assertFalse(result["checks"]["private_qa_manifest"]["passed"])
        self.assertFalse(result["private_build_verified"])

    def test_exe_hash_change_is_rejected(self):
        self.exe.write_bytes(b"tampered")
        with mock.patch.object(gates, "read_game_build", return_value=100):
            result = gates.inspect(self.qa, self.league)
        self.assertFalse(result["checks"]["frozen_executable"]["passed"])

    def test_unknown_dll_cutoff_cannot_be_considered_compatible(self):
        with (
            mock.patch.object(gates, "read_game_build", return_value=100),
            mock.patch.object(gates, "read_dll_eol", return_value=None),
        ):
            result = gates.inspect(self.qa, self.league, self.ltk)
        self.assertFalse(result["checks"]["ltk_game_build_cutoff"]["passed"])


if __name__ == "__main__":
    import unittest
    unittest.main()
