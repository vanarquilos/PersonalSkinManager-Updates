"""Keep PSM responsive while waiting for League's LCU WebSocket.

A live localhost LCU HTTP endpoint does not guarantee a WebSocket is connected.
Only run Pengu/injection startup after a real WebSocket connection; otherwise
leave the main loop responsive and emit bounded status updates.
"""
from __future__ import annotations

import time
from typing import Callable


def wait_for_client_websocket(
    *,
    is_connected: Callable[[], bool],
    is_thread_alive: Callable[[], bool],
    should_stop: Callable[[], bool],
    on_ready: Callable[[], None],
    on_waiting: Callable[[], None],
    on_thread_exit: Callable[[], None],
    poll_seconds: float = 0.25,
    notice_seconds: float = 15.0,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """Return True only if the ready callback actually finished successfully."""
    next_notice = monotonic() + notice_seconds
    while not should_stop():
        if is_connected():
            if should_stop():
                return False
            on_ready()
            return True
        if not is_thread_alive():
            on_thread_exit()
            return False
        if monotonic() >= next_notice:
            on_waiting()
            next_notice = monotonic() + notice_seconds
        sleep(poll_seconds)
    return False
