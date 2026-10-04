#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

from injection.overlay.overlay_manager import OverlayManager, WAD_V3_HEADER_SIZE


class Patch2619WadHeaderTests(unittest.TestCase):
    def test_rebases_current_game_header_without_touching_overlay_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            game = root / "Game"
            overlay = root / "overlay"
            relative = Path("DATA/FINAL/Champions/Aphelios.wad.client")
            game_wad = game / relative
            overlay_wad = overlay / relative
            game_wad.parent.mkdir(parents=True)
            overlay_wad.parent.mkdir(parents=True)

            prefix = b"RW\x03\x00"
            game_header = prefix + bytes((i % 251 for i in range(WAD_V3_HEADER_SIZE - 4)))
            old_header = prefix + b"\x00" * (WAD_V3_HEADER_SIZE - 4)
            payload = b"PSM-MODDED-PAYLOAD" * 32

            game_wad.write_bytes(game_header + b"ORIGINAL-GAME-DATA")
            overlay_wad.write_bytes(old_header + payload)

            restored, candidates = OverlayManager._restore_game_wad_headers(
                overlay,
                game,
            )

            self.assertEqual((restored, candidates), (1, 1))
            result = overlay_wad.read_bytes()
            self.assertEqual(result[:WAD_V3_HEADER_SIZE], game_header)
            self.assertEqual(result[WAD_V3_HEADER_SIZE:], payload)

    def test_skips_header_when_wad_magic_or_version_does_not_match(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            game = root / "Game"
            overlay = root / "overlay"
            relative = Path("DATA/FINAL/Champions/Caitlyn.wad.client")
            game_wad = game / relative
            overlay_wad = overlay / relative
            game_wad.parent.mkdir(parents=True)
            overlay_wad.parent.mkdir(parents=True)

            game_wad.write_bytes(
                b"RW\x03\x00" + b"A" * (WAD_V3_HEADER_SIZE - 4) + b"GAME"
            )
            before = b"RW\x02\x00" + b"B" * (WAD_V3_HEADER_SIZE - 4) + b"MOD"
            overlay_wad.write_bytes(before)

            restored, candidates = OverlayManager._restore_game_wad_headers(
                overlay,
                game,
            )

            self.assertEqual((restored, candidates), (0, 1))
            self.assertEqual(overlay_wad.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
