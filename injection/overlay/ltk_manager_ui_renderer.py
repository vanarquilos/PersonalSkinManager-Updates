"""Experimental external rendering adapter using official LTK Manager's own UI.

LTK Manager 1.33.0 publicly supports named profiles, enabled mods and a Start
button (or library Ctrl+P hotkey). PSM selects a preconfigured profile using
Windows accessibility, then presses the *official* Start control. The vendor
still decides mod eligibility and performs every patch operation.

This is NOT a DLL injector, an LTK internal API client, nor a guarantee that
the selected skin actually rendered. It needs native Windows/League QA.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Mapping, Optional

from utils.core.logging import get_logger

log = get_logger()
PROCESS_NAME = "ltk-manager.exe"
DATA_FOLDER = "dev.leaguetoolkit.manager"


class ManagerUIError(RuntimeError):
    """A user-visible failure before confirmed patcher startup."""


@dataclass(frozen=True)
class LibraryProfile:
    profile_id: str
    name: str
    enabled_mods: tuple[str, ...]


@dataclass(frozen=True)
class ManagerSession:
    selected_profile: str
    previous_profile: str
    started_by_psm: bool
    manager_started_by_psm: bool


def installed_manager(env: Optional[Mapping[str, str]] = None) -> Optional[Path]:
    """Find an installed app, without opening or changing anything."""
    env = env if env is not None else os.environ
    roots = [Path(value) for key in ("ProgramFiles", "LOCALAPPDATA", "ProgramFiles(x86)")
             if (value := env.get(key))]
    for root in roots:
        for location in (root / "LTK Manager" / PROCESS_NAME,
                         root / "Programs" / "LTK Manager" / PROCESS_NAME):
            if location.is_file() and not location.is_symlink():
                return location.resolve()
    return None


def library_path(env: Optional[Mapping[str, str]] = None) -> Path:
    env = env if env is not None else os.environ
    roaming = env.get("APPDATA")
    if not roaming:
        raise ManagerUIError("Windows APPDATA is missing.")
    return Path(roaming) / DATA_FOLDER / "library.json"


def read_library(path: Path) -> tuple[tuple[LibraryProfile, ...], str]:
    """Read only LTK's documented v2 index, never write it behind its back."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ManagerUIError("LTK library index missing/unreadable. Open LTK Manager once.") from exc
    if not isinstance(raw, dict) or raw.get("version") != 2:
        raise ManagerUIError("Unexpected LTK library schema; refusing to guess.")
    profiles = raw.get("profiles")
    active = raw.get("activeProfileId")
    if not isinstance(profiles, list) or not isinstance(active, str):
        raise ManagerUIError("Incomplete LTK profile library.")
    parsed = []
    for row in profiles:
        if not isinstance(row, dict):
            raise ManagerUIError("Invalid profile entry.")
        pid, name, enabled = row.get("id"), row.get("name"), row.get("enabledMods")
        if not isinstance(pid, str) or not isinstance(name, str) or not isinstance(enabled, list):
            raise ManagerUIError("Invalid profile identifier or enabledMods.")
        if any(not isinstance(item, str) for item in enabled):
            raise ManagerUIError("Invalid enabled mod entry.")
        parsed.append(LibraryProfile(pid, name, tuple(enabled)))
    if not any(row.profile_id == active for row in parsed):
        raise ManagerUIError("Active LTK profile ID does not exist.")
    return tuple(parsed), active


def resolve_skin_profile(skin_key: str, mapping_file: Path) -> str:
    """Only use explicit PSM skin -> LTK profile mappings; never guess a skin."""
    try:
        mapping = json.loads(Path(mapping_file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ManagerUIError("PSM-to-LTK profile mapping missing or invalid.") from exc
    if not isinstance(mapping, dict):
        raise ManagerUIError("Mapping must be a JSON object.")
    name = mapping.get(skin_key)
    if not isinstance(name, str) or not name.strip():
        raise ManagerUIError(f"No LTK profile mapped for {skin_key!r}.")
    return name.strip()


class LtkManagerUIRenderer:
    """Drive the public Manager UI only, with user opt-in on Windows.

    Win32 UI Automation element names may change between Manager releases;
    no coordinate clicking, internal Tauri IPC or silent library.json writes.
    """

    def __init__(self, manager_exe: Optional[Path] = None,
                 index_file: Optional[Path] = None):
        self.manager_exe = Path(manager_exe) if manager_exe else installed_manager()
        self.index_file = Path(index_file) if index_file else library_path()
        if self.manager_exe is None or not self.manager_exe.is_file():
            raise ManagerUIError("Official LTK Manager executable is not installed.")
        if self.manager_exe.name.casefold() != PROCESS_NAME:
            raise ManagerUIError("Refusing an unexpected manager executable name.")

    def check_profile(self, profile_name: str) -> LibraryProfile:
        profiles, _ = read_library(self.index_file)
        matches = [p for p in profiles if p.name.casefold() == profile_name.casefold()]
        if len(matches) != 1:
            raise ManagerUIError(f"Expected one LTK profile named {profile_name!r}; found {len(matches)}.")
        if not matches[0].enabled_mods:
            raise ManagerUIError(f"LTK profile {profile_name!r} has no enabled mods to render.")
        return matches[0]

    def _window(self, *, start_manager: bool):
        try:
            import psutil
            from pywinauto import Desktop
        except ImportError as exc:
            raise ManagerUIError(
                "Install the optional Windows UI automation dependency: pywinauto."
            ) from exc
        actual = self.manager_exe.resolve()
        def matching_pids():
            found = set()
            for process in psutil.process_iter(["pid", "exe"]):
                try:
                    path = process.info.get("exe")
                    if path and Path(path).resolve() == actual:
                        found.add(process.info["pid"])
                except (OSError, ValueError, TypeError, psutil.Error):
                    continue
            return found

        started_here = False
        if not matching_pids() and start_manager:
            subprocess.Popen([str(actual)], cwd=str(actual.parent))
            started_here = True
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            pids = matching_pids()
            if pids:
                try:
                    for item in Desktop(backend="uia").windows():
                        if item.process_id() in pids and item.is_visible():
                            return item, started_here
                except Exception:
                    pass
            time.sleep(0.25)
        raise ManagerUIError("LTK Manager window did not become accessible within 20 seconds.")

    @staticmethod
    def _buttons(window) -> list:
        try:
            return [control for control in window.descendants(control_type="Button")
                    if control.is_visible()]
        except Exception as exc:
            raise ManagerUIError("Could not inspect LTK Manager's accessible controls.") from exc

    @classmethod
    def _find_button(cls, window, name: str):
        matches = [item for item in cls._buttons(window)
                   if item.window_text().strip().casefold() == name.casefold()
                   and item.is_enabled()]
        if len(matches) != 1:
            raise ManagerUIError(
                f"Cannot uniquely identify official LTK control {name!r}; "
                f"found {len(matches)}. No click attempted."
            )
        return matches[0]

    @staticmethod
    def _focus_library(window):
        from pywinauto.keyboard import send_keys
        window.set_focus()
        send_keys("^2")  # Official Manager shortcut: app.library
        time.sleep(0.35)

    def _switch_profile(self, window, target_name: str, *, wait_s: float = 5.0):
        profiles, old_id = read_library(self.index_file)
        target = next((p for p in profiles if p.name == target_name), None)
        if target is None:
            raise ManagerUIError(f"LTK profile {target_name!r} was removed.")
        if target.profile_id == old_id:
            return
        active_profile = next(p for p in profiles if p.profile_id == old_id)
        self._focus_library(window)
        self._find_button(window, active_profile.name).click_input()
        time.sleep(0.15)
        self._find_button(window, target_name).click_input()
        deadline = time.monotonic() + wait_s
        while time.monotonic() < deadline:
            _, active = read_library(self.index_file)
            if active == target.profile_id:
                return
            time.sleep(0.15)
        raise ManagerUIError(
            "LTK Manager did not confirm a profile switch in library.json. "
            "Patcher was not started."
        )

    def activate(self, profile_name: str, *, confirmed_by_user: bool = False) -> ManagerSession:
        """Select an existing profile and start LTK's native patcher, once.

        Only invoke after explicit consent to foreground UI automation.
        Starting a patcher is not confirmation of in-game skin rendering.
        """
        if not confirmed_by_user:
            raise ManagerUIError("External Manager control requires explicit consent.")
        if os.name != "nt":
            raise ManagerUIError("This renderer requires Windows.")
        selected = self.check_profile(profile_name)
        profiles, previous_id = read_library(self.index_file)
        previous = next(p for p in profiles if p.profile_id == previous_id)
        window, launched_here = self._window(start_manager=True)
        self._focus_library(window)
        self._switch_profile(window, selected.name)

        # Official library Start and Stop controls. Never blindly toggle
        # Ctrl+P, which could STOP an already-running patcher.
        if any(b.window_text().strip().casefold() == "stop"
               for b in self._buttons(window)):
            raise ManagerUIError(
                "LTK patcher is already running. Stop it through LTK Manager "
                "before PSM switches rendering sessions."
            )
        try:
            self._find_button(window, "Start").click_input()
        except ManagerUIError:
            raise
        except Exception as exc:
            raise ManagerUIError("Official LTK Start button could not be pressed.") from exc

        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if any(b.window_text().strip().casefold() == "stop"
                   for b in self._buttons(window)):
                return ManagerSession(selected.name, previous.name, True, launched_here)
            time.sleep(0.25)
        raise ManagerUIError(
            "LTK Manager did not confirm patcher startup. "
            "Inspect Manager diagnostics; do not resume League on assumption."
        )

    def finish(self, session: ManagerSession):
        """Stop only this adapter's patcher, restore the user's prior profile.

        Does not terminate LTK Manager, even when this adapter opened it.
        """
        if not isinstance(session, ManagerSession) or not session.started_by_psm:
            return
        window, _ = self._window(start_manager=False)
        self._focus_library(window)
        self._find_button(window, "Stop").click_input()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if any(b.window_text().strip().casefold() == "start"
                   for b in self._buttons(window)):
                self._switch_profile(window, session.previous_profile)
                return
            time.sleep(0.25)
        raise ManagerUIError("LTK patcher stop was not confirmed; profile left untouched.")
