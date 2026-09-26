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
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from utils.core.logging import get_logger
from utils.core.issue_reporter import report_issue
from config import (
    PROCESS_MONITOR_SLEEP_S,
    PROCESS_TERMINATE_TIMEOUT_S,
    LTK_ELEVATE_INJECTOR,
)

log = get_logger()

LTK_HOST_NAME = "ltk_patcher_host.exe"
LTK_DLL_NAME = "ltk_patcher_dll.dll"

# Upstream LTK Manager uses Info=0x10 and Debug=0x20.
LTK_LOGLEVEL_DEBUG = 0x20

# Release builds keep the current runtime's verification path enabled.
LTK_DEFAULT_FLAGS = 0

LTK_ATTACH_TIMEOUT_S = 30.0
LATE_JOIN_MESSAGE = "joined too late"

_SUCCESS_STATES = {"injected", "waiting"}
_FAILURE_STATES = {"failed"}


class LtkHostResult:
    def __init__(self) -> None:
        self.attached = False
        self.last_state: Optional[str] = None
        self.failure: Optional[str] = None
        self.dll_lines = 0


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
            "flags": LTK_DEFAULT_FLAGS,
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

        if LATE_JOIN_MESSAGE in lower:
            result.failure = (
                "the game started before the LTK scanner was ready; overlay was not applied"
            )
            log.error(
                "[INJECT][ltk-host] LTK joined the game too late - overlay was not applied"
            )
            return

        if "overlay verification failed, disabling overlay" in lower:
            result.failure = line
            log.error(f"[INJECT][ltk-host] {line}")
            _report_overlay_rejected(line)
            return

        if "wad scan failed" in lower:
            log.warning(f"[INJECT][ltk-host] {line}")
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
) -> Optional[LtkHostSession]:
    """Start/configure LTK and begin scanning before League is resumed."""

    host_exe = tools_dir / LTK_HOST_NAME
    hook_dll = tools_dir / LTK_DLL_NAME

    if not host_exe.is_file() or not hook_dll.is_file():
        log.error(
            "[INJECT][ltk-host] Missing LTK runtime pair. Expected "
            f"{host_exe} and {hook_dll}"
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
        "[INJECT] LTK runtime verification enabled (flags=%d)",
        LTK_DEFAULT_FLAGS,
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

        _send_line(proc, f"config loglevel {LTK_LOGLEVEL_DEBUG}")
        _send_line(proc, f"config flags {LTK_DEFAULT_FLAGS}")
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
    """Resume League only after the overlay is ready, then monitor LTK."""

    proc = session.proc
    result = session.result
    events = session.events

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

        attach_deadline = time.time() + LTK_ATTACH_TIMEOUT_S

        while proc.poll() is None:
            _drain_events(events, result)

            if result.failure:
                log.error(f"[INJECT][ltk-host] Injection failed: {result.failure}")
                _shutdown_host(proc)
                return 2

            # Do not treat "exited" as terminal by itself. Current Rose keeps the
            # host scanning so reconnects can be hooked again. The game-phase
            # callback decides when the full session is over.
            if stop_callback and stop_callback():
                log.info("[INJECT] Game session ended, stopping LTK patcher host")
                _shutdown_host(proc)
                _drain_events(events, result)
                if result.attached:
                    log.info(
                        "[INJECT][ltk-host] Session completed after confirmed attach "
                        f"(state={result.last_state}, dll_lines={result.dll_lines})"
                    )
                    return 0
                log.error(
                    "[INJECT][ltk-host] Session ended without a confirmed attach "
                    f"(last_state={result.last_state})"
                )
                return 3

            if not result.attached and time.time() >= attach_deadline:
                log.error(
                    "[INJECT][ltk-host] Timed out waiting for current LTK attach "
                    f"after {LTK_ATTACH_TIMEOUT_S:.0f}s "
                    f"(last_state={result.last_state})"
                )
                _shutdown_host(proc)
                return 124

            time.sleep(PROCESS_MONITOR_SLEEP_S)

        _drain_events(events, result)
        if result.failure:
            log.error(f"[INJECT][ltk-host] Host failure: {result.failure}")
            return 2
        if proc.returncode not in (0, None):
            log.error(f"[INJECT][ltk-host] Host exited with code {proc.returncode}")
            return proc.returncode
        if result.attached:
            return 0

        log.error(
            "[INJECT][ltk-host] Host exited without confirming injection "
            f"(last_state={result.last_state})"
        )
        return 3

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
) -> int:
    """Compatibility wrapper for callers that do not pre-start the scanner."""
    session = start_ltk_patcher_host(
        tools_dir,
        overlay_dir,
        process_manager=process_manager,
    )
    if session is None:
        return 1
    return run_ltk_patcher_host_session(
        session,
        stop_callback=stop_callback,
        injection_manager=injection_manager,
    )
