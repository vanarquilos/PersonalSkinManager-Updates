#!/usr/bin/env python3
"""Regression tests for unsupported runtime reporting on current League builds."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from injection.tools.patcher import LtkPatcherStatus
from injection.tools.tools_manager import ToolsManager
from utils.core import issue_reporter


class RuntimeFailureReportingTests(unittest.TestCase):
    def test_runtime_failure_codes_are_written_to_diagnostics(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "rose_diagnostics.txt"
            issue_reporter._LAST.clear()
            with patch.object(issue_reporter, "_issues_path", return_value=target):
                issue_reporter.report_issue(
                    "LTK_PATCHER_EOL",
                    "error",
                    "PSM cannot apply skins: unsupported game build.",
                    hint="Obtain a compatible trusted runtime.",
                )
                issue_reporter.report_issue(
                    "INJECTION_RUNTIME_UNAVAILABLE",
                    "error",
                    "Injection unavailable.",
                )
            text = target.read_text(encoding="utf-8")
            self.assertIn("unsupported game build", text)
            self.assertIn("compatible trusted runtime", text)
            self.assertIn("Injection unavailable", text)

    def test_known_expired_runtime_is_rejected_before_injection(self):
        with tempfile.TemporaryDirectory() as d:
            tools = Path(d)
            for n in ("mod-tools.exe", "ltk_patcher_host.exe", "ltk_patcher_dll.dll"):
                (tools / n).write_bytes(b"x")
            status = LtkPatcherStatus(
                host=tools / "ltk_patcher_host.exe",
                dll=tools / "ltk_patcher_dll.dll",
                missing=[],
                eol=1_000_000,
            )
            with (
                patch("injection.tools.tools_manager.check_ltk_patcher", return_value=status),
                patch.object(status, "expired_for", return_value=True) as check,
                patch("injection.tools.tools_manager.read_game_build", return_value=1_000_001),
                patch("injection.tools.tools_manager.report_issue") as report,
            ):
                self.assertFalse(ToolsManager(tools).check_tools_available(tools))
            check.assert_called_once_with(tools)
            self.assertEqual(report.call_args.args[0], "LTK_PATCHER_EOL")

    def test_unknown_dll_cutoff_never_claims_runtime_ready(self):
        with tempfile.TemporaryDirectory() as d:
            tools = Path(d)
            for name in ("mod-tools.exe", "ltk_patcher_host.exe", "ltk_patcher_dll.dll"):
                (tools / name).write_bytes(b"x")
            status = LtkPatcherStatus(
                host=tools / "ltk_patcher_host.exe",
                dll=tools / "ltk_patcher_dll.dll",
                missing=[],
                eol=None,
            )
            with (
                patch("injection.tools.tools_manager.check_ltk_patcher", return_value=status),
                patch("injection.tools.tools_manager.report_issue") as reported,
            ):
                manager = ToolsManager(tools)
                self.assertFalse(manager.check_tools_available(tools))
            self.assertEqual(manager.last_failure_code, "LTK_PATCHER_CUTOFF_UNKNOWN")
            self.assertEqual(reported.call_args.args[0], "LTK_PATCHER_CUTOFF_UNKNOWN")

    def test_unreadable_league_build_is_not_a_false_ready_state(self):
        with tempfile.TemporaryDirectory() as d:
            tools = Path(d)
            for name in ("mod-tools.exe", "ltk_patcher_host.exe", "ltk_patcher_dll.dll"):
                (tools / name).write_bytes(b"x")
            status = LtkPatcherStatus(
                host=tools / "ltk_patcher_host.exe",
                dll=tools / "ltk_patcher_dll.dll",
                missing=[],
                eol=1_000_000,
            )
            with (
                patch("injection.tools.tools_manager.check_ltk_patcher", return_value=status),
                patch("injection.tools.tools_manager.read_game_build", return_value=None),
                patch("injection.tools.tools_manager.report_issue") as reported,
            ):
                manager = ToolsManager(tools)
                self.assertFalse(manager.check_tools_available(tools))
            self.assertEqual(manager.last_failure_code, "LEAGUE_BUILD_UNREADABLE")
            self.assertEqual(reported.call_args.args[0], "LEAGUE_BUILD_UNREADABLE")

    def test_known_cutoff_only_logs_preliminary_validation_not_skin_success(self):
        with tempfile.TemporaryDirectory() as d:
            tools = Path(d)
            for name in ("mod-tools.exe", "ltk_patcher_host.exe", "ltk_patcher_dll.dll"):
                (tools / name).write_bytes(b"x")
            status = LtkPatcherStatus(
                host=tools / "ltk_patcher_host.exe",
                dll=tools / "ltk_patcher_dll.dll",
                missing=[],
                eol=1_000_001,
            )
            with (
                patch("injection.tools.tools_manager.check_ltk_patcher", return_value=status),
                patch("injection.tools.tools_manager.read_game_build", return_value=1_000_000),
                patch.object(status, "expired_for", return_value=False),
                patch("injection.tools.tools_manager.log") as logger,
            ):
                self.assertTrue(ToolsManager(tools).check_tools_available(tools))
            messages = " ".join(str(call.args) for call in logger.info.call_args_list)
            self.assertIn("UNVERIFIED", messages)
            self.assertNotIn("skin applied successfully", messages.lower())


if __name__ == "__main__":
    unittest.main()
