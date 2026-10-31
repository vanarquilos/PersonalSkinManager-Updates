#!/usr/bin/env python3
"""Distribution security audit: permit certifi CA store, never private credentials."""
import tempfile
import unittest
from pathlib import Path

from scripts.audit_v105_distribution_tree import inspect_distribution


CERT = b"-----BEGIN CERTIFICATE-----\nPUBLIC-TEST-ONLY\n-----END CERTIFICATE-----\n"
KEY = b"-----BEGIN PRIVATE KEY-----\nSECRET-TEST-ONLY\n-----END PRIVATE KEY-----\n"


class DistributionTreeAuditTests(unittest.TestCase):
    def test_public_certifi_ca_trust_bundle_is_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "_internal" / "certifi" / "cacert.pem"
            path.parent.mkdir(parents=True)
            path.write_bytes(CERT)
            blocked, allowed = inspect_distribution(Path(td))
            self.assertEqual(blocked, [])
            self.assertEqual(allowed, ["_internal/certifi/cacert.pem"])

    def test_unrelated_pem_certificate_is_not_automatically_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "_internal" / "some_library" / "certificate.pem"
            path.parent.mkdir(parents=True)
            path.write_bytes(CERT)
            blocked, _ = inspect_distribution(Path(td))
            self.assertEqual(blocked, ["_internal/some_library/certificate.pem"])

    def test_certifi_path_with_private_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "_internal" / "certifi" / "cacert.pem"
            path.parent.mkdir(parents=True)
            path.write_bytes(CERT + KEY)
            blocked, allowed = inspect_distribution(Path(td))
            self.assertEqual(blocked, ["_internal/certifi/cacert.pem"])
            self.assertEqual(allowed, [])

    def test_runtime_state_and_signing_credentials_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            for name in (
                "_v105_rose_legacy_local_state.json",
                "publisher.pfx",
                "release_private.key",
                "cert.p12",
                "session.pem",
            ):
                (Path(td) / name).write_bytes(b"private test fixture")
            blocked, _ = inspect_distribution(Path(td))
            self.assertEqual(len(blocked), 5)

    def test_other_normal_application_files_are_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "PersonalSkinManager.exe").write_bytes(b"fixture")
            blocked, allowed = inspect_distribution(Path(td))
            self.assertEqual((blocked, allowed), ([], []))


if __name__ == "__main__":
    unittest.main()
