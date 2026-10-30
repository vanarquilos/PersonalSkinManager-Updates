#!/usr/bin/env python3
"""Unit tests for explicit manifest-pinned modern LTK private QA runtime."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from injection.tools.patcher import (
    LTK_PATCHER_HOST,
    LTK_PATCHER_DLL,
    LTK_QA_RUNTIME_DIR_ENV,
    LTK_QA_MANIFEST_ENV,
    LTK_CURRENT_HOST_PROTOCOL,
    check_ltk_patcher,
)


class CurrentLtkPrivateQaManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.selected = self.root / "reviewed"
        self.selected.mkdir()
        self.blobs = {
            LTK_PATCHER_HOST: b"test-host-not-an-executable",
            LTK_PATCHER_DLL: b"test-dll-not-an-executable",
        }
        for name, content in self.blobs.items():
            (self.selected / name).write_bytes(content)
        self.info = {
            "schema": 1,
            "purpose": "PSM_V105_PRIVATE_QA_ONLY",
            "source_manager_release": "v1.31.1",
            "host_protocol": LTK_CURRENT_HOST_PROTOCOL,
            "public_distribution_approved": False,
            "files_sha256": {
                k: hashlib.sha256(v).hexdigest().upper() for k, v in self.blobs.items()
            },
        }
        self.manifest = self.root / "manifest.json"
        self.save()
        env = {
            LTK_QA_RUNTIME_DIR_ENV: str(self.selected),
            LTK_QA_MANIFEST_ENV: str(self.manifest),
        }
        patcher = patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def save(self):
        self.manifest.write_text(json.dumps(self.info), encoding="utf-8")

    def check(self):
        return check_ltk_patcher(self.root / "fallback")

    def test_accepts_exact_pinned_current_pair_without_gameplay_claim(self):
        status = self.check()
        self.assertEqual(status.missing, [])
        self.assertEqual(status.host, self.selected / LTK_PATCHER_HOST)
        self.assertEqual(status.dll, self.selected / LTK_PATCHER_DLL)

    def test_rejects_mismatched_or_missing_binary(self):
        (self.selected / LTK_PATCHER_HOST).write_bytes(b"tampered")
        self.assertIn("fingerprint mismatch", " ".join(self.check().missing))
        (self.selected / LTK_PATCHER_DLL).unlink()
        self.assertIn("missing", " ".join(self.check().missing))

    def test_rejects_bad_purpose_protocol_and_public_distribution(self):
        for key, bad in (
            ("purpose", "PUBLIC_RELEASE"),
            ("host_protocol", 2),
            ("host_protocol", True),
            ("public_distribution_approved", True),
            ("schema", 2),
        ):
            with self.subTest(key=key, bad=bad):
                original = self.info[key]
                self.info[key] = bad
                self.save()
                self.assertTrue(self.check().missing)
                self.info[key] = original
        self.save()

    def test_manager_label_not_accepting_invalid_value(self):
        for label in ("v1.31", "../other", "1.31.1", "v1.31.1-beta", "", 1311):
            with self.subTest(label=label):
                self.info["source_manager_release"] = label
                self.save()
                self.assertTrue(self.check().missing)
        self.info["source_manager_release"] = "v1.31.1"
        self.save()

    def test_rejects_missing_manifest_and_oversized(self):
        self.manifest.unlink()
        self.assertTrue(self.check().missing)
        self.manifest.write_text(" " * 16385, encoding="utf-8")
        self.assertTrue(self.check().missing)

    def test_rejects_symlinked_files(self):
        # Not every Windows user has symlink privileges; skip only this test.
        target = self.root / "target-host.exe"
        target.write_bytes(self.blobs[LTK_PATCHER_HOST])
        (self.selected / LTK_PATCHER_HOST).unlink()
        try:
            (self.selected / LTK_PATCHER_HOST).symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this test host")
        self.assertTrue(self.check().missing)

    def test_manifest_without_dir_never_silently_uses_fallback(self):
        with patch.dict(os.environ, {LTK_QA_RUNTIME_DIR_ENV: ""}):
            self.assertIn("requires a runtime directory", " ".join(self.check().missing))


if __name__ == "__main__":
    unittest.main()
