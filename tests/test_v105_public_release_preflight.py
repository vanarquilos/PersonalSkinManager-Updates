#!/usr/bin/env python3
"""The public-release audit is read-only and cannot approve the private installer."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_v105_public_release import (
    EXPECTED_SHA256, SOURCE_COMMIT, audit, private_manifest_matches,
)


class PublicReleasePreflightTests(unittest.TestCase):
    def test_manifest_requires_both_commit_and_installer_hash(self):
        self.assertTrue(private_manifest_matches({
            'source_commit': SOURCE_COMMIT,
            'installer_sha256': EXPECTED_SHA256,
        }))
        self.assertFalse(private_manifest_matches({
            'source_commit': SOURCE_COMMIT,
            'installer_sha256': 'incorrect',
        }))
        self.assertFalse(private_manifest_matches({
            'source_commit': 'incorrect',
            'installer_sha256': EXPECTED_SHA256,
        }))

    def test_audit_cannot_change_files_or_approve_distribution(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            builds = root / 'builds'
            builds.mkdir()
            source = root / 'source'
            tools = source / 'injection' / 'tools'
            tools.mkdir(parents=True)
            manifest = builds / 'private-qa-manifest.json'
            manifest.write_text(json.dumps({
                'source_commit': SOURCE_COMMIT,
                'installer_sha256': EXPECTED_SHA256,
            }), encoding='utf-8')
            before = {p.as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            report = audit(builds, tools, source)
            after = {p.as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(report['manifests_matching_source_and_installer'], 1)
            self.assertFalse(report['public_distribution_approved'])
            self.assertEqual(len(report['publication_blockers']), 4)


if __name__ == '__main__':
    unittest.main()
