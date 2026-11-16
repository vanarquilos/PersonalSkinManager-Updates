#!/usr/bin/env python3
"""PSM v1.0.5 official LTK Manager handoff (custom mods only).

No patcher control, DLL manipulation, background automation, or success claims.
Usage:
  python scripts/ltk_manager_handoff_v105.py --status
  python scripts/ltk_manager_handoff_v105.py --open-manager --confirm
  python scripts/ltk_manager_handoff_v105.py --import-custom-mod "C:\mods\my-mod.fantome" --confirm
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.integration.ltk_manager_handoff import (  # noqa: E402
    ModHandoffError, find_manager, request_custom_mod_import, request_open_manager,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--status", action="store_true", help="Read-only installation check")
    action.add_argument("--open-manager", action="store_true", help="Open official manager UI")
    action.add_argument("--import-custom-mod", type=Path,
                        help="Request LTK's import UI for a local .fantome/.modpkg")
    parser.add_argument("--confirm", action="store_true",
                        help="Explicitly authorize opening the external program")
    parser.add_argument("--manager-exe", type=Path,
                        help="Optional full path to an installed ltk-manager.exe")
    args = parser.parse_args()

    manager = args.manager_exe or find_manager()
    if args.status:
        print(f"LTK manager: {manager if manager else 'NOT_FOUND'}")
        print("PSM skin rendering: NOT_VERIFIED")
        print("LTK public file-open handoff: custom mods only")
        print("No published LTK API for automatic PSM patcher/session control.")
        return 0 if manager else 2

    try:
        if args.open_manager:
            result = request_open_manager(
                confirmed_by_user=args.confirm, manager_exe=manager
            )
        else:
            result = request_custom_mod_import(
                args.import_custom_mod, confirmed_by_user=args.confirm,
                manager_exe=manager,
            )
    except ModHandoffError as exc:
        print(f"LTK handoff unavailable: {exc}", file=sys.stderr)
        return 2

    print(result)
    print(
        "The official manager controls import review, mod health, enabling and "
        "patcher start. This is NOT confirmation of a skin applying in-game."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
