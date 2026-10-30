#!/usr/bin/env python3
"""Read-only inventory of existing local LTK host/DLL pairs for PSM v1.0.5.

No network, downloads, DLL execution, signature changes, file copying or
process/game interaction. A compatible *cutoff* is not gameplay proof.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from injection.tools.patcher import (
    LTK_PATCHER_DLL,
    LTK_PATCHER_HOST,
    _hash_file,
    read_dll_eol,
    read_game_build,
)

MAX_PAIRS = 100


def candidate_report(host: Path, game_build: int | None) -> dict:
    dll = host.parent / LTK_PATCHER_DLL
    entry: dict = {
        "directory": str(host.parent),
        "host": LTK_PATCHER_HOST,
        "dll": LTK_PATCHER_DLL if dll.is_file() else "MISSING",
        "host_sha256": None,
        "dll_sha256": None,
        "dll_cutoff_utc": None,
        "status": "UNVERIFIED",
    }
    if host.is_symlink() or dll.is_symlink() or not dll.is_file():
        entry["status"] = "INCOMPLETE_OR_LINKED"
        return entry
    try:
        entry["host_sha256"] = _hash_file(host)
        entry["dll_sha256"] = _hash_file(dll)
        cutoff = read_dll_eol(dll)
    except (OSError, ValueError):
        entry["status"] = "UNREADABLE"
        return entry
    if cutoff is None:
        entry["status"] = "UNKNOWN_DLL_CUTOFF"
        return entry
    entry["dll_cutoff_utc"] = datetime.fromtimestamp(
        cutoff, tz=timezone.utc
    ).isoformat()
    if game_build is None:
        entry["status"] = "UNKNOWN_GAME_BUILD"
    elif game_build > cutoff:
        entry["status"] = "EXPIRED_FOR_INSTALLED_GAME"
    else:
        entry["status"] = "CUTOFF_NOT_EXCEEDED"
    return entry


def find_pairs(roots: list[Path], game_build: int | None) -> list[dict]:
    reports = []
    seen = set()
    for root in roots:
        if not root.is_dir() or root.is_symlink():
            continue
        try:
            files = sorted(root.rglob(LTK_PATCHER_HOST))
        except OSError:
            continue
        for host in files:
            if not host.is_file() or host.is_symlink():
                continue
            directory = host.parent.resolve()
            if directory in seen:
                continue
            seen.add(directory)
            reports.append(candidate_report(host, game_build))
            if len(reports) >= MAX_PAIRS:
                return reports
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league-dir", type=Path, required=True)
    parser.add_argument("--root", type=Path, action="append", required=True)
    args = parser.parse_args()

    # The configured League installation may point at the installation root.
    game_build = read_game_build(args.league_dir)
    if game_build is None:
        game_build = read_game_build(args.league_dir / "Game")
    rows = find_pairs(args.root, game_build)
    print(json.dumps({
        "game_build_utc": (
            datetime.fromtimestamp(game_build, tz=timezone.utc).isoformat()
            if game_build is not None else None
        ),
        "candidates": rows,
        "notice": (
            "No files changed. CUTOFF_NOT_EXCEEDED is NOT proof of "
            "signature validity, LTK protocol compatibility, supported "
            "cosmetic rendering, or permission to redistribute binaries."
        ),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
