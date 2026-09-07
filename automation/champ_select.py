#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Champion-select automation coordinator for Client Automation."""

from __future__ import annotations

import threading
from typing import Callable, Optional

from lcu import LCU
from utils.core.logging import get_logger

from .config import ClientAutomationConfig, load_client_automation_config

log = get_logger()


class ChampSelectAutomationController:
    """Coordinate local champion-select automation.

    Phase E implements Auto Pick only. The class is deliberately isolated from
    matchmaking state while sharing the same persisted Client Automation
    contract. Phase F will extend this coordinator with Auto Ban so pick/ban
    ordering, action identity, and manual-override rules stay in one place.
    """

    CHAMP_SELECT_PHASE = "ChampSelect"
    PICK_COMPLETE_DELAY_S = 0.35

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

        self._current_phase: Optional[str] = None
        self._pending_pick_timer: Optional[threading.Timer] = None
        self._pending_pick_action_id: Optional[int] = None
        self._pending_pick_candidate_id: Optional[int] = None
        self._attempted_pick_action_ids: set[int] = set()
        self._stopped = False

    def handle_phase_change(self, phase: str) -> None:
        """Reset per-session guards and reconcile when entering ChampSelect."""
        if not isinstance(phase, str):
            return

        with self._lock:
            previous = self._current_phase
            self._current_phase = phase

            if phase != self.CHAMP_SELECT_PHASE:
                self._clear_pending_pick_locked()
                if previous == self.CHAMP_SELECT_PHASE:
                    self._attempted_pick_action_ids.clear()
                return

            if previous != self.CHAMP_SELECT_PHASE:
                self._clear_pending_pick_locked()
                self._attempted_pick_action_ids.clear()

        if previous != self.CHAMP_SELECT_PHASE:
            self.reconcile_session()

    def handle_session_event(self, payload: dict) -> None:
        """Process champion-select session updates from the existing LCU WS."""
        if not isinstance(payload, dict):
            return
        data = payload.get("data")
        session = data if isinstance(data, dict) else None
        if session is None:
            return
        self._process_session(session, source="event")

    def reconcile_session(self) -> None:
        """Read the current session once to recover from a missed WS event."""
        config = self._safe_config()
        if not config.auto_pick_active:
            return
        try:
            session = self.lcu.champ_select_session()
        except Exception as exc:  # noqa: BLE001
            log.debug("[CHAMP SELECT] Session reconciliation failed: %s", type(exc).__name__)
            return
        if isinstance(session, dict):
            self._process_session(session, source="reconcile")

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            self._clear_pending_pick_locked()
            self._attempted_pick_action_ids.clear()

    def _safe_config(self) -> ClientAutomationConfig:
        try:
            return self._config_loader()
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[CHAMP SELECT] Failed to load settings (%s); automation disabled",
                type(exc).__name__,
            )
            return ClientAutomationConfig()

    def _process_session(self, session: dict, *, source: str) -> None:
        config = self._safe_config()

        with self._lock:
            if self._stopped or self._current_phase != self.CHAMP_SELECT_PHASE:
                return
            pending_action_id = self._pending_pick_action_id
            pending_candidate_id = self._pending_pick_candidate_id

        active = self.lcu.active_local_champ_select_action(session, "pick")

        # A pending automated selection is waiting for the short completion
        # revalidation window. Session changes can cancel it before the POST.
        if pending_action_id is not None:
            if not isinstance(active, dict):
                self._cancel_pick_for_manual_or_state_change(
                    pending_action_id,
                    "pick action ended before completion",
                )
                return

            action_id = self._action_id(active)
            if action_id != pending_action_id:
                self._cancel_pick_for_manual_or_state_change(
                    pending_action_id,
                    "active pick action changed",
                )
                return

            current_champion = self._action_champion_id(active)
            if current_champion not in (None, 0, pending_candidate_id):
                self._cancel_pick_for_manual_or_state_change(
                    pending_action_id,
                    "manual champion selection detected",
                )
            return

        if not config.auto_pick_active:
            return
        if not isinstance(active, dict):
            return

        action_id = self._action_id(active)
        if action_id is None:
            return

        with self._lock:
            if action_id in self._attempted_pick_action_ids:
                return

        # If the user has already hovered/selected a champion when we first see
        # the action, preserve that manual decision and never overwrite it.
        current_champion = self._action_champion_id(active)
        if current_champion not in (None, 0):
            with self._lock:
                self._attempted_pick_action_ids.add(action_id)
            log.info("[CHAMP SELECT] Auto Pick skipped: manual selection already present")
            return

        banned = self.lcu.banned_champion_ids(session)
        selected = self.lcu.selected_champion_ids(session)
        candidates = [
            champion_id
            for champion_id in config.pick_priority
            if champion_id not in banned and champion_id not in selected
        ]

        if not candidates:
            with self._lock:
                self._attempted_pick_action_ids.add(action_id)
            log.info("[CHAMP SELECT] Auto Pick skipped: no configured candidate is available")
            return

        for candidate_id in candidates:
            try:
                response = self.lcu.select_champ_select_action(action_id, candidate_id)
            except Exception as exc:  # noqa: BLE001
                log.debug(
                    "[CHAMP SELECT] Pick candidate %s failed (%s)",
                    candidate_id,
                    type(exc).__name__,
                )
                continue

            if not self._response_ok(response):
                log.debug(
                    "[CHAMP SELECT] Pick candidate %s rejected: HTTP %s",
                    candidate_id,
                    getattr(response, "status_code", None),
                )
                continue

            with self._lock:
                if self._stopped or self._current_phase != self.CHAMP_SELECT_PHASE:
                    return
                self._pending_pick_action_id = action_id
                self._pending_pick_candidate_id = candidate_id
                timer = self._timer_factory(
                    self.PICK_COMPLETE_DELAY_S,
                    self._complete_pending_pick,
                    args=(action_id, candidate_id),
                )
                try:
                    timer.daemon = True
                except Exception:
                    pass
                self._pending_pick_timer = timer

            log.info(
                "[CHAMP SELECT] Auto Pick selected champion %s; revalidating before lock",
                candidate_id,
            )
            timer.start()
            return

        # All configured candidates were rejected by the current client state.
        # Do not keep mutating the same action on duplicate session events.
        with self._lock:
            self._attempted_pick_action_ids.add(action_id)
        log.info("[CHAMP SELECT] Auto Pick skipped: all configured candidates were rejected")

    def _complete_pending_pick(self, action_id: int, candidate_id: int) -> None:
        with self._lock:
            if self._stopped or self._current_phase != self.CHAMP_SELECT_PHASE:
                return
            if self._pending_pick_action_id != action_id:
                return
            if self._pending_pick_candidate_id != candidate_id:
                return
            self._pending_pick_timer = None

        config = self._safe_config()
        if not config.auto_pick_active:
            self._finish_pick_attempt(action_id, "Auto Pick disabled before completion")
            return

        try:
            session = self.lcu.champ_select_session()
        except Exception as exc:  # noqa: BLE001
            self._finish_pick_attempt(
                action_id,
                f"session revalidation failed ({type(exc).__name__})",
            )
            return

        if not isinstance(session, dict):
            self._finish_pick_attempt(action_id, "champion-select session unavailable")
            return

        active = self.lcu.active_local_champ_select_action(session, "pick")
        if not isinstance(active, dict) or self._action_id(active) != action_id:
            self._finish_pick_attempt(action_id, "pick action changed before completion")
            return

        current_champion = self._action_champion_id(active)
        if current_champion != candidate_id:
            # This is the core manual-override guard: a user change after our
            # PATCH wins and PSM does not write the preferred champion again.
            self._finish_pick_attempt(action_id, "manual champion selection detected")
            return

        try:
            response = self.lcu.complete_champ_select_action(action_id)
        except Exception as exc:  # noqa: BLE001
            self._finish_pick_attempt(
                action_id,
                f"pick completion failed ({type(exc).__name__})",
            )
            return

        if self._response_ok(response):
            log.info("[CHAMP SELECT] Auto Pick complete: champion %s", candidate_id)
        else:
            log.warning(
                "[CHAMP SELECT] Auto Pick completion rejected: HTTP %s",
                getattr(response, "status_code", None),
            )

        self._finish_pick_attempt(action_id)

    def _cancel_pick_for_manual_or_state_change(self, action_id: int, reason: str) -> None:
        self._finish_pick_attempt(action_id, reason)

    def _finish_pick_attempt(self, action_id: int, reason: Optional[str] = None) -> None:
        with self._lock:
            self._attempted_pick_action_ids.add(action_id)
            self._clear_pending_pick_locked()
        if reason:
            log.info("[CHAMP SELECT] Auto Pick cancelled: %s", reason)

    def _clear_pending_pick_locked(self) -> None:
        timer = self._pending_pick_timer
        self._pending_pick_timer = None
        self._pending_pick_action_id = None
        self._pending_pick_candidate_id = None
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass

    @staticmethod
    def _action_id(action: dict) -> Optional[int]:
        try:
            value = int(action.get("id"))
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    @staticmethod
    def _action_champion_id(action: dict) -> Optional[int]:
        try:
            value = int(action.get("championId") or 0)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else 0

    @staticmethod
    def _response_ok(response) -> bool:
        status_code = getattr(response, "status_code", None)
        return isinstance(status_code, int) and 200 <= status_code < 300
