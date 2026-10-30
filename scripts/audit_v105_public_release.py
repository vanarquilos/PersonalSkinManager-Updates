#!/usr/bin/env python3
"""Read-only v1.0.5 private-QA provenance and public-distribution preflight.

This does not modify LTK, CSLOL, PSM, League, signatures, manifests, or files.
CSLOL distribution requires separately verified CA signing and content restrictions;
there is intentionally no auto-approval or public release action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_NAME = (
    'PersonalSkinManager_v1.0.5_Combined_PrivateQA_'
    'PSMv105Combined-20261030-192151-d6ef3007.exe'
)
EXPECTED_SIZE = 28_210_688
EXPECTED_SHA256 = '49661E6419F1A0B0691DADBC6FC4D9F5193B997B2B55C1649200180DEF5AEF69'
SOURCE_COMMIT = 'b06fa4bde67bf226b371ff75f993c3434dfc8f9f'
SIGNED_LTK = {
    'ltk_patcher_host.exe': '23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1',
    'ltk_patcher_dll.dll': '6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74',
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()


def private_manifest_matches(manifest: dict) -> bool:
    """Match source and installer digest, without trusting path or filename alone."""
    return (
        str(manifest.get('source_commit', '')).lower() == SOURCE_COMMIT
        and str(manifest.get('installer_sha256', '')).upper() == EXPECTED_SHA256
    )


def audit(builds: Path, tools: Path, source: Path) -> dict:
    report = {
        'private_installer_filename': EXPECTED_NAME,
        'private_installer_found': False,
        'private_installer_matches_reported_sha256': False,
        'private_installer_matches_reported_size': False,
        'manifest_count': 0,
        'manifests_matching_source_and_installer': 0,
        'ltkv1281_source_hashes': {},
        'cslol_companion_present': False,
        'mod_tools_present': False,
        'unowned_skin_routing_in_source': False,
        'public_distribution_approved': False,
        'publication_blockers': [
            'CSLOL DLL Addendum §5: distributor public-trust CA code signing, timestamp and published fingerprint/hash are not evidenced',
            'CSLOL DLL Addendum §§6–7: launcher enforcement against paid-skin replication and competitive-advantage mods is not evidenced',
            'LTK Patcher License §2: signed private source pair cannot be bundled in public PSM without permission; separately staged unsigned copies need fresh gameplay QA',
            'The exact distributable installer has not been generated, reviewed and independently gameplay-tested',
        ],
    }
    candidate = builds / EXPECTED_NAME
    if candidate.is_file():
        report['private_installer_found'] = True
        report['private_installer_matches_reported_size'] = (candidate.stat().st_size == EXPECTED_SIZE)
        # Hash even if size differs so a mismatch is never incorrectly accepted.
        report['private_installer_matches_reported_sha256'] = (sha256_file(candidate) == EXPECTED_SHA256)
    if builds.is_dir():
        # Two previous manifests may be from different sessions; count matching
        # SHA and commit but don't claim they belong to the exact file by path.
        for path in builds.rglob('private-qa-manifest.json'):
            report['manifest_count'] += 1
            try:
                data = json.loads(path.read_text(encoding='utf-8-sig'))
                if isinstance(data, dict) and private_manifest_matches(data):
                    report['manifests_matching_source_and_installer'] += 1
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
    report['mod_tools_present'] = (tools / 'mod-tools.exe').is_file()
    report['cslol_companion_present'] = (tools / 'cslol-dll.dll').is_file()
    for name, expected in SIGNED_LTK.items():
        path = tools / name
        report['ltkv1281_source_hashes'][name] = (
            'PINNED ORIGINAL' if path.is_file() and sha256_file(path) == expected
            else 'MISSING OR DIFFERENT'
        )
    route = source / 'threads' / 'handlers' / 'injection_trigger.py'
    if route.is_file():
        text = route.read_text(encoding='utf-8', errors='replace')
        report['unowned_skin_routing_in_source'] = (
            'Custom mod targets unowned skin' in text
            or 'unowned selected skin is added as the Rose-style carrier' in text
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--builds-dir', type=Path,
                        default=Path.home() / 'Desktop' / 'PSM-Rose-Private-Builds')
    parser.add_argument('--repo', type=Path,
                        default=Path.home() / 'Desktop' / 'PersonalSkinManager-Updates')
    args = parser.parse_args()
    try:
        result = audit(args.builds_dir, args.repo / 'injection' / 'tools', args.repo)
    except OSError as exc:
        print(f'Read-only audit failed: {exc.__class__.__name__}: {exc}')
        return 1
    print(json.dumps(result, indent=2))
    print('\nPUBLIC RELEASE: NO-GO until all separately required license, signing, content and installed-QA checks are independently satisfied.')
    print('No files were written, copied, signed, changed, removed or published.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
