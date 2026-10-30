#!/usr/bin/env python3
"""Resolve ONLY a historical v1.0.5 Pengu startup warning in Rose diagnostics.

The Rose local source rollback renders skins and its issue reporter does not
emit PENGU_ACTIVATION_FAILED. A 2026-10-30 11:46 warning in the shared,
persistent diagnostics file belongs to the later failed installed candidate.

Read-only preview by default. --apply requires all PSM instances closed,
backs up the entire original file, and atomically removes exactly the
matching historical record plus its adjacent Fix: hint. It does not change
LTK, League, Pengu state, other diagnostic records, or game settings.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import tempfile

LEGACY_TIMESTAMP = "Oct 30 11:46"
LEGACY_MESSAGE = "League was detected, but the client integration could not start."


def default_diagnostics_file() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise RuntimeError("LOCALAPPDATA is unavailable")
    return Path(base) / "Rose" / "rose_diagnostics.txt"


def is_matching_issue(line: str) -> bool:
    timestamp, separator, message = line.strip().partition(" | ")
    return (
        bool(separator)
        and timestamp == LEGACY_TIMESTAMP
        and message == LEGACY_MESSAGE
    )


def plan_removal(lines: list[str]) -> tuple[list[str], int]:
    retained = []
    removed = 0
    skip_hint = False
    for line in lines:
        if skip_hint:
            skip_hint = False
            if line.lstrip().startswith("Fix:"):
                continue
        if is_matching_issue(line):
            removed += 1
            skip_hint = True
            continue
        retained.append(line)
    return retained, removed


def is_psm_active() -> bool:
    try:
        import psutil
    except ImportError as exc:
        raise RuntimeError("psutil is required to verify PSM is closed") from exc
    for proc in psutil.process_iter(attrs=["name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").casefold()
            if name in {"personalskinmanager.exe", "ltk_patcher_host.exe"}:
                return True
            if name in {"python.exe", "pythonw.exe", "python"}:
                args = proc.info.get("cmdline") or ()
                if any(Path(arg).name.casefold() == "main.py" for arg in args):
                    return True
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
    return False


def resolve_issue(path: Path, *, apply: bool) -> tuple[int, Path | None]:
    if not path.is_file():
        return 0, None

    original = path.read_bytes()
    # Round-trip the original bytes exactly on no-op; do not rewrite other rows.
    decoded = original.decode("utf-8-sig")
    lines = decoded.splitlines(keepends=True)
    retained, count = plan_removal(lines)
    if not apply or count == 0:
        return count, None
    if is_psm_active():
        raise RuntimeError("Close PSM and any LTK host before applying the cleanup")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(f"rose_diagnostics.backup-{timestamp}.txt")
    # Exclusive backup creation prevents accidental overwrite of an earlier copy.
    with backup.open("xb") as handle:
        handle.write(original)

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix="rose_diagnostics-clean-", suffix=".tmp",
            dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            # This source file uses UTF-8; keep any existing BOM.
            prefix = b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b""
            handle.write(prefix + "".join(retained).encode("utf-8"))
        shutil.copymode(path, temporary)
        # Fail if another process has modified the diagnostics since our read.
        if path.read_bytes() != original:
            raise RuntimeError("Diagnostics changed while preparing cleanup; no changes applied")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    return count, backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Back up and remove the single old warning")
    parser.add_argument("--file", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        target = args.file if args.file else default_diagnostics_file()
        count, backup = resolve_issue(target, apply=args.apply)
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"[ERROR] Stale-warning cleanup refused: {type(exc).__name__}: {exc}")
        return 1

    if not count:
        print("[OK] No matching October 30 11:46 legacy warning exists. No files changed.")
    elif backup is None:
        print(f"[PREVIEW] Found {count} old Pengu integration warning record(s); nothing changed.")
        print("Close PSM, then rerun with --apply to back up the diagnostics and remove only those records.")
    else:
        print(f"[OK] Removed {count} old 11:46 warning record(s). Other diagnostics preserved.")
        print(f"[OK] Original diagnostics safely backed up as: {backup.name}")
        print("Reopen PSM Troubleshooting to refresh its displayed warnings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
