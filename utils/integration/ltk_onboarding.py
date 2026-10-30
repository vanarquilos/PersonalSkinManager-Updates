"""First-launch guidance for user-provided LTK runtime (Rose-style model).

This module never downloads or installs binaries. It only explains why PSM
cannot run without a reviewed user-provided LTK pair and can reveal its
protected tools directory for explicit user provisioning.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from injection.tools.patcher import check_ltk_patcher


def notify_user_provided_ltk_missing(tools_dir: Path) -> bool:
    """Return True when the runtime is ready; optionally show a Windows guide.

    The notification is best-effort; runtime gates continue to fail closed
    even when the user dismisses it.
    """
    status = check_ltk_patcher(tools_dir)
    if not status.missing:
        return True
    if sys.platform != "win32":
        return False

    try:
        import ctypes

        MB_YESNO = 0x00000004
        MB_ICONINFORMATION = 0x00000040
        IDYES = 6
        detail = (
            "Personal Skin Manager requires a user-provided LeagueToolkit "
            "patcher host and DLL.\n\n"
            "PSM does not bundle those files. Obtain an official, unmodified "
            "matching pair from LTK Manager, verify its publisher and SHA-256 "
            "identities, then use PSM's documented "
            "scripts/import_user_ltk_v105.ps1 provisioning workflow.\n\n"
            "The current runtime is missing, incomplete or failed local "
            "integrity checks.\n\n"
            "Open PSM's runtime tools folder in File Explorer? "
            "(No files will be changed.)"
        )
        answer = ctypes.windll.user32.MessageBoxW(
            None, detail, "Personal Skin Manager - LTK runtime required",
            MB_YESNO | MB_ICONINFORMATION,
        )
        if answer == IDYES and tools_dir.is_dir():
            os.startfile(str(tools_dir))
    except (AttributeError, OSError):
        pass
    return False
