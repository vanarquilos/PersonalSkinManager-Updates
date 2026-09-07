#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Event-driven coordinator for Personal Skin Manager Client Automation."""

from __future__ import annotations

import threading
from typing import Callable, Optional

from lcu import LCU
from utils.core.logging import get_logger

from .config import ClientAutomationConfig, load_client_automation_config

log = get_logger()


class AutomationController:
    """Coordinate automatic League-client actions.

    Phase C implements only Auto Accept. The controller owns scheduling,
    idempotency, revalidation, and cancellation so WebSocket handlers never
    perform mutations directly.
    """

    READY_CHECK_PHASE = "ReadyCheck"

    def __init__(
        self,
        lcu: LCU,
        *,
        config_loader: Callable[[], ClientAutomationConfig] = load_client_automation_config,
        timer_factory: Callable[..., threading.Timer] = threading.Timer,
    ) -> None:
        self.lcu = lcu
        self._config_loader = config_loader
        self._timer_factory = timer_factory
        self._lock = threading.RLock()
        self._pending_ready_timer: Optional[threading.Timer] = None
        self._ready_check_active = False
        self._ready_check_generation = 0
        self._ready_check_attempted_generation: Optional[int] = None
        self._stopped = False

    def handle_ready_check_event(self, payload: dict) -> None:
        """Process an LCU ready-check event without mutating from the WS thread."""
        if not isinstance(payload, dict):
            return
        data = payload.get("data")
        state = data if isinstance(data, dict) else payload
        self._process_ready_check_state(state, source="event")

    def handle_phase_change(self, phase: str) -> None:
        """Reconcile a ready check on entry and cancel stale work on exit."""
        if phase == self.READY_CHECK_PHASE:
            self.reconcile_ready_check()
            return

        with self._lock:
            self._clear_ready_check_locked()

    def reconcile_ready_check(self) -> None:
        """Read current state to recover if PSM missed the initial WS event."""
        config = self._safe_config()
        if not config.auto_accept_active:
            with self._lock:
                self._clear_ready_check_locked()
            return

        try:
            state = self.lcu.ready_check()
        except Exception as exc:  # noqa: BLE001
            log.debug("[READY CHECK] Reconciliation failed: %s", type(exc).__name__)
            return
        self._process_ready_check_state(state, source="reconcile")

    def stop(self) -> None:
        """Cancel pending automation and prevent future scheduled actions."""
        with self._lock:
            self._stopped = True
            self._clear_ready_check_locked()

    def _safe_config(self) -> ClientAutomationConfig:
        try:
            return self._config_loader()
        except Exception as exc:  # noqa: BLE001
            log.warning("[AUTOMATION] Failed to load settings (%s); automation disabled", type(exc).__name__)
            return ClientAutomationConfig()

    def _process_ready_check_state(self, state: Optional[dict], *, source: str) -> None:
        config = self._safe_config()
        actionable = self.lcu.ready_check_is_actionable(state)

        with self._lock:
            if self._stopped or not config.auto_accept_active:
                self._clear_ready_check_locked()
                return

            if not actionable:
                if self._ready_check_active:
                    log.debug("[READY CHECK] No longer actionable (%s); pending accept cancelled", source)
                self._clear_ready_check_locked()
                return

            if self._ready_check_active:
                # Duplicate Create/Update events for the same ready check must not
                # schedule a second acceptance attempt.
                return

            self._ready_check_active = True
            self._ready_check_generation += 1
            generation = self._ready_check_generation
            self._ready_check_attempted_generation = None
            delay_seconds = config.auto_accept_delay_ms / 1000.0

            timer = self._timer_factory(
                delay_seconds,
                self._execute_ready_check_accept,
                args=(generation,),
            )
            try:
                timer.daemon = True
            except Exception:
                pass
            self._pending_ready_timer = timer

            log.info("[READY CHECK] Auto-accept scheduled: %.1fs", delay_seconds)
            timer.start()

    def _execute_ready_check_accept(self, generation: int) -> None:
        with self._lock:
            if self._stopped:
                return
            if generation != self._ready_check_generation:
                return
            if not self._ready_check_active:
                return
            if self._ready_check_attempted_generation == generation:
                return

            # Claim the single allowed attempt before doing I/O. Duplicate timer
            # callbacks or repeated events cannot produce a second POST.
            self._ready_check_attempted_generation = generation
            self._pending_ready_timer = None

        config = self._safe_config()
        if not config.auto_accept_active:
            log.info("[READY CHECK] Auto-accept cancelled: setting disabled")
            return

        try:
            current = self.lcu.ready_check()
        except Exception as exc:  # noqa: BLE001
            log.warning("[READY CHECK] Revalidation failed (%s); accept skipped", type(exc).__name__)
            return

        if not self.lcu.ready_check_is_actionable(current):
            # A manual Accept/Decline, expiry, or other League state transition
            # wins over the pending automation.
            log.info("[READY CHECK] State changed before execution; auto-accept cancelled")
            with self._lock:
                self._ready_check_active = False
            return

        try:
            response = self.lcu.accept_ready_check()
        except Exception as exc:  # noqa: BLE001
            log.warning("[READY CHECK] Accept failed (%s)", type(exc).__name__)
            return

        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int) and 200 <= status_code < 300:
            log.info("[READY CHECK] Accepted")
            return

        log.warning("[READY CHECK] Accept failed: HTTP %s", status_code if status_code is not None else "no response")

    def _cancel_pending_timer_locked(self) -> None:
        timer = self._pending_ready_timer
        self._pending_ready_timer = None
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass

    def _clear_ready_check_locked(self) -> None:
        self._cancel_pending_timer_locked()
        self._ready_check_active = False
        self._ready_check_attempted_generation = None
