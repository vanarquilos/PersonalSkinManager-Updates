#!/usr/bin/env python3
"""Read-only PSM pre-release audit of local LTK runtime inputs.

Use on the Windows build machine:
  python scripts/audit_runtime_v105.py --game-dir "C:\\Riot Games\\League of Legends\\Game"

This does not download, execute, or change any patcher file. It cannot by
itself prove that an LTK host/DLL pair supports the new 26.21 material format.
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

from injection.tools.patcher import check_ltk_patcher, read_game_build  # noqa: E402

RUNTIME_FILES = ("mod-tools.exe", "ltk_patcher_host.exe", "ltk_patcher_dll.dll")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def as_utc(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", required=True, type=Path,
                        help="Exact League Game directory containing its executable")
    parser.add_argument("--tools-dir", default=ROOT / "injection" / "tools", type=Path)
    args = parser.parse_args()

    files: dict[str, dict] = {}
    missing = []
    for name in RUNTIME_FILES:
        p = args.tools_dir / name
        if not p.is_file():
            missing.append(name)
            continue
        files[name] = {"bytes": p.stat().st_size, "sha256": sha256(p)}

    status = check_ltk_patcher(args.tools_dir)
    game_build = read_game_build(args.game_dir)
    errors = []
    warnings = []

    if missing:
        errors.append("Required runtime binaries missing: " + ", ".join(missing))
    if game_build is None:
        errors.append("Could not establish League build from the selected Game directory")
    if game_build is not None and status.eol is not None and status.expired_for(args.game_dir):
        errors.append("The bundled patcher DLL is older than the installed League build")
    if status.eol is None:
        warnings.append("DLL cutoff not detected; confirm runtime compatibility through upstream provenance and live testing")

    warnings.append(
        "Hashes identify local inputs; they do not prove that the host/DLL protocol, "
        "26.21 material hashes, or game overlay verification works"
    )

    print(json.dumps({
        "game_dir": str(args.game_dir),
        "game_build_pe_timestamp": game_build,
        "game_build_utc": as_utc(game_build),
        "dll_cutoff_pe_timestamp": status.eol,
        "dll_cutoff_utc": as_utc(status.eol),
        "runtime_files": files,
        "errors": errors,
        "warnings": warnings,
        "review_required": [
            "Confirm trusted source, license, and checksum for each runtime file",
            "Confirm LTK host/DLL protocol compatibility (v3 introduced upstream)",
            "Confirm League 26.21 overlay verification and material hash compatibility",
            "Test Practice Tool and Swiftplay in-game injection",
        ],
    }, indent=2))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
