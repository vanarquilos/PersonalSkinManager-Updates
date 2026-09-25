#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTK patcher-host adapter.

This module intentionally does not bundle or download League Toolkit binaries.
For development QA, ltk_patcher_host.exe and ltk_patcher_dll.dll must already
exist in PSM's injection/tools directory.

The wire protocol mirrors the public LTK Manager host protocol:
    config loglevel <N>
    config flags <N>
    config prefix <overlay-root-with-trailing-separator>
    start scan
    stop
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
    LTK_ENFORCE_SKINHACK_SCAN,
    LTK_ELEVATE_INJECTOR,
)

log = get_logger()

LTK_HOST_NAME = "ltk_patcher_host.exe"
LTK_DLL_NAME = "ltk_patcher_dll.dll"

# Upstream LTK Manager uses Info=0x10 and Debug=0x20.
LTK_LOGLEVEL_DEBUG = 0x20

# Public upstream hook flags used by LTK Manager.
LTK_OPT_OUT_AH_V1 = 4

# Mirror LTK Manager's own "Enforce anti-skinhack scan" setting:
#   enabled  -> flags 0
#   disabled -> CSLOL_HOOK_OPT_OUT_AH_V1 (4)
# This branch uses the latter for Rose v1.0.1 compatibility QA.
LTK_DEFAULT_FLAGS = 0 if LTK_ENFORCE_SKINHACK_SCAN else LTK_OPT_OUT_AH_V1

# The game should appear immediately after FINALIZATION, but keep this generous
# enough for slow Riot/League startup without turning a wedged host into a hang.
LTK_ATTACH_TIMEOUT_S = 30.0

_SUCCESS_STATES = {"injected", "waiting"}
_TERMINAL_SUCCESS_STATES = {"exited"}
_FAILURE_STATES = {"failed"}


class LtkHostResult:
    def __init__(self) -> None:
        self.attached = False
        self.last_state: Optional[str] = None
        self.failure: Optional[str] = None
        self.dll_lines = 0


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
        # Surface overlay-disable verdicts at error level. The host can stay in
        # "waiting" even after the DLL disables the overlay, so treating attach
        # alone as success would produce a false-positive "INJECTION COMPLETED".
        lower = line.lower()
        if "overlay verification failed, disabling overlay" in lower:
            result.failure = line
            log.error(f"[INJECT][ltk-host] {line}")
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
        elif "wad scan failed" in lower:
            if not LTK_ENFORCE_SKINHACK_SCAN:
                log.warning(
                    "[INJECT][ltk-host] WAD scan warning under Rose compatibility mode: %s",
                    line,
                )
            else:
                log.warning(f"[INJECT][ltk-host] {line}")
        else:
            # DLL records can be very verbose; keep normal records at debug.
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

    # Closing stdin mirrors the upstream host shutdown path.
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


def run_ltk_patcher_host(
    tools_dir: Path,
    overlay_dir: Path,
    stop_callback: Optional[Callable[[], bool]] = None,
    process_manager=None,
    injection_manager=None,
) -> int:
    """
    Run one LTK patcher-host session against an already-built overlay.

    Returns 0 only after the host confirms an attached/waiting state and the
    session then ends normally (game exit or PSM-requested stop). A host that
    merely finds/scans the game is not considered a successful injection.
    """
    host_exe = tools_dir / LTK_HOST_NAME
    hook_dll = tools_dir / LTK_DLL_NAME

    if not host_exe.is_file() or not hook_dll.is_file():
        log.error(
            "[INJECT][ltk-host] Missing LTK runtime pair. Expected "
            f"{host_exe} and {hook_dll}"
        )
        return 127

    overlay_prefix = str(overlay_dir.resolve())
    if not overlay_prefix.endswith(os.sep):
        overlay_prefix += os.sep

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW

    # Match current LTK Manager's normal behavior: elevation is an explicit
    # setting, not something PSM should force for every League session.
    cmd = [str(host_exe)]
    if sys.platform == "win32" and LTK_ELEVATE_INJECTOR:
        cmd.append("--elevate")

    compatibility_mode = not LTK_ENFORCE_SKINHACK_SCAN
    log.info(
        "[INJECT] Starting LTK patcher-host backend"
        + (" with elevation" if "--elevate" in cmd else " in normal mode")
    )
    log.info(
        "[INJECT] LTK Rose compatibility: anti-skinhack enforcement %s (flags=%d)",
        "ON" if LTK_ENFORCE_SKINHACK_SCAN else "OFF",
        LTK_DEFAULT_FLAGS,
    )
    started_at = time.time()
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
        stdout_thread = threading.Thread(
            target=_reader,
            args=(proc.stdout, "stdout", events),
            daemon=True,
            name="LtkHostStdout",
        )
        stderr_thread = threading.Thread(
            target=_reader,
            args=(proc.stderr, "stderr", events),
            daemon=True,
            name="LtkHostStderr",
        )
        stdout_thread.start()
        stderr_thread.start()

        # Mirror LTK Manager's public host protocol and its exposed
        # anti-skinhack enforcement setting.
        _send_line(proc, f"config loglevel {LTK_LOGLEVEL_DEBUG}")
        _send_line(proc, f"config flags {LTK_DEFAULT_FLAGS}")
        _send_line(proc, f"config prefix {overlay_prefix}")
        _send_line(proc, "start scan")

        if injection_manager is not None:
            # Defensive only: compatibility mode does not suspend the game, but
            # release any stale suspension left by an interrupted older run.
            injection_manager.resume_if_suspended()

        result = LtkHostResult()
        attach_deadline = time.time() + LTK_ATTACH_TIMEOUT_S

        while proc.poll() is None:
            _drain_events(events, result)

            if result.failure:
                log.error(f"[INJECT][ltk-host] Injection failed: {result.failure}")
                _shutdown_host(proc)
                return 2

            if result.last_state in _TERMINAL_SUCCESS_STATES:
                _shutdown_host(proc, request_stop=False)
                return 0 if result.attached else 3

            if stop_callback and stop_callback():
                log.info("[INJECT] Game ended, stopping LTK patcher host")
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
                    "[INJECT][ltk-host] Timed out waiting for an attached/waiting "
                    f"state after {LTK_ATTACH_TIMEOUT_S:.0f}s "
                    f"(last_state={result.last_state})"
                )
                _shutdown_host(proc)
                return 124

            time.sleep(PROCESS_MONITOR_SLEEP_S)

        _drain_events(events, result)
        returncode = proc.returncode
        if result.failure:
            log.error(f"[INJECT][ltk-host] Host failure: {result.failure}")
            return 2
        if returncode not in (0, None):
            log.error(f"[INJECT][ltk-host] Host exited with code {returncode}")
            return returncode
        if result.attached:
            return 0

        log.error(
            "[INJECT][ltk-host] Host exited without confirming injection "
            f"(last_state={result.last_state})"
        )
        return 3

    except Exception as exc:
        log.error(f"[INJECT][ltk-host] Backend error: {exc}")
        if proc is not None:
            _shutdown_host(proc)
        return 1
    finally:
        if process_manager is not None:
            process_manager.current_overlay_process = None
        if proc is not None and proc.poll() is None:
            _shutdown_host(proc)
        elapsed = time.time() - started_at
        log.debug(f"[INJECT][ltk-host] Backend finished after {elapsed:.2f}s")
