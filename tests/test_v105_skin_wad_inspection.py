#!/usr/bin/env python3
"""Offline unit tests for the read-only selected skin WAD inspection."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.inspect_v105_skin_wad import (
    game_relative_wad,
    packed_fantome_wad_alias,
    inspect_archive,
    wad_payload_fingerprint,
)

WAD_HEADER = b"RW" + (b"\x00" * 266)


class SkinWadInspectionTests(unittest.TestCase):
    def test_normalizes_only_game_relative_wad_members(self):
        expected = "DATA/FINAL/Champions/Ahri.wad.client"
        self.assertEqual(str(game_relative_wad("WAD/" + expected)), expected)
        self.assertEqual(str(game_relative_wad(expected)), expected)
        self.assertIsNone(game_relative_wad("META/info.json"))
        self.assertIsNone(game_relative_wad("WAD/DATA/../secret.wad.client"))
        self.assertIsNone(game_relative_wad("C:/Windows/secret.wad.client"))

    def test_packed_fantome_alias_is_valid_without_game_relative_path(self):
        self.assertEqual(
            packed_fantome_wad_alias("WAD/Aphelios.wad.client"),
            "Aphelios.wad.client",
        )
        self.assertEqual(
            packed_fantome_wad_alias("wad/aphelios.wad.client"),
            "aphelios.wad.client",
        )
        self.assertIsNone(game_relative_wad("WAD/Aphelios.wad.client"))
        self.assertIsNone(packed_fantome_wad_alias("WAD/../bad.wad.client"))

    def test_packed_fantome_inspection_reports_advisory_game_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / "game"
            installed = game / "DATA" / "FINAL" / "Champions" / "Aphelios.wad.client"
            installed.parent.mkdir(parents=True, exist_ok=True)
            installed.write_bytes(WAD_HEADER + b"large-original-game-payload")

            mod = root / "aphelios.fantome"
            with zipfile.ZipFile(mod, "w") as z:
                z.writestr("META/info.json", "{}")
                z.writestr(
                    "WAD/Aphelios.wad.client",
                    WAD_HEADER + b"small-modified-chunks",
                )
            report = inspect_archive(mod, game)
            self.assertEqual(report["archive_member_count"], 2)
            self.assertEqual(report["wad_member_count"], 1)
            check = report["wad_checks"][0]
            self.assertEqual(check["package_wad_format"], "fantome_packed_wad")
            self.assertEqual(check["wad_alias"], "Aphelios.wad.client")
            self.assertTrue(check["packed_wad_header_valid"])
            self.assertIsNone(check["recognized_game_relative_path"])
            self.assertEqual(
                check["game_wad_filename_candidates"],
                ["DATA/FINAL/Champions/Aphelios.wad.client"],
            )
            self.assertFalse(check["matching_game_wad_exists"])
            self.assertIsNone(check["payload_identical_to_installed_game"])

    def test_identical_and_modified_wads_are_distinguished(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            relative = "DATA/FINAL/Champions/Ahri.wad.client"
            original = root / "game" / relative
            original.parent.mkdir(parents=True)
            original.write_bytes(WAD_HEADER + b"original-game-payload")

            skin = root / "skin.zip"
            with zipfile.ZipFile(skin, "w") as z:
                z.writestr("META/info.json", "{}")
                z.writestr("WAD/" + relative, WAD_HEADER + b"original-game-payload")

            same = inspect_archive(skin, root / "game")
            self.assertEqual(same["archive_member_count"], 2)
            self.assertEqual(same["wad_member_count"], 1)
            self.assertTrue(same["wad_checks"][0]["matching_game_wad_exists"])
            self.assertTrue(same["wad_checks"][0]["payload_identical_to_installed_game"])

            with zipfile.ZipFile(skin, "w") as z:
                z.writestr("META/info.json", "{}")
                z.writestr("WAD/" + relative, WAD_HEADER + b"modified-skin-payload")
            changed = inspect_archive(skin, root / "game")
            self.assertFalse(changed["wad_checks"][0]["payload_identical_to_installed_game"])

    def test_no_wad_is_reported_without_modifying_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skin = root / "skin.fantome"
            with zipfile.ZipFile(skin, "w") as z:
                z.writestr("META/info.json", "{}")
            result = inspect_archive(skin, root / "game")
            self.assertEqual(result["wad_member_count"], 0)


if __name__ == "__main__":
    unittest.main()
