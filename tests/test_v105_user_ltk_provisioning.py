#!/usr/bin/env python3
"""Rose-style user-owned LTK import: hash verification and non-distribution."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from injection.tools import patcher

ROOT = Path(__file__).resolve().parents[1]


class UserProvidedLtkTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.names = (patcher.LTK_PATCHER_HOST, patcher.LTK_PATCHER_DLL)
        self.blobs = dict(zip(self.names, [b"non-executable-test-host", b"non-executable-test-dll"]))
        for name, data in self.blobs.items():
            (self.root / name).write_bytes(data)
        self.manifest = self.root / patcher.LTK_USER_MANIFEST
        self.record = {
            "schema": 1,
            "purpose": "PSM_V105_USER_PROVIDED_LTK",
            "host_protocol": patcher.LTK_CURRENT_HOST_PROTOCOL,
            "public_distribution_approved": False,
            "files_sha256": {
                k: hashlib.sha256(v).hexdigest().upper()
                for k, v in self.blobs.items()
            },
        }
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.record), encoding="utf-8")

    def get(self):
        with patch.dict(os.environ, {
            patcher.LTK_QA_RUNTIME_DIR_ENV: "",
            patcher.LTK_QA_MANIFEST_ENV: "",
        }):
            return patcher.check_ltk_patcher(self.root)

    def test_valid_user_supplied_pair_is_pinned(self):
        status = self.get()
        self.assertFalse(status.missing)
        self.assertEqual(status.host, self.root / self.names[0])
        self.assertEqual(status.dll, self.root / self.names[1])

    def test_tampering_fails_closed_even_if_files_exist(self):
        (self.root / self.names[0]).write_bytes(b"tampered")
        self.assertIn("changed since provisioning", " ".join(self.get().missing))

    def test_incomplete_pair_is_rejected(self):
        (self.root / self.names[1]).unlink()
        self.assertIn("missing", " ".join(self.get().missing))

    def test_bad_manifest_protocol_and_distribution_are_rejected(self):
        for key, value in [
            ("host_protocol", 2), ("host_protocol", True),
            ("purpose", "PUBLIC_RELEASE"), ("public_distribution_approved", True),
        ]:
            with self.subTest(key=key, value=value):
                old = self.record[key]
                self.record[key] = value
                self.save()
                self.assertTrue(self.get().missing)
                self.record[key] = old
        self.save()

    def test_missing_user_manifest_does_not_invent_provenance(self):
        self.manifest.unlink()
        self.assertTrue(self.get().host.is_file())
        # Legacy source pair is allowed for developer compatibility, but not
        # classified as user-provisioned or a verified new distribution.
        self.assertEqual(self.get().missing, [])

    def test_provisioning_script_does_not_overwrite_or_bypass_checks(self):
        source = (ROOT / "scripts/import_user_ltk_v105.ps1").read_text("utf-8")
        self.assertIn("Get-AuthenticodeSignature", source)
        self.assertIn("Get-FileHash", source)
        self.assertIn("No overwrite permitted", source)
        self.assertIn("ReparsePoint", source)
        self.assertIn("WindowsBuiltInRole]::Administrator", source)
        self.assertIn("PSM_V105_USER_PROVIDED_LTK", source)
        self.assertNotIn("signtool remove", source)

    def test_tools_manager_enforces_patcher_manifest_errors(self):
        source = (ROOT / "injection/tools/tools_manager.py").read_text("utf-8")
        self.assertIn("missing = list(patcher.missing)", source)


if __name__ == "__main__":
    unittest.main()
