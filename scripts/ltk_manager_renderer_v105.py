#!/usr/bin/env python3
r"""Local LTK Manager rendering-session experiment, no unofficial DLL execution.

Usage:
  python -B scripts/ltk_manager_renderer_v105.py --inspect
  python -B scripts/ltk_manager_renderer_v105.py --profile "PSM Test Skin" --run

A profile must ALREADY exist in official LTK Manager and contain at least one
enabled permitted mod. This tool changes ONLY LTK's official GUI. On Ctrl+C
it stops its own patcher session and restores the previously active profile.
A Start response is NOT a guarantee of in-game skin rendering.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from injection.overlay.ltk_manager_ui_renderer import (  # noqa: E402
    LtkManagerUIRenderer,
    ManagerUIError,
    installed_manager,
    library_path,
    read_library,
    resolve_skin_profile,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--inspect", action="store_true",
                        help="Read-only list of profile names/mod counts")
    action.add_argument("--profile", type=str,
                        help="LTK profile name to activate with --run")
    action.add_argument("--skin-key", type=str,
                        help="PSM skin key resolved through --mapping")
    parser.add_argument("--mapping", type=Path,
                        help="JSON mapping of PSM skin keys to LTK profile names")
    parser.add_argument("--run", action="store_true",
                        help="Authorize official UI profile selection and Start")
    options = parser.parse_args()

    try:
        exe = installed_manager()
        if exe is None:
            raise ManagerUIError("LTK Manager installation not found.")
        index_file = library_path()
        profiles, active_id = read_library(index_file)
        if options.inspect:
            print(f"Manager: {exe}")
            print(f"Library: {index_file}")
            for p in profiles:
                marker = " (ACTIVE)" if p.profile_id == active_id else ""
                print(f"  {p.name}: {len(p.enabled_mods)} enabled mod(s){marker}")
            return 0
        if not options.run:
            raise ManagerUIError("--run is required to control the official manager GUI.")
        if options.profile:
            name = options.profile
        elif options.skin_key and options.mapping:
            name = resolve_skin_profile(options.skin_key, options.mapping)
        else:
            raise ManagerUIError("Provide --profile or --skin-key with --mapping.")

        renderer = LtkManagerUIRenderer(exe, index_file)
        session = renderer.activate(name, confirmed_by_user=True)
        print(f"LTK PATCHER START REQUEST CONFIRMED: {session.selected_profile}")
        print("Launch a permitted League Practice Tool game to inspect rendering.")
        print("This does not verify that a skin appeared.")
        print("Use Ctrl+C AFTER the game to stop the patcher and restore the profile.")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nStopping session and restoring previous profile...")
        renderer.finish(session)
        print("Requested LTK patcher stop and previous-profile restoration.")
        return 0
    except ManagerUIError as exc:
        print(f"LTK UI renderer: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
