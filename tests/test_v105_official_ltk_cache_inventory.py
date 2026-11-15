#!/usr/bin/env python3
"""Official LTK delivery cache is read-only and never a patcher downloader."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from scripts import audit_official_ltk_delivery_cache_v105 as audit


class OfficialLtkCacheInventoryTests(TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.blob = b"fixture delivered dll"
        import hashlib
        digest = hashlib.sha256(self.blob).hexdigest()
        self.directory = self.root / digest
        self.directory.mkdir()
        (self.directory / audit.LTK_PATCHER_DLL).write_bytes(self.blob)
        (self.directory / audit.LTK_PATCHER_HOST).write_bytes(b"fixture host")

    def test_matching_digest_with_newer_game_is_expired(self):
        with mock.patch.object(audit, "read_dll_eol", return_value=100):
            rows = audit.probe(self.root, game_build=101)
        self.assertEqual(rows[0]["status"], "EXPIRED_FOR_INSTALLED_GAME")

    def test_matching_digest_with_older_game_is_not_rendering_proof(self):
        with mock.patch.object(audit, "read_dll_eol", return_value=100):
            rows = audit.probe(self.root, game_build=99)
        self.assertEqual(rows[0]["status"], "CUTOFF_NOT_EXCEEDED")
        self.assertNotIn("WORKING", rows[0]["status"])

    def test_mismatched_hash_directory_is_rejected(self):
        (self.directory / audit.LTK_PATCHER_DLL).write_bytes(b"changed")
        rows = audit.probe(self.root, game_build=99)
        self.assertEqual(rows[0]["status"], "DIGEST_DIRECTORY_MISMATCH")

    def test_staged_host_is_required(self):
        (self.directory / audit.LTK_PATCHER_HOST).unlink()
        rows = audit.probe(self.root, game_build=99)
        self.assertEqual(rows[0]["status"], "INCOMPLETE")

    def test_no_delivery_json_token_access(self):
        src = Path(audit.__file__).read_text("utf-8")
        self.assertNotIn('read_text("delivery.json")', src)
        self.assertNotIn('joinpath("delivery.json")', src)
        for forbidden in ("requests.", "urllib.", "subprocess.", "Invoke-WebRequest"):
            self.assertNotIn(forbidden, src)

    def test_missing_cache_is_safe(self):
        self.assertEqual(audit.probe(self.root / "no-such-root", 42), [])


if __name__ == "__main__":
    import unittest
    unittest.main()
