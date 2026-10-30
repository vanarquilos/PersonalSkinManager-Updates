#!/usr/bin/env python3
"""PSM installed League detection must report failures without credential leaks."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LeagueConnectionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (ROOT / "main/__init__.py").read_text("utf-8")
        cls.detector = (ROOT / "injection/game/game_detector.py").read_text("utf-8")
        cls.diagnostic = (ROOT / "scripts/diagnose_v105_league_connection.py").read_text("utf-8")

    def test_fallback_uses_on_disk_installation_without_reading_lockfile_secrets(self):
        self.assertIn("def _detect_via_installation", self.detector)
        self.assertIn("from lcu.core.lockfile import find_lockfile", self.detector)
        self.assertIn('client_dir / "LeagueClient.exe"', self.detector)
        self.assertIn('game_dir / "League of Legends.exe"', self.detector)
        self.assertNotIn("parse_lockfile(", self.detector)

    def test_failure_to_activate_pengu_not_silently_ignored(self):
        self.assertIn("if not pengu_loader.activate_on_start", self.main)
        self.assertIn('"PENGU_ACTIVATION_FAILED"', self.main)

    def test_direct_script_execution_can_import_repository_modules(self):
        self.assertIn("PROJECT_ROOT = Path(__file__).resolve().parents[1]", self.diagnostic)
        self.assertIn('sys.path.insert(0, str(PROJECT_ROOT))', self.diagnostic)

    def test_blocked_websocket_startup_is_visible_and_nonblocking(self):
        self.assertIn("LCU WebSocket still disconnected", self.main)
        self.assertIn("WebSocket worker alive=", self.main)
        self.assertIn('"LCU_WEBSOCKET_WAIT"', self.main)
        self.assertIn("should_stop=lambda: bool(state.stop)", self.main)
        self.assertIn("Stopped while waiting for LCU WebSocket", self.main)
        self.assertIn("client_startup_thread.start()", self.main)
        self.assertNotIn("while not t_ws.connection.is_connected", self.main)

    def test_issue_reporter_accepts_client_integration_failures(self):
        issue_reporter = (ROOT / "utils/core/issue_reporter.py").read_text("utf-8")
        self.assertIn("'PENGU_ACTIVATION_FAILED'", issue_reporter)
        self.assertIn("'LCU_WEBSOCKET_WAIT'", issue_reporter)

    def test_process_diagnostic_distinguishes_stale_running_instances(self):
        self.assertIn("Installed PSM process uptime (minutes)", self.diagnostic)
        self.assertIn("no matched startup log", self.diagnostic)

    def test_report_does_not_dump_sensitive_lcu_data(self):
        self.assertIn("No passwords, lockfile contents, tokens", self.diagnostic)
        self.assertIn("Latest shared PSM log age", self.diagnostic)
        self.assertIn("LCU websocket connected", self.diagnostic)
        self.assertIn("Pengu activation failed", self.diagnostic)
        self.assertNotIn("print(lockfile", self.diagnostic)
        self.assertNotIn("print(password", self.diagnostic)
        self.assertNotIn("getpass", self.diagnostic)


if __name__ == "__main__":
    unittest.main()
