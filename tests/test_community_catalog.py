#!/usr/bin/env python3
import unittest

from utils.download.community_catalog import CommunityCatalogService


class CommunityCatalogParsingTests(unittest.TestCase):
    def test_accepts_hash_pinned_https_entry(self):
        entry = CommunityCatalogService._parse_entry(
            {
                "id": "creator-mod-1",
                "championId": 523,
                "name": "Example",
                "packageUrl": "https://example.com/example.fantome",
                "sha256": "a" * 64,
                "targetSkinIds": [523000],
            }
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry.catalog_mod_id, "catalog:creator-mod-1")

    def test_rejects_unpinned_or_non_https_entry(self):
        self.assertIsNone(
            CommunityCatalogService._parse_entry(
                {
                    "id": "bad",
                    "championId": 523,
                    "name": "Bad",
                    "packageUrl": "http://example.com/bad.fantome",
                    "sha256": "a" * 64,
                    "targetSkinIds": [523000],
                }
            )
        )
        self.assertIsNone(
            CommunityCatalogService._parse_entry(
                {
                    "id": "bad",
                    "championId": 523,
                    "name": "Bad",
                    "packageUrl": "https://example.com/bad.fantome",
                    "sha256": "",
                    "targetSkinIds": [523000],
                }
            )
        )

    def test_rejects_cross_champion_targets_and_path_like_ids(self):
        self.assertIsNone(
            CommunityCatalogService._parse_entry(
                {
                    "id": "../escape",
                    "championId": 523,
                    "name": "Bad",
                    "packageUrl": "https://example.com/bad.fantome",
                    "sha256": "b" * 64,
                    "targetSkinIds": [523000],
                }
            )
        )
        self.assertIsNone(
            CommunityCatalogService._parse_entry(
                {
                    "id": "wrong-target",
                    "championId": 523,
                    "name": "Bad",
                    "packageUrl": "https://example.com/bad.fantome",
                    "sha256": "b" * 64,
                    "targetSkinIds": [51000],
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
