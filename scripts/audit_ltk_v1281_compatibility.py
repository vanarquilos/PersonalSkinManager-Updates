#!/usr/bin/env python3
r"""Read-only identity and game-build audit for official legacy LTK v1.28.1.

This does not download, install, load or replace any executable. An old
official build passing this audit is NOT vendor authorization or proof that
it works with current League assets. Do not ship it in a PSM installer.

Run only on separately obtained official files:
  python scripts/audit_ltk_v1281_compatibility.py --candidate-dir "X:\\LTK-v1281" --game-dir "C:\\Riot Games\\League of Legends\\Game"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from injection.tools.patcher import read_dll_eol, read_game_build  # noqa: E402

UPSTREAM = "LeagueToolkit/ltk-manager"
TAG = "v1.28.1"
COMMIT = "9f06802de5d83d6dde3ff1644a1c56049fadf9bb"
# Official git tree values at the tag. These protect against mistaken or
# unrelated executables; they do not prove material/host compatibility.
EXPECTED = {
    "ltk_patcher_host.exe": {
        "bytes": 1238272,
        "git_blob": "b2fc81c6de7bf5b40b81daaf8987706308ed5b33",
    },
    "ltk_patcher_dll.dll": {
        "bytes": 764160,
        "git_blob": "0cd0f58530906c3792e3189ea8af1a8f8bc6f264",
    },
}


def git_blob_sha1(payload: bytes) -> str:
    prefix = b"blob " + str(len(payload)).encode("ascii") + b"\x00"
    return hashlib.sha1(prefix + payload).hexdigest()


def utc(timestamp: int | None) -> str | None:
    return (datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
            if timestamp is not None else None)


def inspect(candidate_dir: Path, game_dir: Path) -> dict:
    binary_checks = {}
    problems = []
    for name, expected in EXPECTED.items():
        path = candidate_dir / name
        try:
            payload = path.read_bytes()
        except OSError:
            binary_checks[name] = {"exists": False, "official_git_blob_matches": False}
            problems.append(f"{name}: missing or unreadable")
            continue
        blob = git_blob_sha1(payload)
        match = len(payload) == expected["bytes"] and blob == expected["git_blob"]
        binary_checks[name] = {
            "exists": True,
            "bytes": len(payload),
            "official_git_blob_matches": match,
        }
        if not match:
            problems.append(f"{name}: differs from official pinned GitHub blob")
    build = read_game_build(game_dir)
    cutoff = read_dll_eol(candidate_dir / "ltk_patcher_dll.dll")
    if build is None:
        problems.append("League executable build timestamp unavailable")
    if cutoff is None:
        problems.append("Candidate DLL build cutoff unavailable")
    if build is not None and cutoff is not None and build > cutoff:
        problems.append("League executable is newer than the historical DLL cutoff")

    return {
        "upstream": UPSTREAM,
        "tag": TAG,
        "source_commit": COMMIT,
        "binary_checks": binary_checks,
        "league_game_build_utc": utc(build),
        "dll_game_build_cutoff_utc": utc(cutoff),
        "passes_identity_and_build_timestamp_checks": not problems,
        "problems": problems,
        "notes": [
            "No executables were downloaded, started, swapped, or modified.",
            "This checks original-file identity and build timestamps only.",
            "Version 1.28.1 predates League 26.21 material parsing fixes.",
            "Upstream host verification intentionally limits third-party use; "
            "an old version is not an authorized integration or a public release gate.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate-dir", type=Path, required=True)
    ap.add_argument("--game-dir", type=Path, required=True)
    args = ap.parse_args()
    report = inspect(args.candidate_dir, args.game_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["passes_identity_and_build_timestamp_checks"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
