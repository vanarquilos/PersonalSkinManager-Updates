#!/usr/bin/env python3
"""Read-only League detection report. Never reveal lockfile contents or LCU tokens."""
from __future__ import annotations

import argparse
from collections import deque
import datetime as dt
import os
import re
from pathlib import Path

KNOWN_CLIENT_ROOTS = (
    Path("C:/Riot Games/League of Legends"),
    Path("C:/Program Files/Riot Games/League of Legends"),
    Path("C:/Program Files (x86)/Riot Games/League of Legends"),
)
CLIENT_PROCESSES = {
    "leagueclient.exe",
    "leagueclientux.exe",
    "leagueclientuxrender.exe",
}
GAME_PROCESSES = {"league of legends.exe", "league of legends (tm) client.exe"}
LOG_MARKERS = {
    "LCU lockfile not ready": "LCU lockfile is not ready",
    "LCU connected": "LCU Connected",
    "LCU websocket connected": "WEBSOCKET CONNECTED",
    "LCU websocket disconnected": "WEBSOCKET DISCONNECTED",
    "League path discovery failed": "Could not detect League paths",
    "Pengu activation failed": "Pengu activation failed",
    "League detected but Pengu unavailable": "League client detected, but Pengu Loader activation failed",
    "Unknown Pengu status": "initial status is unknown",
    "Pengu loader unavailable": "Pengu Loader executable is unavailable",
    "Source privilege marker": "PSM launch privilege:",
    "Frozen host DLL lookup normalized": "External host spawned with standard Windows DLL lookup",
}


def _status(path: Path) -> str:
    try:
        return "present" if path.is_file() else "missing"
    except OSError:
        return "inaccessible"


def gather_install_candidates():
    paths = []
    # The lockfile finder is used only to derive its directory; no bytes are read.
    try:
        from lcu.core.lockfile import find_lockfile
        lockfile = find_lockfile()
        if lockfile:
            paths.append(("locatable LCU lockfile directory", Path(lockfile).parent))
    except Exception:
        pass
    try:
        from injection.config.config_manager import ConfigManager
        config = ConfigManager()
        saved_client = config.load_client_path()
        saved_game = config.load_league_path()
        if saved_client:
            paths.append(("saved client directory", Path(saved_client)))
        if saved_game:
            candidate = Path(saved_game)
            if candidate.name.casefold() == "game":
                candidate = candidate.parent
            paths.append(("saved game parent", candidate))
    except Exception:
        pass
    paths.extend(("standard install candidate", root) for root in KNOWN_CLIENT_ROOTS)
    seen = set()
    for label, root in paths:
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        yield label, root


def inspect_processes() -> tuple[int, int, int]:
    import psutil
    clients = games = inaccessible = 0
    for proc in psutil.process_iter(attrs=["name"]):
        try:
            name = (proc.info.get("name") or "").casefold()
            if name in CLIENT_PROCESSES:
                clients += 1
                try:
                    if not proc.exe():
                        inaccessible += 1
                except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                    inaccessible += 1
            elif name in GAME_PROCESSES:
                games += 1
        except (psutil.Error, OSError):
            continue
    return clients, games, inaccessible


def inspect_log() -> list[str]:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return ["Local Rose logs: environment path unavailable"]
    log_dir = Path(local_appdata) / "Rose" / "logs"
    if not log_dir.is_dir():
        return ["Local Rose logs: unavailable"]
    try:
        logs = sorted(log_dir.glob("rose_*.log*"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return ["Local Rose logs: listing unavailable"]
    if not logs:
        return ["Local Rose logs: none"]
    latest = logs[0]
    age_minutes = max(0, int((dt.datetime.now().timestamp() - latest.stat().st_mtime) / 60))
    result = [f"Latest shared PSM log age (minutes): {age_minutes}"]
    try:
        with latest.open("r", encoding="utf-8", errors="replace") as handle:
            lines = deque(handle, maxlen=8000)
        counts = {label: 0 for label in LOG_MARKERS}
        for line in lines:
            for label, phrase in LOG_MARKERS.items():
                if phrase.casefold() in line.casefold():
                    counts[label] += 1
        for label, n in counts.items():
            result.append(f"Log marker {label}: {n}")
    except OSError:
        result.append("Recent logs: unreadable")
    result.append("Markers can include older attempts; not attributed to this session.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=Path.home() / "Desktop" / "PSM-v1.0.5-league-connection.txt")
    args = parser.parse_args()
    output = [
        "PSM v1.0.5 - read-only League connection diagnostics",
        f"Generated: {dt.datetime.now().astimezone().isoformat(timespec='seconds')}",
        "No passwords, lockfile contents, tokens, usernames or absolute paths recorded.",
    ]
    try:
        clients, games, inaccessible = inspect_processes()
        output.extend([
            f"League client process instances: {clients}",
            f"League game process instances: {games}",
            f"Client EXE path inspection unavailable: {inaccessible}",
        ])
    except Exception as exc:
        output.append(f"Process observation unavailable: {type(exc).__name__}")
    for label, root in gather_install_candidates():
        output.append(
            f"Candidate {label}: client={_status(root / 'LeagueClient.exe')}, "
            f"game={_status(root / 'Game' / 'League of Legends.exe')}, "
            f"lockfile={_status(root / 'lockfile')}"
        )
    output.extend(inspect_log())
    output.append("NOTE: installation files alone do not establish a live LCU connection.")
    args.report.write_text("\n".join(output) + "\n", encoding="utf-8")
    print("\n".join(output))
    print(f"Saved report: {args.report.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
