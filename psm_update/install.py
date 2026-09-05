from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import psutil

from utils.core.paths import get_user_data_dir

LEAGUE_PROCESS_NAMES = {
    "leagueclient.exe",
    "leagueclientux.exe",
    "leagueclientuxrender.exe",
    "league of legends.exe",
}


def league_is_running() -> bool:
    for process in psutil.process_iter(["name"]):
        try:
            name = (process.info.get("name") or "").lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if name in LEAGUE_PROCESS_NAMES:
            return True
    return False


def install_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


def runtime_cslol_path(app_dir: Path | None = None) -> Path:
    root = app_dir or install_root()
    return root / "_internal" / "injection" / "tools" / "cslol-dll.dll"


def update_root() -> Path:
    root = get_user_data_dir() / "updates"
    root.mkdir(parents=True, exist_ok=True)
    return root


def create_apply_script(
    installer_path: Path,
    current_version: str,
    target_version: str,
) -> Path:
    app_dir = install_root()
    updates = update_root()
    backup = updates / "backup" / current_version
    preserved = updates / "preserved"
    preserved.mkdir(parents=True, exist_ok=True)
    preserved_cslol = preserved / "cslol-dll.dll"
    cslol = runtime_cslol_path(app_dir)
    helper = updates / "apply_update.cmd"
    app_exe = app_dir / "PersonalSkinManager.exe"

    content = rf"""@echo off
setlocal EnableExtensions
set "PSM_PID={os.getpid()}"
set "APP_DIR={app_dir}"
set "INSTALLER={installer_path}"
set "BACKUP={backup}"
set "CSLOL={cslol}"
set "PRESERVED_CSLOL={preserved_cslol}"
set "APP_EXE={app_exe}"

:wait_for_exit
tasklist /FI "PID eq %PSM_PID%" 2>NUL | find "%PSM_PID%" >NUL
if not errorlevel 1 (
  timeout /t 1 /nobreak >NUL
  goto wait_for_exit
)

if exist "%BACKUP%" rmdir /S /Q "%BACKUP%"
mkdir "%BACKUP%" >NUL 2>&1
robocopy "%APP_DIR%" "%BACKUP%" /MIR /NFL /NDL /NJH /NJS /NP >NUL

if exist "%CSLOL%" copy /Y "%CSLOL%" "%PRESERVED_CSLOL%" >NUL

start /wait "" "%INSTALLER%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
set "INSTALL_RC=%ERRORLEVEL%"
if not "%INSTALL_RC%"=="0" goto rollback

if exist "%PRESERVED_CSLOL%" (
  if not exist "%APP_DIR%\_internal\injection\tools" mkdir "%APP_DIR%\_internal\injection\tools" >NUL 2>&1
  copy /Y "%PRESERVED_CSLOL%" "%APP_DIR%\_internal\injection\tools\cslol-dll.dll" >NUL
)

start "" "%APP_EXE%"
timeout /t 20 /nobreak >NUL

tasklist /FI "IMAGENAME eq PersonalSkinManager.exe" 2>NUL | find /I "PersonalSkinManager.exe" >NUL
if errorlevel 1 goto rollback_after_launch
exit /b 0

:rollback_after_launch
taskkill /IM PersonalSkinManager.exe /F >NUL 2>&1

:rollback
if exist "%BACKUP%" robocopy "%BACKUP%" "%APP_DIR%" /MIR /NFL /NDL /NJH /NJS /NP >NUL
if exist "%PRESERVED_CSLOL%" (
  if not exist "%APP_DIR%\_internal\injection\tools" mkdir "%APP_DIR%\_internal\injection\tools" >NUL 2>&1
  copy /Y "%PRESERVED_CSLOL%" "%APP_DIR%\_internal\injection\tools\cslol-dll.dll" >NUL
)
if exist "%APP_EXE%" start "" "%APP_EXE%"
exit /b %INSTALL_RC%
"""
    helper.write_text(content, encoding="utf-8", newline="\r\n")
    return helper


def schedule_verified_installer(
    installer_path: Path,
    current_version: str,
    target_version: str,
) -> Path:
    if league_is_running():
        raise RuntimeError("League is running; update installation must be deferred")

    helper = create_apply_script(installer_path, current_version, target_version)
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    subprocess.Popen(
        ["cmd.exe", "/d", "/c", str(helper)],
        cwd=str(helper.parent),
        creationflags=creationflags,
        close_fds=True,
    )
    return helper
