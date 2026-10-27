#!/usr/bin/env python3
"""Read-only PSM v1.0.5 selected-skin WAD inspection.

Does not launch League, extract/write archives, alter files, or invoke a patcher.
Prints only relative archive member paths and structural/comparison results.
Example:
  python scripts/inspect_v105_skin_wad.py
  python scripts/inspect_v105_skin_wad.py --game-dir "D:\Riot Games\League of Legends\Game"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

WAD_HEADER_SIZE = 268
SKIN_LOG_MARKER = re.compile(r"\[INJECT\] Using skin file:\s*(.+?)\s*$", re.I)
MAX_REPORT_WADS = 12


def get_latest_skin_archive(log_dir: Path) -> tuple[Path | None, str]:
    logs = sorted(log_dir.glob("rose_*.log*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return None, "no_log_files"
    for log in logs[:3]:
        # PSM rotates logs, so limit the scan to the newest 6,000 lines.
        try:
            with log.open("r", encoding="utf-8", errors="replace") as stream:
                from collections import deque
                recent = deque(stream, maxlen=6000)
        except OSError:
            continue
        paths = []
        for line in recent:
            match = SKIN_LOG_MARKER.search(line)
            if match:
                paths.append(match.group(1).strip().strip('"'))
        if paths:
            return Path(paths[-1]), "found"
    return None, "no_skin_archive_line"


def game_relative_wad(member_name: str) -> PurePosixPath | None:
    """Accept only ordinary WAD/... or DATA/... relative WAD member names."""
    name = member_name.replace("\\", "/")
    parts = list(PurePosixPath(name).parts)
    if parts and parts[0].lower() == "wad":
        parts.pop(0)
    if (
        not parts
        or parts[0].lower() != "data"
        or any(p in {"..", ".", "/", ""} or ":" in p for p in parts)
        or not parts[-1].lower().endswith(".wad.client")
    ):
        return None
    return PurePosixPath(*parts)


def wad_payload_fingerprint(stream) -> tuple[bool, str]:
    header = stream.read(WAD_HEADER_SIZE)
    if len(header) < WAD_HEADER_SIZE:
        return False, ""
    digest = hashlib.sha256()
    for data in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(data)
    return header[:2] == b"RW", digest.hexdigest()


def inspect_archive(archive_path: Path, game_dir: Path) -> dict:
    report: dict = {
        "selected_skin_archive_exists": archive_path.is_file(),
        "archive_member_count": None,
        "wad_member_count": None,
        "wad_checks": [],
        "notes": [],
    }
    if not archive_path.is_file():
        report["notes"].append("Selected archive missing; the log may be from an old session.")
        return report
    try:
        with zipfile.ZipFile(archive_path, "r") as package:
            members = [m for m in package.infolist() if not m.is_dir()]
            wads = [m for m in members if m.filename.lower().endswith(".wad.client")]
            report["archive_member_count"] = len(members)
            report["wad_member_count"] = len(wads)
            if not wads:
                report["notes"].append("Selected archive contains no .wad.client entries.")
            if len(wads) > MAX_REPORT_WADS:
                report["notes"].append("Only the first 12 WAD entries are inspected.")
            game_root = game_dir.resolve()
            for member in wads[:MAX_REPORT_WADS]:
                normalized = game_relative_wad(member.filename)
                check = {
                    "member_relative_path": member.filename.replace("\\", "/"),
                    "wad_bytes": member.file_size,
                    "recognized_game_relative_path": str(normalized) if normalized else None,
                    "packed_wad_header_valid": False,
                    "matching_game_wad_exists": False,
                    "game_wad_header_valid": None,
                    "payload_identical_to_installed_game": None,
                }
                if normalized is not None:
                    game_wad = (game_root / Path(*normalized.parts)).resolve()
                    if game_wad.is_relative_to(game_root) and game_wad.is_file():
                        check["matching_game_wad_exists"] = True
                with package.open(member) as packed:
                    valid, packed_hash = wad_payload_fingerprint(packed)
                check["packed_wad_header_valid"] = valid
                if check["matching_game_wad_exists"]:
                    with game_wad.open("rb") as game_stream:
                        game_valid, game_hash = wad_payload_fingerprint(game_stream)
                    check["game_wad_header_valid"] = game_valid
                    if valid and game_valid:
                        check["payload_identical_to_installed_game"] = packed_hash == game_hash
                report["wad_checks"].append(check)
    except (OSError, RuntimeError, zipfile.BadZipFile, EOFError, ValueError):
        report["notes"].append("Could not read/compare this archive; check whether it is a valid ZIP/Fantome.")
    report["notes"].append(
        "Different payload bytes indicate changes, not that the skin was redirected or rendered."
    )
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--game-dir",
        type=Path,
        default=Path(r"C:\Riot Games\League of Legends\Game"),
        help="League's Game directory, used read-only for WAD comparisons.",
    )
    ap.add_argument(
        "--log-dir",
        type=Path,
        default=Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Rose" / "logs",
    )
    args = ap.parse_args()
    archive_path, status = get_latest_skin_archive(args.log_dir)
    if archive_path is None:
        print(json.dumps({"log_status": status, "notes": ["Run from an earlier source QA session is required."]}, indent=2))
        return 1
    result = inspect_archive(archive_path, args.game_dir)
    result["log_status"] = status
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
