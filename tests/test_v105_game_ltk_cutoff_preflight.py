#!/usr/bin/env python3
"""Fail-closed private build preflight against actual installed League timestamp."""
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from scripts import verify_v105_game_ltk_cutoff as audit


class GameLtkCutoffPreflightTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        for name in (audit.LTK_PATCHER_HOST, audit.LTK_PATCHER_DLL):
            (self.dir / name).write_bytes(b"test binary fixture")

    def test_all_local_runtime_cutoffs_older_than_current_league_are_rejected(self):
        # Actual latest observed local pair: Oct 28 cutoff; Oct 30 game build.
        game_build = int(datetime(2026, 10, 30, 19, 7, 32, tzinfo=timezone.utc).timestamp())
        cutoff = int(datetime(2026, 10, 28, 23, 6, 41, tzinfo=timezone.utc).timestamp())
        with (
            mock.patch.object(audit, "read_game_build", return_value=game_build),
            mock.patch.object(audit, "read_dll_eol", return_value=cutoff),
        ):
            ok, explanation = audit.compare_game_and_patch(self.dir, self.dir)
        self.assertFalse(ok)
        self.assertIn("expired for installed League", explanation)
        self.assertIn("League PE build:", explanation)
        self.assertIn("LTK DLL cutoff:", explanation)

    def test_unexpired_candidate_passes_only_cutoff_not_gameplay(self):
        with (
            mock.patch.object(audit, "read_game_build", return_value=100),
            mock.patch.object(audit, "read_dll_eol", return_value=101),
        ):
            ok, explanation = audit.compare_game_and_patch(self.dir, self.dir)
        self.assertTrue(ok)
        self.assertIn("NOT proof", explanation)
        self.assertIn("rendering", explanation)

    def test_unknown_game_or_cutoff_fails_closed(self):
        with mock.patch.object(audit, "read_game_build", return_value=None):
            ok, msg = audit.compare_game_and_patch(self.dir, self.dir)
        self.assertFalse(ok)
        self.assertIn("cannot establish", msg)
        with (
            mock.patch.object(audit, "read_game_build", return_value=100),
            mock.patch.object(audit, "read_dll_eol", return_value=None),
        ):
            ok, msg = audit.compare_game_and_patch(self.dir, self.dir)
        self.assertFalse(ok)
        self.assertIn("cannot be verified", msg)

    def test_incomplete_pair_fails_closed_without_executing_binaries(self):
        (self.dir / audit.LTK_PATCHER_DLL).unlink()
        ok, msg = audit.compare_game_and_patch(self.dir, self.dir)
        self.assertFalse(ok)
        self.assertIn("missing", msg)

    def test_private_builds_call_preflight_before_python_builder(self):
        root = Path(__file__).resolve().parents[1]
        for path in (
            "scripts/build_v105_signed_source_parity_private_qa.ps1",
            "scripts/build_v105_current_ltk_frozen_private_qa.ps1",
        ):
            script = (root / path).read_text("utf-8")
            with self.subTest(path=path):
                self.assertIn("verify_v105_game_ltk_cutoff.py", script)
                self.assertLess(
                    script.index("verify_v105_game_ltk_cutoff.py"),
                    script.index("scripts\\build_pyinstaller.py"),
                )
                self.assertIn('Check "League-vs-LTK cutoff preflight"', script)

    def test_public_path_builder_rejects_expired_pair_before_packaging(self):
        script = (
            Path(__file__).resolve().parents[1]
            / "scripts/build_v105_public_path_local_test.ps1"
        ).read_text("utf-8")
        self.assertIn("verify_v105_game_ltk_cutoff.py", script)
        self.assertIn('Check-Exit "League-vs-LTK cutoff preflight"', script)
        self.assertLess(
            script.index("verify_v105_game_ltk_cutoff.py"),
            script.index("scripts\\build_all.py"),
        )
        self.assertNotIn("SOURCE QA now renders skins", script)

    def test_preflight_is_read_only(self):
        source = Path(audit.__file__).read_text("utf-8")
        for forbidden in ("subprocess", "requests", "urllib", "Start-Process",
                          "SetWindowsHookEx", "write_bytes", "write_text", "unlink()"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    import unittest
    unittest.main()
