#!/usr/bin/env python3
"""Live League connection diagnostics must remain read-only and sanitized."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import diagnose_v105_league_connection as diagnostic


class LiveLcuDiagnosticTests(unittest.TestCase):
    def test_live_endpoint_success_is_read_only_and_no_credentials_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "lockfile"
            lock.write_text("LeagueClient:12345:24680:SECRET-DO-NOT-PRINT:https", encoding="utf-8")
            response = Mock(status_code=200)
            session = Mock()
            session.get.return_value = response
            with patch.object(diagnostic, "_known_lockfile_candidates", return_value=iter([lock])):
                with patch("requests.Session", return_value=session):
                    with patch("psutil.pid_exists", return_value=True):
                        findings = diagnostic.inspect_live_lcu()
            combined = "\n".join(findings)
            self.assertIn("reachable (HTTP 200)", combined)
            self.assertNotIn("SECRET-DO-NOT-PRINT", combined)
            self.assertNotIn("24680", combined)
            args, kwargs = session.get.call_args
            self.assertEqual(args, ("https://127.0.0.1:24680/lol-gameflow/v1/gameflow-phase",))
            self.assertEqual(kwargs["auth"], ("riot", "SECRET-DO-NOT-PRINT"))
            self.assertFalse(kwargs["allow_redirects"])
            self.assertEqual(kwargs["timeout"], 3)
            session.close.assert_called_once()

    def test_unavailable_local_api_does_not_print_secret_or_exception_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "lockfile"
            lock.write_text("LeagueClient:1:24680:SECRET-DO-NOT-PRINT:https", encoding="utf-8")
            session = Mock()
            session.get.side_effect = RuntimeError("secret response SECRET-DO-NOT-PRINT")
            with patch.object(diagnostic, "_known_lockfile_candidates", return_value=iter([lock])):
                with patch("requests.Session", return_value=session):
                    findings = diagnostic.inspect_live_lcu()
            self.assertIn("request failed (RuntimeError)", "\n".join(findings))
            self.assertNotIn("SECRET-DO-NOT-PRINT", "\n".join(findings))
            session.close.assert_called_once()

    def test_malformed_lockfile_does_not_produce_network_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "lockfile"
            lock.write_text("LeagueClient:1:999999:secret:https", encoding="utf-8")
            with patch.object(diagnostic, "_known_lockfile_candidates", return_value=iter([lock])):
                with patch("requests.Session") as session:
                    findings = diagnostic.inspect_live_lcu()
            self.assertIn("lockfile endpoint invalid", "\n".join(findings))
            session.assert_not_called()

    def test_no_running_psm_is_reported_explicitly(self):
        with patch("psutil.process_iter", return_value=[]):
            findings = diagnostic.inspect_psm_process(Path("C:/Program Files/Personal Skin Manager"))
        self.assertIn("PSM running processes: 0", findings)
        self.assertIn("PSM installed process active: no", findings)

    def test_secret_redaction_source_contract(self):
        src = (Path(__file__).resolve().parents[1] /
               "scripts/diagnose_v105_league_connection.py").read_text("utf-8")
        self.assertIn("allow_redirects=False", src)
        self.assertIn("127.0.0.1:", src)
        self.assertNotIn("print(password)", src)
        self.assertNotIn("print(parts)", src)
        self.assertNotIn("print(lockfile.read_text", src)


if __name__ == "__main__":
    unittest.main()
