#!/usr/bin/env python3
"""Rose 1.5 vs PSM 1.0.5 runtime failure regression coverage.

Testing actual diagnostic file visibility does not exercise Riot/League
processes, bypass host verification, or load upstream DLLs.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, mock

from injection.overlay.ltk_host import LtkHostResult, _parse_stdout
from utils.core import issue_reporter
from utils.integration.ltk_onboarding import explain_ltk_runtime_problem


class CurrentRoseRuntimeDiagnostics(TestCase):
    def setUp(self):
        self.dir = TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.report = Path(self.dir.name) / "rose_diagnostics.txt"
        issue_reporter._LAST.clear()

    def test_current_host_verification_refusal_is_visible_and_sanitized(self):
        result = LtkHostResult()
        with mock.patch.object(issue_reporter, "_issues_path", return_value=self.report):
            _parse_stdout(
                "dll 5.0 100 200 ERROR ltk_patcher_dll::verify: "
                "host verification failed, refusing overlay: "
                "[VRF00000007] (1234,ltk-manager.exe)",
                result,
            )
        self.assertIn("host verification", result.failure.lower())
        text = self.report.read_text("utf-8")
        self.assertIn("host verification", text.lower())
        self.assertIn("authorized integration", text)
        self.assertNotIn("VRF00000007", text)
        self.assertNotIn("1234", text)

    def test_important_runtime_codes_are_not_silently_discarded(self):
        codes = {
            "LTK_ADMIN_CONTEXT": "Cannot start LTK while PSM is elevated",
            "LTK_NO_WAD_REDIRECTION": "No skin WAD was served to the game",
            "LTK_PATCHER_CUTOFF_UNKNOWN": "Unknown patcher build cutoff",
            "LEAGUE_BUILD_UNREADABLE": "League executable build unreadable",
            "LEAGUE_DIR_NOT_FOUND": "League game directory missing",
        }
        with mock.patch.object(issue_reporter, "_issues_path", return_value=self.report):
            for key, message in codes.items():
                issue_reporter.report_issue(key, "error", message, hint="Review source diagnostics")
        text = self.report.read_text("utf-8")
        for message in codes.values():
            self.assertIn(message, text)

    def test_onboarding_does_not_claim_a_copied_dll_is_rose_compatible(self):
        status = SimpleNamespace(missing=["LTK DLL absent"], eol=None)
        with mock.patch("utils.integration.ltk_onboarding.check_ltk_patcher", return_value=status):
            message = explain_ltk_runtime_problem(Path(self.dir.name))
        self.assertIn("Current Alban1911/Rose uses installed LTK Manager", message)
        self.assertIn("NOT a confirmed fix", message)

    def test_onboarding_rejects_unknown_cutoff(self):
        status = SimpleNamespace(missing=[], eol=None)
        with mock.patch("utils.integration.ltk_onboarding.check_ltk_patcher", return_value=status):
            message = explain_ltk_runtime_problem(Path(self.dir.name))
        self.assertIn("cannot verify", message)
        self.assertIn("integrity checks", message)

    def test_no_diagnostics_claim_success_on_direct_host_verification_refusal(self):
        code = (Path(__file__).resolve().parents[1] / "injection/tools/tools_manager.py").read_text("utf-8")
        self.assertIn('self.last_failure_code = "LTK_PATCHER_CUTOFF_UNKNOWN"', code)
        self.assertIn('self.last_failure_code = "LEAGUE_BUILD_UNREADABLE"', code)
        self.assertIn("visible skin rendering remain UNVERIFIED", code)


if __name__ == "__main__":
    import unittest
    unittest.main()
