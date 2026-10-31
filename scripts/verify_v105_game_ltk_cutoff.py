#!/usr/bin/env python3
"""Fail a PSM v1.0.5 private QA build when local LTK DLL predates League.

Read-only PE metadata inspection. Does not run, modify, download or replace
the patcher; timestamp eligibility is NOT proof of in-game functionality.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from injection.tools.patcher import (  # noqa: E402
    LTK_PATCHER_DLL,
    LTK_PATCHER_HOST,
    read_dll_eol,
    read_game_build,
)


def compare_game_and_patch(game_dir: Path, ltk_dir: Path) -> tuple[bool, str]:
    host = ltk_dir / LTK_PATCHER_HOST
    dll = ltk_dir / LTK_PATCHER_DLL
    if not host.is_file() or not dll.is_file() or host.is_symlink() or dll.is_symlink():
        return False, "Blocked: missing or symlinked LTK host/DLL."
    game_build = read_game_build(game_dir)
    if game_build is None:
        game_build = read_game_build(game_dir / "Game")
    if game_build is None:
        return False, "Blocked: cannot establish installed League executable PE build."
    cutoff = read_dll_eol(dll)
    if cutoff is None:
        return False, "Blocked: LTK DLL build cutoff cannot be verified."
    timestamp = lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    detail = (
        f"League PE build: {timestamp(game_build)}; "
        f"LTK DLL cutoff: {timestamp(cutoff)}."
    )
    if game_build > cutoff:
        return False, "Blocked: local LTK DLL expired for installed League. " + detail
    return True, (
        "Cutoff not exceeded; this is NOT proof of vendor provenance, "
        "host protocol compatibility, cosmetic rendering or redistribution rights. "
        + detail
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--ltk-dir", type=Path, required=True)
    args = parser.parse_args()
    eligible, message = compare_game_and_patch(args.game_dir, args.ltk_dir)
    print(message)
    return 0 if eligible else 2


if __name__ == "__main__":
    raise SystemExit(main())
