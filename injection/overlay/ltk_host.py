#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTK patcher-host adapter.

This module intentionally does not bundle or download League Toolkit binaries.
For development QA, ltk_patcher_host.exe and ltk_patcher_dll.dll must already
exist in PSM's injection/tools directory.

Patch 26.19 / Rose parity requires a two-stage lifecycle:

1. start the LTK host and begin scanning BEFORE League is allowed to launch;
2. build + rebase the overlay while PSM temporarily holds the game;
3. resume League only when the overlay is ready.

The current LTK DLL can report a "joined too late" condition if the game was
already running before scanning started. That condition is treated as a hard
injection failure instead of a false success.
"""

from __future__ import annotations

import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

try:
    import psutil
except ImportError:
    psutil = None

from utils.core.logging import get_logger
from utils.core.issue_reporter import report_issue
from ..tools.patcher import (
    LTK_PATCHER_DLL,
    LTK_PATCHER_HOST,
    check_ltk_patcher,
)
from config import (
    PROCESS_MONITOR_SLEEP_S,
    PROCESS_TERMINATE_TIMEOUT_S,
    LTK_ELEVATE_INJECTOR,
)

log = get_logger()

LTK_HOST_NAME = LTK_PATCHER_HOST
LTK_DLL_NAME = LTK_PATCHER_DLL

# Match Rose 1.3.1 / latest main patcher-host configuration.
# Info=0x10. Flag 4 = CSLOL_HOOK_OPT_OUT_AH_V1, which disables the
# base-skin anti-skinhack enforcement that rejects Rose's generic skin0 carrier.
LTK_PATCHER_LOG_LEVEL = 0x10
LTK_PATCHER_DEBUG_LOG_LEVEL = 0x20


def _runtime_log_level() -> int:
    """Ask LTK for DEBUG records only in local Python --debug sessions.

    The upstream host marks redirection and material details at varying
    verbosity. Release builds retain the existing INFO level and no paths
    from DLL records are written to the normal PSM log.
    """
    if not getattr(sys, "frozen", False) and "--debug" in sys.argv:
        return LTK_PATCHER_DEBUG_LOG_LEVEL
    return LTK_PATCHER_LOG_LEVEL
LTK_PATCHER_FLAGS = 4

# Backward-compatible alias for older PSM tests/imports.
LTK_DEFAULT_FLAGS = LTK_PATCHER_FLAGS
LATE_JOIN_MESSAGE = "joined too late"
END_OF_LIFE_MESSAGE = "end of life reached"

_SUCCESS_STATES = {"injected"}
_FAILURE_STATES = {"failed"}
# Keep both current League game process names, as in Rose's live lifecycle.
_LEAGUE_GAME_NAMES = frozenset(
    ("league of legends.exe", "league of legends (tm) client.exe")
)


def _league_game_process_running() -> bool:
    """Check the actual League game, not the client's potentially stale phase.

    When the client disconnects or reports post-game prematurely, stopping
    the LTK host can leave the game running without its overlay.
    """
    if psutil is None:
        return False
    try:
        for process in psutil.process_iter(["name"]):
            if (process.info.get("name") or "").casefold() in _LEAGUE_GAME_NAMES:
                return True
    except (psutil.Error, OSError):
        # We cannot establish that the game is still running; defer to the
        # existing stop callback instead of leaving an orphaned host.
        log.debug("[INJECT][ltk-host] Could not check League game process")
    return False


def _should_stop_after_callback(stop_requested: bool) -> bool:
    """Only stop on a client-phase transition once League itself has exited."""
    return stop_requested and not _league_game_process_running()


def _skin_redirect_not_observed(result: "LtkHostResult") -> bool:
    """Reject the false-positive state: active overlay but no WAD served."""
    return result.attached and result.overlay_initialized and result.redirected_wads == 0



class LtkHostResult:
    def __init__(self) -> None:
        self.attached = False
        self.last_state: Optional[str] = None
        self.failure: Optional[str] = None
        self.dll_lines = 0
        # None means no verification verdict was observed, not zero WADs.
        self.verified_wads: Optional[int] = None
        self.redirected_wads = 0
        # Upstream emits `init done` when its DLL overlay is initialized.
        # This is separate from the host's `injected` attachment state.
        self.overlay_initialized = False


class LtkHostSession:
    def __init__(
        self,
        proc: subprocess.Popen,
        events: queue.Queue,
        result: LtkHostResult,
        process_manager=None,
    ) -> None:
        self.proc = proc
        self.events = events
        self.result = result
        self.process_manager = process_manager
        self.started_at = time.time()


def _send_line(proc: subprocess.Popen, line: str) -> None:
    if proc.stdin is None:
        raise RuntimeError("LTK patcher host stdin is unavailable")
    proc.stdin.write(line + "\n")
    proc.stdin.flush()
    log.debug(f"[INJECT][ltk-host] >> {line}")


def _reader(pipe, stream_name: str, event_queue: queue.Queue) -> None:
    try:
        for raw_line in pipe:
            line = raw_line.rstrip("\r\n")
            if line:
                event_queue.put((stream_name, line))
    except Exception as exc:
        event_queue.put(("reader-error", f"{stream_name}: {exc}"))


def _report_overlay_rejected(line: str) -> None:
    report_issue(
        "LTK_OVERLAY_REJECTED",
        "error",
        "Current LTK runtime still disabled the Rose overlay.",
        details={
            "backend": "ltk",
            "flags": LTK_PATCHER_FLAGS,
            "verdict": line,
        },
        hint=(
            "Stop repeated match attempts and send the latest Rose log. "
            "The current runtime attached, but the overlay was disabled."
        ),
        dedupe_window_s=30.0,
    )


def _parse_stdout(line: str, result: LtkHostResult) -> None:
    parts = line.split(" ", 3)
    keyword = parts[0].lower() if parts else ""

    if keyword == "status" and len(parts) >= 3:
        state = parts[2].lower()
        message = parts[3] if len(parts) >= 4 else ""
        result.last_state = state
        if state in _SUCCESS_STATES:
            result.attached = True
        elif state in _FAILURE_STATES:
            result.failure = message or "LTK patcher host reported a failed state"
        log.info(
            f"[INJECT][ltk-host] status={state}"
            + (f" | {message}" if message else "")
        )
        return

    if keyword == "dll":
        result.dll_lines += 1
        lower = line.lower()

        if END_OF_LIFE_MESSAGE in lower:
            result.failure = (
                "the current LTK patcher DLL reached its built-in end-of-life date"
            )
            log.error(
                "[INJECT][ltk-host] LTK patcher DLL reached end of life; "
                "update the runtime before retrying"
            )
            return

        if LATE_JOIN_MESSAGE in lower:
            result.failure = (
                "the game started before the LTK scanner was ready; overlay was not applied"
            )
            log.error(
                "[INJECT][ltk-host] LTK joined the game too late - overlay was not applied"
            )
            return

        # Record positive overlay evidence at INFO without logging paths or
        # requiring upstream DEBUG output. An attached host alone does not
        # demonstrate that any modded WAD was actually used by the game.
        verified = re.search(r"overlay verified\s+(\d+)\s+wad", lower)
        if verified is not None:
            result.verified_wads = int(verified.group(1))
            log.info(
                "[INJECT][ltk-host] overlay verified %d WAD(s)",
                result.verified_wads,
            )
            return

        if "redirected wad:" in lower:
            result.redirected_wads += 1
            if result.redirected_wads == 1:
                log.info("[INJECT][ltk-host] WAD redirection observed")
            return

        # Upstream uses "init done" for a live DLL overlay, which is distinct
        # from the host's earlier "injected" attachment state.
        if re.search(r"(?:^|:\s+|\s+)init done\s*$", lower):
            result.overlay_initialized = True
            log.info("[INJECT][ltk-host] DLL overlay initialization confirmed")
            return

        # Rose issue #404 (League 26.21): a vendor host-verification
        # refusal is a terminal runtime verdict, not successful injection.
        # Report only its category; do not leak vendor proof or host details.
        if "host verification failed" in lower and "refusing overlay" in lower:
            result.failure = "LTK host verification refused the overlay"
            log.error(
                "[INJECT][ltk-host] LTK host verification refused the overlay; "
                "third-party host integration is not vendor-supported"
            )
            report_issue(
                "LTK_HOST_VERIFICATION_FAILED",
                "error",
                "The LTK patcher refused its host verification; no skin was applied.",
                details={"backend": "ltk", "stage": "host_verification"},
                hint=(
                    "The current vendor patcher may reject third-party hosts. "
                    "Seek an authorized integration or supported backend; "
                    "do not bypass vendor integrity or game security verification."
                ),
                dedupe_window_s=30.0,
            )
            return

        # Fail visibly for distinct upstream overlay rejection signatures.
        if "lazy verification failed, not overlaying:" in lower:
            result.failure = "LTK declined a WAD because lazy verification failed"
            log.error("[INJECT][ltk-host] LTK did not apply the overlay: WAD verification failed")
            return

        if "failed to install " in lower and " hook" in lower:
            result.failure = "LTK failed to install a required game hook"
            log.error("[INJECT][ltk-host] LTK could not initialize a required hook")
            return

        if "overlay verification failed, disabling overlay" in lower:
            result.failure = line
            log.error(f"[INJECT][ltk-host] {line}")
            _report_overlay_rejected(line)
            return

        if "wad scan failed" in lower:
            # A WARN is an observation; an ERROR is a rejection verdict.
            if re.search(r"\bERROR\b", line):
                result.failure = "LTK WAD integrity scan reported an error"
                log.error("[INJECT][ltk-host] LTK WAD integrity scan failed")
            else:
                log.warning("[INJECT][ltk-host] LTK reported a WAD scan warning")
            return

        log.debug(f"[INJECT][ltk-host] {line}")
        return

    if keyword == "error":
        message = parts[2] if len(parts) >= 3 else line
        if len(parts) >= 4:
            message = f"{parts[2]} {parts[3]}"
        result.failure = message
        log.error(f"[INJECT][ltk-host] {line}")
        return

    if keyword == "ok":
        log.debug(f"[INJECT][ltk-host] {line}")
        return

    log.debug(f"[INJECT][ltk-host] {line}")


def _drain_events(event_queue: queue.Queue, result: LtkHostResult) -> None:
    while True:
        try:
            stream_name, line = event_queue.get_nowait()
        except queue.Empty:
            return

        if stream_name == "stdout":
            _parse_stdout(line, result)
        elif stream_name == "stderr":
            log.warning(f"[INJECT][ltk-host][stderr] {line}")
        else:
            log.debug(f"[INJECT][ltk-host] {line}")


def _shutdown_host(proc: subprocess.Popen, request_stop: bool = True) -> None:
    if proc.poll() is not None:
        return

    if request_stop:
        try:
            _send_line(proc, "stop")
        except Exception as exc:
            log.debug(f"[INJECT][ltk-host] Could not send stop: {exc}")

    try:
        if proc.stdin is not None:
            proc.stdin.close()
    except Exception:
        pass

    try:
        proc.wait(timeout=PROCESS_TERMINATE_TIMEOUT_S)
        return
    except subprocess.TimeoutExpired:
        pass

    try:
        proc.terminate()
        proc.wait(timeout=PROCESS_TERMINATE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def start_ltk_patcher_host(
    tools_dir: Path,
    overlay_dir: Path,
    process_manager=None,
    game_dir: Optional[Path] = None,
) -> Optional[LtkHostSession]:
    """Start/configure LTK and begin scanning before League is resumed."""

    patcher = check_ltk_patcher(tools_dir)
    host_exe = patcher.host
    hook_dll = patcher.dll

    if patcher.missing:
        log.error(
            "[INJECT][ltk-host] Missing LTK runtime file(s): %s",
            ", ".join(patcher.missing),
        )
        report_issue(
            "LTK_PATCHER_MISSING",
            "error",
            "Injection failed: required LTK runtime files are missing.",
            details={"missing": patcher.missing, "tools_dir": str(tools_dir)},
            hint="Restore the current PSM runtime files, then retry.",
            dedupe_window_s=30.0,
        )
        return None

    if patcher.expired_for(game_dir):
        eol_text = time.strftime("%Y-%m-%d %H:%M", time.localtime(patcher.eol))
        log.error(
            "[INJECT][ltk-host] LTK patcher DLL does not support this League build "
            "(build cutoff %s)",
            eol_text,
        )
        report_issue(
            "LTK_PATCHER_EOL",
            "error",
            "Injection failed: the current LTK runtime does not support this League build.",
            details={
                "eol": patcher.eol,
                "eol_local": eol_text,
                "game_dir": str(game_dir) if game_dir is not None else None,
            },
            hint="Update PSM's LTK runtime before starting another match.",
            dedupe_window_s=30.0,
        )
        return None

    overlay_prefix = str(overlay_dir.resolve())
    if not overlay_prefix.endswith(os.sep):
        overlay_prefix += os.sep

    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    cmd = [str(host_exe)]
    if sys.platform == "win32" and LTK_ELEVATE_INJECTOR:
        cmd.append("--elevate")

    log.info(
        "[INJECT] Starting LTK patcher-host scanner before game launch"
        + (" with elevation" if "--elevate" in cmd else " in normal mode")
    )
    log.info(
        "[INJECT] Rose-compatible LTK patcher configuration active "
        "(flags=%d, anti-skinhack base-skin enforcement disabled)",
        LTK_PATCHER_FLAGS,
    )

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(tools_dir),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )

        if process_manager is not None:
            process_manager.current_overlay_process = proc

        events: queue.Queue = queue.Queue()
        result = LtkHostResult()

        threading.Thread(
            target=_reader,
            args=(proc.stdout, "stdout", events),
            daemon=True,
            name="LtkHostStdout",
        ).start()
        threading.Thread(
            target=_reader,
            args=(proc.stderr, "stderr", events),
            daemon=True,
            name="LtkHostStderr",
        ).start()

        selected_log_level = _runtime_log_level()
        log.info(
            "[INJECT][ltk-host] DLL log level: %s",
            "DEBUG (local source QA)" if selected_log_level == LTK_PATCHER_DEBUG_LOG_LEVEL else "INFO",
        )
        _send_line(proc, f"config loglevel {selected_log_level}")
        _send_line(proc, f"config flags {LTK_PATCHER_FLAGS}")
        _send_line(proc, f"config prefix {overlay_prefix}")
        _send_line(proc, "start scan")

        # Give the host a brief opportunity to acknowledge configuration. Do not
        # wait for a game here; the whole point is to have scanning active before
        # League is resumed.
        acknowledge_deadline = time.time() + 1.0
        while time.time() < acknowledge_deadline and proc.poll() is None:
            _drain_events(events, result)
            if result.failure:
                break
            if result.last_state == "injecting":
                break
            time.sleep(0.02)

        if proc.poll() is not None or result.failure:
            if result.failure:
                log.error(
                    "[INJECT][ltk-host] Scanner failed before game launch: %s",
                    result.failure,
                )
            else:
                log.error(
                    "[INJECT][ltk-host] Scanner exited before game launch (code=%s)",
                    proc.returncode,
                )
            _shutdown_host(proc)
            if process_manager is not None:
                process_manager.current_overlay_process = None
            return None

        log.info("[INJECT][ltk-host] Scanner armed before League launch")
        return LtkHostSession(proc, events, result, process_manager)

    except Exception as exc:
        log.error(f"[INJECT][ltk-host] Could not start scanner: {exc}")
        if proc is not None:
            _shutdown_host(proc)
        if process_manager is not None:
            process_manager.current_overlay_process = None
        return None


def abort_ltk_patcher_host(session: Optional[LtkHostSession]) -> None:
    """Stop a pre-started scanner when overlay preparation fails."""
    if session is None:
        return
    try:
        _shutdown_host(session.proc)
    finally:
        if session.process_manager is not None:
            session.process_manager.current_overlay_process = None


def run_ltk_patcher_host_session(
    session: LtkHostSession,
    stop_callback: Optional[Callable[[], bool]] = None,
    injection_manager=None,
) -> int:
    """Resume League after the overlay is ready and mirror Rose's host lifecycle.

    Rose keeps the patcher host scanning across game-process exits so reconnects
    can be hooked again. Explicit DLL/host failures are terminal; a transient
    "exited" state is not.
    """

    proc = session.proc
    result = session.result
    events = session.events
    game_ended = False
    early_client_end_logged = False

    try:
        _drain_events(events, result)
        if result.failure:
            log.error(
                "[INJECT][ltk-host] Scanner failed before game resume: %s",
                result.failure,
            )
            _shutdown_host(proc)
            return 2

        if injection_manager is not None:
            log.info(
                "[INJECT] Overlay ready and LTK scanner armed - resuming League now"
            )
            injection_manager.resume_game()

        while proc.poll() is None:
            _drain_events(events, result)

            if result.failure:
                log.error(f"[INJECT][ltk-host] Injection failed: {result.failure}")
                break

            # Match Rose 1.3.1: "exited" only means the current game process
            # closed. Keep the host alive so a reconnect can be scanned/hooked.
            stop_requested = bool(stop_callback and stop_callback())
            if _should_stop_after_callback(stop_requested):
                log.info("[INJECT] League game process exited; stopping LTK patcher host")
                game_ended = True
                break
            if stop_requested and not early_client_end_logged:
                # Rose main guards this exact race: the client may disconnect
                # or close while League is still loading or in a live match.
                log.info(
                    "[INJECT][ltk-host] Client phase ended while League game "
                    "is still running; keeping overlay host alive"
                )
                early_client_end_logged = True
            elif not stop_requested:
                early_client_end_logged = False

            time.sleep(PROCESS_MONITOR_SLEEP_S)

        _shutdown_host(proc)
        _drain_events(events, result)

        if getattr(session.process_manager, "stopped_by_user", False):
            log.info("[INJECT] LTK patcher stopped by the user")
            return 0

        if result.failure:
            log.error(f"[INJECT][ltk-host] LTK patcher failed: {result.failure}")
            return 2

        if not game_ended and proc.returncode not in (0, None):
            log.error(f"[INJECT][ltk-host] Host exited with code {proc.returncode}")
            return proc.returncode

        log.info(
            "[INJECT][ltk-host] Rose-compatible session completed "
            f"(last_state={result.last_state}, injected={result.attached}, "
            f"dll_lines={result.dll_lines}, verified_wads={result.verified_wads}, "
            f"redirected_wads={result.redirected_wads})"
        )
        log.info(
            "[INJECT][ltk-host] DLL overlay initialization observed: %s",
            result.overlay_initialized,
        )
        if result.attached and not result.overlay_initialized and result.redirected_wads == 0:
            log.warning(
                "[INJECT][ltk-host] Game attachment observed but overlay activation "
                "was not confirmed by the DLL. Skin rendering remains unverified."
            )

        # A skin mod in PSM includes at least one WAD. The upstream runtime
        # distinguishes an initialized overlay from an archive actually served.
        # Do not mark the user's skin as successfully applied when not a single
        # redirection event was observed. Never relax integrity checks to force
        # the redirect.
        if _skin_redirect_not_observed(result):
            log.warning(
                "[INJECT][ltk-host] No WAD redirection confirmed during game. "
                "Skin application not verified."
            )
            report_issue(
                "LTK_NO_WAD_REDIRECTION",
                "warning",
                "Skin not confirmed: patcher initialized but served no recorded modded WAD.",
                details={
                    "dll_events": result.dll_lines,
                    "verified_wads": result.verified_wads,
                    "overlay_initialized": result.overlay_initialized,
                },
                hint="Check the selected mod archive's WAD path and compare it to the installed League WAD.",
                dedupe_window_s=60.0,
            )
            return 3
        return 0

    except Exception as exc:
        log.error(f"[INJECT][ltk-host] Backend error: {exc}")
        if proc.poll() is None:
            _shutdown_host(proc)
        return 1
    finally:
        if session.process_manager is not None:
            session.process_manager.current_overlay_process = None
        if proc.poll() is None:
            _shutdown_host(proc)
        elapsed = time.time() - session.started_at
        log.debug(f"[INJECT][ltk-host] Backend finished after {elapsed:.2f}s")

def run_ltk_patcher_host(
    tools_dir: Path,
    overlay_dir: Path,
    stop_callback: Optional[Callable[[], bool]] = None,
    process_manager=None,
    injection_manager=None,
    game_dir: Optional[Path] = None,
) -> int:
    """Compatibility wrapper for callers that do not pre-start the scanner."""
    session = start_ltk_patcher_host(
        tools_dir,
        overlay_dir,
        process_manager=process_manager,
        game_dir=game_dir,
    )
    if session is None:
        return 1
    return run_ltk_patcher_host_session(
        session,
        stop_callback=stop_callback,
        injection_manager=injection_manager,
    )
