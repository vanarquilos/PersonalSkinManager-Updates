#!/usr/bin/env python3
"""League installation discovery must work when process EXE access is denied."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from injection.game.game_detector import GameDetector


class LeaguePathDetectionTests(unittest.TestCase):
    def make_install(self, root: Path):
        client_dir = root / "League of Legends"
        game_dir = client_dir / "Game"
        game_dir.mkdir(parents=True)
        (client_dir / "LeagueClient.exe").write_bytes(b"fixture")
        (game_dir / "League of Legends.exe").write_bytes(b"fixture")
        return game_dir, client_dir

    def test_lockfile_directory_fallback_requires_both_real_exe_files(self):
        with tempfile.TemporaryDirectory() as temp:
            game, client = self.make_install(Path(temp))
            (client / "lockfile").write_text("opaque; do not parse", encoding="utf-8")
            config = Mock()
            config.load_league_path.return_value = None
            config.load_client_path.return_value = None
            detector = GameDetector(config)
            with patch.object(detector, "_detect_via_leagueclient", return_value=(None, None)):
                with patch("lcu.core.lockfile.find_lockfile", return_value=str(client / "lockfile")):
                    self.assertEqual(detector.detect_paths(), (game, client))
            config.save_paths.assert_called_once_with(str(game), str(client))

    def test_partially_saved_game_path_restores_client_path(self):
        with tempfile.TemporaryDirectory() as temp:
            game, client = self.make_install(Path(temp))
            config = Mock()
            config.load_league_path.return_value = str(game)
            config.load_client_path.return_value = None
            detector = GameDetector(config)
            with patch.object(detector, "_detect_via_leagueclient", return_value=(None, None)):
                with patch("lcu.core.lockfile.find_lockfile", return_value=None):
                    self.assertEqual(detector.detect_paths(), (game, client))

    def test_fallback_rejects_incomplete_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            client = Path(temp) / "League of Legends"
            client.mkdir()
            (client / "LeagueClient.exe").write_bytes(b"fixture")
            config = Mock()
            config.load_league_path.return_value = None
            config.load_client_path.return_value = str(client)
            detector = GameDetector(config)
            with patch.object(detector, "_detect_via_leagueclient", return_value=(None, None)):
                with patch("lcu.core.lockfile.find_lockfile", return_value=None):
                    self.assertEqual(detector._detect_via_installation(), (None, None))

    def test_still_prioritizes_valid_config(self):
        with tempfile.TemporaryDirectory() as temp:
            game, client = self.make_install(Path(temp))
            config = Mock()
            config.load_league_path.return_value = str(game)
            config.load_client_path.return_value = str(client)
            detector = GameDetector(config)
            with patch.object(detector, "_detect_via_leagueclient") as process_scan:
                self.assertEqual(detector.detect_paths(), (game, client))
            process_scan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
