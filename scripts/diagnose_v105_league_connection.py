#!/usr/bin/env python3
"""Read-only League detection report. Never reveal lockfile contents or LCU tokens."""
from __future__ import annotations

import argparse
import configparser
from collections import deque
import datetime as dt
import os
import sys
from pathlib import Path

# Directly executing "python scripts/diagnose_v105_league_connection.py"
# places scripts/ (not the repository root) on sys.path. The earlier
# ModuleNotFoundError was caused by this diagnostic environment and cannot
# be attributed to the installed PSM executable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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




def inspect_psm_lockfile_discovery() -> list[str]:
    """Check PSM's Python discovery helper without recording credentials."""
    try:
        from lcu.core.lockfile import find_lockfile
    except ModuleNotFoundError as exc:
        # A missing module name is useful and doesn't disclose the LCU secret.
        return ["PSM source LCU diagnostic import: missing module " + str(exc.name or "unknown")]
    except Exception as exc:
        return ["PSM source LCU diagnostic import: unavailable (" + type(exc).__name__ + ")"]
    try:
        selected = find_lockfile()
        return ["PSM LCU lockfile finder: " + ("found" if selected else "not found")]
    except Exception as exc:
        return ["PSM LCU lockfile finder: unavailable (" + type(exc).__name__ + ")"]


def _known_lockfile_candidates():
    """Use filesystem paths only; never print or upload lockfile credentials."""
    override = os.environ.get("LCU_LOCKFILE")
    if override:
        yield Path(override)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        config_path = Path(local) / "Rose" / "config.ini"
        if config_path.is_file():
            try:
                config = configparser.ConfigParser()
                config.read(config_path, encoding="utf-8")
                if config.has_option("General", "clientPath"):
                    yield Path(config.get("General", "clientPath")) / "lockfile"
            except (OSError, configparser.Error, ValueError):
                pass
    for root in KNOWN_CLIENT_ROOTS:
        yield root / "lockfile"


def inspect_live_lcu() -> list[str]:
    """Probe the existing localhost LCU endpoint read-only, never print secrets."""
    lockfile = next((p for p in _known_lockfile_candidates() if p.is_file()), None)
    if lockfile is None:
        return ["Live LCU: lockfile not located"]
    try:
        parts = lockfile.read_text(encoding="utf-8").strip().split(":", 4)
        if len(parts) != 5:
            return ["Live LCU: lockfile format invalid"]
        _, pid_raw, port_raw, password, protocol = parts
        pid, port = int(pid_raw), int(port_raw)
        if protocol not in ("https", "http") or not 1 <= port <= 65535 or not password:
            return ["Live LCU: lockfile endpoint invalid"]
        try:
            import psutil
            active = psutil.pid_exists(pid)
            pid_status = f"Live LCU: lockfile owner process exists: {active}"
        except Exception:
            pid_status = "Live LCU: lockfile process ownership could not be checked"

        # The request is only to the already running local Riot client. Do not
        # follow redirects or capture the returned account/gameflow data.
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session = requests.Session()
        session.trust_env = False
        try:
            response = session.get(
                f"{protocol}://127.0.0.1:{port}/lol-gameflow/v1/gameflow-phase",
                auth=("riot", password),
                timeout=3,
                verify=False,
                allow_redirects=False,
            )
            code = response.status_code
            state = "reachable" if code == 200 else "HTTP error or unexpected response"
            return [pid_status, f"Live LCU API: {state} (HTTP {code})"]
        finally:
            session.close()
    except (OSError, UnicodeError, ValueError):
        return ["Live LCU: lockfile unreadable or invalid"]
    except Exception as exc:
        # requests exceptions may contain full URLs and environment strings.
        # Never print their messages or anything from the lockfile.
        return ["Live LCU API: request failed (" + type(exc).__name__ + ")"]



def inspect_live_websocket() -> list[str]:
    """Read-only WAMP handshake to the local League client; do not log secrets."""
    lockfile = next((p for p in _known_lockfile_candidates() if p.is_file()), None)
    if lockfile is None:
        return ["Live LCU WebSocket: lockfile not located"]
    try:
        import base64
        import ssl
        import websocket

        parts = lockfile.read_text(encoding="utf-8").strip().split(":", 4)
        if len(parts) != 5:
            return ["Live LCU WebSocket: lockfile format invalid"]
        _, _, port_text, password, protocol = parts
        port = int(port_text)
        if not 1 <= port <= 65535 or not password or protocol not in ("https", "http"):
            return ["Live LCU WebSocket: invalid endpoint"]
        scheme = "wss" if protocol == "https" else "ws"
        auth = base64.b64encode(f"riot:{password}".encode("utf-8")).decode("ascii")
        ws = websocket.create_connection(
            f"{scheme}://127.0.0.1:{port}/",
            timeout=3,
            header=[f"Authorization: Basic {auth}"],
            subprotocols=["wamp"],
            origin=f"{protocol}://127.0.0.1:{port}",
            sslopt={"cert_reqs": ssl.CERT_NONE},
            http_proxy_host=None,
            http_proxy_port=None,
            http_no_proxy=["127.0.0.1"],
        )
        try:
            negotiated = ws.getsubprotocol()
            return [
                "Live LCU WebSocket: handshake succeeded"
                + (" (wamp)" if negotiated == "wamp" else " (subprotocol unconfirmed)")
            ]
        finally:
            ws.close()
    except Exception as exc:
        # Errors can contain URLs/auth headers. Only report the exception class.
        return ["Live LCU WebSocket: handshake failed (" + type(exc).__name__ + ")"]



def inspect_psm_process(installed_dir: Path) -> list[str]:
    try:
        import psutil
        expected = (installed_dir / "PersonalSkinManager.exe").resolve()
        found = []
        for proc in psutil.process_iter(attrs=["name"]):
            try:
                if (proc.info.get("name") or "").casefold() != "personalskinmanager.exe":
                    continue
                try:
                    exe = proc.exe()
                    is_installed = bool(exe) and Path(exe).resolve() == expected
                except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                    is_installed = None
                found.append((is_installed, proc.create_time()))
            except (psutil.Error, OSError):
                continue
        records = [f"PSM running processes: {len(found)}"]
        installed_starts = [when for is_installed, when in found if is_installed is True]
        if installed_starts:
            elapsed = max(0, int((dt.datetime.now().timestamp() - max(installed_starts)) / 60))
            records.append(f"Installed PSM process uptime (minutes): {elapsed}")
        if not found:
            records.append("PSM installed process active: no")
        else:
            records.append(
                "PSM installed process active: "
                + ("yes" if any(x[0] is True for x in found)
                   else "unknown" if any(x[0] is None for x in found)
                   else "no (different executable)")
            )
        # Shared logs may contain earlier sessions. This merely identifies
        # whether the newest one was written after the installed app began.
        local = os.environ.get("LOCALAPPDATA")
        if local and found:
            log_dir = Path(local) / "Rose" / "logs"
            try:
                logs = sorted(log_dir.glob("rose_*.log*"),
                              key=lambda f: f.stat().st_mtime, reverse=True)
                if logs:
                    if installed_starts:
                        is_after_launch = logs[0].stat().st_mtime >= max(installed_starts) - 3
                        records.append(
                            "Newest PSM log updated since installed process start: "
                            + str(is_after_launch)
                        )
                        if not is_after_launch:
                            records.append("WARNING: current installed process has no matched startup log.")
            except OSError:
                pass
        return records
    except Exception as exc:
        return ["PSM process visibility: unavailable (" + type(exc).__name__ + ")"]


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
    parser.add_argument("--installed-dir", type=Path, default=Path("C:/Program Files/Personal Skin Manager"))
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
    output.extend(inspect_psm_process(args.installed_dir))
    output.extend(inspect_psm_lockfile_discovery())
    output.extend(inspect_live_lcu())
    output.extend(inspect_live_websocket())
    output.extend(inspect_log())
    output.append("NOTE: local LCU/WS probes do not prove PSM's own WebSocket or Pengu has connected.")
    args.report.write_text("\n".join(output) + "\n", encoding="utf-8")
    print("\n".join(output))
    print(f"Saved report: {args.report.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
