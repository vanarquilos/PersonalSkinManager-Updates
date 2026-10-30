#!/usr/bin/env python3
"""LCU lockfile discovery from existing client config without process access."""
import configparser
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lcu.core.lockfile import find_lockfile


class SavedClientLockfileTests(unittest.TestCase):
    def test_saved_client_directory_locates_lockfile_without_process_query(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            client = root / "League of Legends"
            client.mkdir()
            lockfile = client / "lockfile"
            lockfile.write_text("unparsed private test fixture", encoding="utf-8")
            config = configparser.ConfigParser()
            config["General"] = {"clientPath": str(client)}
            config_file = root / "config.ini"
            with config_file.open("w", encoding="utf-8") as stream:
                config.write(stream)
            with patch("config.get_config_file_path", return_value=config_file):
                with patch.dict("os.environ", {"LCU_LOCKFILE": ""}):
                    self.assertEqual(find_lockfile(), str(lockfile))


if __name__ == "__main__":
    unittest.main()
