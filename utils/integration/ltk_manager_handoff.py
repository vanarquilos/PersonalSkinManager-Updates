"""Consent-based handoff of local custom mods to official LTK Manager.

LTK Manager's supported startup argument handling accepts existing .fantome
and .modpkg files and opens its own import UI. This module does NOT start an
LTK patcher, set active mods, control a game, hook a vendor DLL, or report
successful in-game rendering.

Source: LeagueToolkit/ltk-manager src-tauri/src/deep_link/files.rs
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Mapping, Optional, Sequence

CUSTOM_MOD_EXTENSIONS = frozenset({".fantome", ".modpkg"})
_MANAGER_EXE_NAMES = frozenset({"ltk-manager.exe"})


class ModHandoffError(RuntimeError):
    """A local mod cannot be handed off safely."""


def manager_candidates(env: Optional[Mapping[str, str]] = None) -> tuple[Path, ...]:
    """Return conventional Windows install candidates; inspect only, never run."""
    env = os.environ if env is None else env
    roots: list[Path] = []
    for key in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
        raw = env.get(key)
        if raw:
            roots.append(Path(raw))
    candidates: list[Path] = []
    for root in roots:
        candidates.extend((
            root / "LTK Manager" / "ltk-manager.exe",
            root / "Programs" / "LTK Manager" / "ltk-manager.exe",
        ))
    # Avoid returning duplicates if environment roots point at the same folder.
    return tuple(dict.fromkeys(candidates))


def find_manager(env: Optional[Mapping[str, str]] = None) -> Optional[Path]:
    """Locate a conventional official LTK install; no registry writes."""
    for path in manager_candidates(env):
        if path.is_file() and not path.is_symlink():
            return path.resolve()
    return None


def _validated_manager(path: Path) -> Path:
    path = Path(path)
    if (
        path.name.casefold() not in _MANAGER_EXE_NAMES
        or not path.is_file()
        or path.is_symlink()
    ):
        raise ModHandoffError(
            "LTK Manager executable not found at the selected location. "
            "Use the official installed ltk-manager.exe."
        )
    return path.resolve()


def _validated_mod(path: Path) -> Path:
    path = Path(path)
    if path.suffix.casefold() not in CUSTOM_MOD_EXTENSIONS:
        raise ModHandoffError("Only local .fantome and .modpkg files are supported.")
    if not path.is_file() or path.is_symlink():
        raise ModHandoffError("Custom mod file does not exist or is a symlink.")
    return path.resolve()


def request_custom_mod_import(
    mod_file: Path,
    *,
    confirmed_by_user: bool = False,
    manager_exe: Optional[Path] = None,
    launcher=None,
) -> str:
    """Ask installed official LTK Manager to open a custom mod file.

    A human must explicitly authorize each request; never call this from a
    champ-select event, timer, startup or silent background thread. Uses an
    argument vector, never a shell command or file association. LTK Manager
    remains in charge of asking to import, validating and enabling the mod.

    Returns a request status, NOT a verification of import or gameplay.
    """
    if not confirmed_by_user:
        raise ModHandoffError("Explicit user confirmation is required.")
    if sys.platform != "win32":
        raise ModHandoffError("This handoff is supported only on Windows.")
    mod = _validated_mod(mod_file)
    candidate = manager_exe if manager_exe is not None else find_manager()
    if candidate is None:
        raise ModHandoffError(
            "Official LTK Manager installation not found. "
            "Install it first; do not copy its DLLs into PSM."
        )
    manager = _validated_manager(candidate)
    launch = launcher if launcher is not None else subprocess.Popen
    try:
        launch([str(manager), str(mod)], cwd=str(manager.parent))
    except OSError as exc:
        raise ModHandoffError(f"LTK Manager could not be opened: {exc}") from exc
    return "IMPORT_REQUESTED_NOT_VERIFIED"


def request_open_manager(
    *,
    confirmed_by_user: bool = False,
    manager_exe: Optional[Path] = None,
    launcher=None,
) -> str:
    """Open official LTK Manager only after user consent; no patcher actions."""
    if not confirmed_by_user:
        raise ModHandoffError("Explicit user confirmation is required.")
    if sys.platform != "win32":
        raise ModHandoffError("LTK Manager handoff requires Windows.")
    candidate = manager_exe if manager_exe is not None else find_manager()
    if candidate is None:
        raise ModHandoffError("Official LTK Manager installation not found.")
    manager = _validated_manager(candidate)
    launch = launcher if launcher is not None else subprocess.Popen
    try:
        launch([str(manager)], cwd=str(manager.parent))
    except OSError as exc:
        raise ModHandoffError(f"LTK Manager could not be opened: {exc}") from exc
    return "MANAGER_OPEN_REQUESTED_NOT_VERIFIED"
