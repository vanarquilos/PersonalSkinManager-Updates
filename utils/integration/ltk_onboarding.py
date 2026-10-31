"""Native startup guidance for missing or expired user-provided LTK runtime.

Follows Rose's supported user-supplied patcher workflow. Never downloads,
replaces, injects, or modifies external binaries or security settings.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from injection.tools.patcher import check_ltk_patcher, read_game_build


def explain_ltk_runtime_problem(tools_dir: Path, game_dir: Optional[Path] = None) -> Optional[str]:
    """Return a specific recovery instruction, or None when no problem is known."""
    status = check_ltk_patcher(tools_dir)
    if status.missing:
        return (
            "LTK patcher files are missing or failed integrity verification.\n\n"
            "PSM needs a matching, trusted ltk_patcher_host.exe and "
            "ltk_patcher_dll.dll. Use the documented local provisioning workflow."
        )
    if status.expired_for(game_dir):
        cutoff = datetime.fromtimestamp(status.eol).strftime("%Y-%m-%d")
        game_timestamp = read_game_build(game_dir) if game_dir is not None else None
        game_date = (
            datetime.fromtimestamp(game_timestamp).strftime("%Y-%m-%d")
            if game_timestamp is not None else "unknown"
        )
        return (
            "The installed LTK DLL is TOO OLD for this League build.\n\n"
            f"LTK DLL cutoff: {cutoff}\n"
            f"League executable build: {game_date}\n\n"
            "Replace BOTH LTK host and DLL with a supported, trusted pair "
            "and restart Personal Skin Manager. Rebuilding PSM with this old "
            "DLL cannot make skins work. Do not disable game security checks."
        )
    return None


def notify_user_provided_ltk_missing(tools_dir: Path) -> bool:
    """Give one native guidance message at installed startup; never installs files.

    A missing/expired runtime is still rejected by ToolsManager later, even
    if this dialog is dismissed. PSM's non-injection features remain usable.
    """
    try:
        from config import get_config_option
        league_path = get_config_option("General", "leaguePath")
        game_dir = None
        if league_path:
            # The configured path may be the League installation root;
            # the real game executable is commonly in its Game child.
            base = Path(league_path)
            for candidate in (base, base / "Game"):
                if read_game_build(candidate) is not None:
                    game_dir = candidate
                    break
    except Exception:
        game_dir = None
    problem = explain_ltk_runtime_problem(tools_dir, game_dir)
    if problem is None:
        return True
    if sys.platform != "win32":
        return False

    try:
        import ctypes
        MB_YESNO = 0x00000004
        MB_ICONWARNING = 0x00000030
        IDYES = 6
        detail = (
            problem
            + "\n\nPSM does not distribute LTK's signed patcher. "
              "Obtain the current official pair from LTK Manager, verify "
              "its signature and SHA-256, then use the included "
              "tools\\import_user_ltk_v105.ps1. See docs\\USER_LTK_SETUP.md.\n\n"
              "Open the local PSM setup-tools folder? No files will be changed."
        )
        answer = ctypes.windll.user32.MessageBoxW(
            None, detail, "Personal Skin Manager - LTK runtime incompatible",
            MB_YESNO | MB_ICONWARNING,
        )
        if answer == IDYES:
            # Open the shipped provisioning scripts, not an unrelated Rose
            # folder or a protected binary directory that lacks the script.
            script_dir = Path(sys.executable).resolve().parent / "tools"
            destination = script_dir if script_dir.is_dir() else tools_dir
            if destination.is_dir():
                os.startfile(str(destination))
    except (AttributeError, OSError):
        pass
    return False
