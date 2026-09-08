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
    """Own all decisions for automatic League-client mutations."""

    LOBBY_PHASE = "Lobby"
    MATCHMAKING_PHASE = "Matchmaking"
    READY_CHECK_PHASE = "ReadyCheck"
    CHAMP_SELECT_PHASE = "ChampSelect"
    IN_PROGRESS_PHASE = "InProgress"
    POST_GAME_PHASES = {"PreEndOfGame", "EndOfGame", "WaitingForStats"}
    _UNKNOWN_LOBBY = "__unknown_lobby__"

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

        # Auto Accept state.
        self._pending_ready_timer: Optional[threading.Timer] = None
        self._ready_check_active = False
        self._ready_check_generation = 0
        self._ready_check_attempted_generation: Optional[int] = None

        # Auto Queue / Requeue state.
        self._pending_queue_timer: Optional[threading.Timer] = None
        self._queue_attempt_generation = 0
        self._queue_attempted_key: Optional[str] = None
        self._queue_suppressed_lobby: Optional[str] = None
        self._queue_started_by_automation = False
        self._search_active = False
        self._last_lobby_fingerprint: Optional[str] = None
        self._post_game_pending = False
        self._current_phase: Optional[str] = None

        self._stopped = False

    # ------------------------------------------------------------------
    # Event surface
    # ------------------------------------------------------------------
    def handle_ready_check_event(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            return
        data = payload.get("data")
        state = data if isinstance(data, dict) else payload
        self._process_ready_check_state(state, source="event")

    def handle_lobby_event(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            return
        data = payload.get("data")
        lobby = data if isinstance(data, dict) else None
        if lobby is not None:
            self._observe_lobby(lobby)

        with self._lock:
            should_reconcile = self._current_phase == self.LOBBY_PHASE
        if should_reconcile:
            self.reconcile_matchmaking()

    def handle_search_state_event(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            return
        data = payload.get("data")
        state = data if isinstance(data, dict) else payload
        active = self._search_state_is_active(state)
        blocking_reason = self._search_blocking_reason(state)

        with self._lock:
            was_active = self._search_active
            self._search_active = active
            phase = self._current_phase
            fingerprint = self._last_lobby_fingerprint

            if blocking_reason:
                self._queue_suppressed_lobby = fingerprint or self._UNKNOWN_LOBBY
                self._cancel_pending_queue_timer_locked()

            if was_active and not active and phase in {self.LOBBY_PHASE, self.MATCHMAKING_PHASE}:
                self._queue_suppressed_lobby = fingerprint or self._UNKNOWN_LOBBY
                self._cancel_pending_queue_timer_locked()

    def handle_phase_change(self, phase: str) -> None:
        if not isinstance(phase, str):
            return

        with self._lock:
            previous = self._current_phase
            self._current_phase = phase

        # Ready check lifecycle.
        if phase == self.READY_CHECK_PHASE:
            self.reconcile_ready_check()
        else:
            with self._lock:
                self._clear_ready_check_locked()

        # Completed game: arm requeue, but wait for League to return to Lobby.
        if phase in self.POST_GAME_PHASES:
            with self._lock:
                self._post_game_pending = True
                self._search_active = False
                self._queue_started_by_automation = False
                self._cancel_pending_queue_timer_locked()
            return

        if phase == self.IN_PROGRESS_PHASE:
            with self._lock:
                self._post_game_pending = False
                self._search_active = False
                self._queue_started_by_automation = False
                self._queue_attempted_key = None
                self._queue_suppressed_lobby = None
                self._cancel_pending_queue_timer_locked()
            return

        if phase == self.MATCHMAKING_PHASE:
            with self._lock:
                self._search_active = True
                self._cancel_pending_queue_timer_locked()
            return

        if phase == self.LOBBY_PHASE:
            with self._lock:
                returned_without_completed_game = (
                    previous in {
                        self.MATCHMAKING_PHASE,
                        self.READY_CHECK_PHASE,
                        self.CHAMP_SELECT_PHASE,
                    }
                    and not self._post_game_pending
                )
                if returned_without_completed_game:
                    self._queue_suppressed_lobby = (
                        self._last_lobby_fingerprint or self._UNKNOWN_LOBBY
                    )
                    self._search_active = False
                    self._queue_started_by_automation = False
                    self._cancel_pending_queue_timer_locked()
                    log.info("[AUTOMATION] Queue restart suppressed after return to lobby")
                    return

            self.reconcile_matchmaking()
            return

        with self._lock:
            self._cancel_pending_queue_timer_locked()

    # ------------------------------------------------------------------
    # Reconciliation / lifecycle
    # ------------------------------------------------------------------
    def reconcile_ready_check(self) -> None:
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

    def reconcile_matchmaking(self) -> None:
        config = self._safe_config()
        with self._lock:
            if self._stopped or self._current_phase != self.LOBBY_PHASE:
                return

            mode = "requeue" if self._post_game_pending else "queue"
            if mode == "requeue":
                if not config.auto_requeue_active:
                    return
            elif not config.auto_queue_active:
                return

            if self._search_active or self._pending_queue_timer is not None:
                return

            if self._queue_suppressed_lobby == self._UNKNOWN_LOBBY:
                return
            if (
                self._last_lobby_fingerprint
                and self._queue_suppressed_lobby == self._last_lobby_fingerprint
            ):
                return

            self._queue_attempt_generation += 1
            generation = self._queue_attempt_generation
            timer = self._timer_factory(
                0.0,
                self._execute_queue_attempt,
                args=(generation, mode),
            )
            try:
                timer.daemon = True
            except Exception:
                pass
            self._pending_queue_timer = timer
            timer.start()

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            self._clear_ready_check_locked()
            self._cancel_pending_queue_timer_locked()

    def _safe_config(self) -> ClientAutomationConfig:
        try:
            return self._config_loader()
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[AUTOMATION] Failed to load settings (%s); automation disabled",
                type(exc).__name__,
            )
            return ClientAutomationConfig()

    # ------------------------------------------------------------------
    # Auto Accept
    # ------------------------------------------------------------------
    def _process_ready_check_state(self, state: Optional[dict], *, source: str) -> None:
        config = self._safe_config()
        actionable = self.lcu.ready_check_is_actionable(state)

        with self._lock:
            if self._stopped or not config.auto_accept_active:
                self._clear_ready_check_locked()
                return
            if not actionable:
                if self._ready_check_active:
                    log.debug(
                        "[READY CHECK] No longer actionable (%s); pending accept cancelled",
                        source,
                    )
                self._clear_ready_check_locked()
                return
            if self._ready_check_active:
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
            self._ready_check_attempted_generation = generation
            self._pending_ready_timer = None

        config = self._safe_config()
        if not config.auto_accept_active:
            log.info("[READY CHECK] Auto-accept cancelled: setting disabled")
            return

        try:
            current = self.lcu.ready_check()
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[READY CHECK] Revalidation failed (%s); accept skipped",
                type(exc).__name__,
            )
            return

        if not self.lcu.ready_check_is_actionable(current):
            log.info("[READY CHECK] State changed before execution; auto-accept cancelled")
            with self._lock:
                self._ready_check_active = False
            return

        try:
            response = self.lcu.accept_ready_check()
        except Exception as exc:  # noqa: BLE001
            log.warning("[READY CHECK] Accept failed (%s)", type(exc).__name__)
            return

        if self._response_ok(response):
            log.info("[READY CHECK] Accepted")
        else:
            log.warning(
                "[READY CHECK] Accept failed: HTTP %s",
                getattr(response, "status_code", None),
            )

    # ------------------------------------------------------------------
    # Auto Queue / Auto Requeue
    # ------------------------------------------------------------------
    def _execute_queue_attempt(self, generation: int, mode: str) -> None:
        with self._lock:
            if self._stopped or generation != self._queue_attempt_generation:
                return
            self._pending_queue_timer = None
            if self._current_phase != self.LOBBY_PHASE:
                return
            if mode == "requeue" and not self._post_game_pending:
                return
            if mode == "queue" and self._post_game_pending:
                return

        config = self._safe_config()
        queue_id = config.queue_id
        if queue_id is None:
            return
        if mode == "requeue":
            if not config.auto_requeue_active:
                return
        elif not config.auto_queue_active:
            return

        # Get lobby identity first so any blocking search state can be tied to
        # one material party/queue and cannot cause a retry loop on WS updates.
        try:
            lobby = self.lcu.matchmaking_lobby()
        except Exception as exc:  # noqa: BLE001
            log.debug("[AUTOMATION] Lobby read failed: %s", type(exc).__name__)
            return

        fingerprint = self._observe_lobby(lobby) if isinstance(lobby, dict) else None
        with self._lock:
            if fingerprint and self._queue_suppressed_lobby == fingerprint:
                return

        try:
            search_state = self.lcu.matchmaking_search_state()
        except Exception as exc:  # noqa: BLE001
            log.debug("[AUTOMATION] Search-state read failed: %s", type(exc).__name__)
            return

        if self._search_state_is_active(search_state):
            with self._lock:
                self._search_active = True
            return

        blocking_reason = self._search_blocking_reason(search_state)
        if blocking_reason:
            self._suppress_lobby(
                fingerprint,
                f"search blocked: {blocking_reason}",
            )
            return

        # No lobby: create exactly one configured solo lobby, then revalidate.
        if not isinstance(lobby, dict):
            create_key = f"{mode}:create:{queue_id}"
            if not self._claim_queue_attempt(create_key):
                return
            try:
                response = self.lcu.create_matchmaking_lobby(queue_id)
            except Exception as exc:  # noqa: BLE001
                log.warning("[AUTOMATION] Lobby creation failed (%s)", type(exc).__name__)
                return
            if not self._response_ok(response):
                log.warning(
                    "[AUTOMATION] Lobby creation failed: HTTP %s",
                    getattr(response, "status_code", None),
                )
                return
            try:
                lobby = self.lcu.matchmaking_lobby()
            except Exception:
                lobby = None
            if not isinstance(lobby, dict):
                log.warning("[AUTOMATION] Lobby creation could not be revalidated")
                return
            fingerprint = self._observe_lobby(lobby)

        current_queue_id = self._lobby_queue_id(lobby)
        member_count = self._lobby_member_count(lobby)
        local_member = lobby.get("localMember") or {}

        # Premade authority is required before any queue mutation.
        if member_count > 1 and local_member.get("isLeader") is not True:
            self._suppress_lobby(fingerprint, "local member is not premade lobby leader")
            return

        if current_queue_id != queue_id:
            # Do not silently change a premade party's queue even when leader.
            if member_count > 1:
                self._suppress_lobby(
                    fingerprint,
                    "configured queue differs from premade lobby",
                )
                return
            if local_member.get("allowedChangeActivity") is False:
                self._suppress_lobby(fingerprint, "local member cannot change queue")
                return

            switch_key = f"{mode}:switch:{fingerprint}:{queue_id}"
            if not self._claim_queue_attempt(switch_key):
                return
            try:
                response = self.lcu.create_matchmaking_lobby(queue_id)
            except Exception as exc:  # noqa: BLE001
                log.warning("[AUTOMATION] Queue switch failed (%s)", type(exc).__name__)
                return
            if not self._response_ok(response):
                self._suppress_lobby(fingerprint, "queue switch rejected")
                return

            try:
                lobby = self.lcu.matchmaking_lobby()
            except Exception:
                lobby = None
            if not isinstance(lobby, dict) or self._lobby_queue_id(lobby) != queue_id:
                self._suppress_lobby(
                    fingerprint,
                    "queue switch could not be revalidated",
                )
                return
            fingerprint = self._observe_lobby(lobby)

        lobby_reason = self._lobby_blocking_reason(lobby)
        if lobby_reason:
            self._suppress_lobby(fingerprint, lobby_reason)
            return

        # Final revalidation immediately before POST /matchmaking/search.
        try:
            current_search = self.lcu.matchmaking_search_state()
        except Exception as exc:  # noqa: BLE001
            log.debug(
                "[AUTOMATION] Final search-state revalidation failed: %s",
                type(exc).__name__,
            )
            return

        if self._search_state_is_active(current_search):
            with self._lock:
                self._search_active = True
            return

        blocking_reason = self._search_blocking_reason(current_search)
        if blocking_reason:
            self._suppress_lobby(
                fingerprint,
                f"search blocked: {blocking_reason}",
            )
            return

        start_key = f"{mode}:start:{fingerprint}:{queue_id}"
        if not self._claim_queue_attempt(start_key):
            return

        try:
            response = self.lcu.start_matchmaking()
        except Exception as exc:  # noqa: BLE001
            self._suppress_lobby(
                fingerprint,
                f"queue start failed: {type(exc).__name__}",
            )
            return

        if not self._response_ok(response):
            self._suppress_lobby(
                fingerprint,
                f"queue start rejected: HTTP {getattr(response, 'status_code', None)}",
            )
            return

        with self._lock:
            self._queue_started_by_automation = True
            self._search_active = True
            if mode == "requeue":
                self._post_game_pending = False

        log.info("[AUTOMATION] %s started", "Requeue" if mode == "requeue" else "Queue")

    def _claim_queue_attempt(self, key: str) -> bool:
        with self._lock:
            if self._stopped or self._queue_attempted_key == key:
                return False
            self._queue_attempted_key = key
            return True

    def _observe_lobby(self, lobby: dict) -> Optional[str]:
        fingerprint = self._lobby_fingerprint(lobby)
        with self._lock:
            if fingerprint != self._last_lobby_fingerprint:
                previous = self._last_lobby_fingerprint
                self._last_lobby_fingerprint = fingerprint
                self._queue_attempted_key = None

                if self._queue_suppressed_lobby == self._UNKNOWN_LOBBY:
                    # We learned the identity after a blocking search event;
                    # attach the suppression to this first observed lobby.
                    self._queue_suppressed_lobby = fingerprint
                elif previous is not None and self._queue_suppressed_lobby != fingerprint:
                    # A real party/queue/member-set change is the recovery gate.
                    self._queue_suppressed_lobby = None
            return fingerprint

    def _suppress_lobby(self, fingerprint: Optional[str], reason: str) -> None:
        with self._lock:
            self._queue_suppressed_lobby = fingerprint or self._UNKNOWN_LOBBY
            self._cancel_pending_queue_timer_locked()
        log.info("[AUTOMATION] Queue skipped: %s", reason)

    # ------------------------------------------------------------------
    # Normalizers / guards
    # ------------------------------------------------------------------
    @staticmethod
    def _lobby_queue_id(lobby: dict) -> Optional[int]:
        game_config = lobby.get("gameConfig") or {}
        raw = game_config.get("queueId", lobby.get("queueId"))
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    @staticmethod
    def _lobby_member_count(lobby: dict) -> int:
        members = lobby.get("members")
        return len(members) if isinstance(members, list) else 0

    @classmethod
    def _lobby_fingerprint(cls, lobby: dict) -> Optional[str]:
        if not isinstance(lobby, dict):
            return None
        party = str(lobby.get("partyId") or lobby.get("chatRoomId") or "")
        queue_id = cls._lobby_queue_id(lobby) or 0
        members = []
        for member in lobby.get("members") or []:
            if not isinstance(member, dict):
                continue
            identity = (
                member.get("puuid")
                or member.get("summonerId")
                or member.get("summonerName")
            )
            if identity is not None:
                members.append(str(identity))
        members.sort()
        return f"{party}|{queue_id}|{','.join(members)}"

    @classmethod
    def _lobby_blocking_reason(cls, lobby: dict) -> Optional[str]:
        if not isinstance(lobby, dict):
            return "lobby unavailable"

        restrictions = lobby.get("restrictions")
        if isinstance(restrictions, list) and restrictions:
            return "lobby has active restrictions"
        if lobby.get("canStartActivity") is False:
            return "lobby cannot start matchmaking"

        local_member = lobby.get("localMember")
        if not isinstance(local_member, dict):
            return "local lobby member unavailable"
        if local_member.get("allowedStartActivity") is False:
            return "local member cannot start matchmaking"
        if cls._lobby_member_count(lobby) > 1 and local_member.get("isLeader") is not True:
            return "local member is not premade lobby leader"
        return None

    @staticmethod
    def _search_state_is_active(state: Optional[dict]) -> bool:
        if not isinstance(state, dict):
            return False
        in_queue = state.get("isCurrentlyInQueue")
        if isinstance(in_queue, bool):
            return in_queue
        search_state = str(state.get("searchState") or "").strip().lower()
        if not search_state:
            return False
        return search_state not in {
            "none",
            "invalid",
            "canceled",
            "cancelled",
            "notsearching",
            "error",
        }

    @staticmethod
    def _search_blocking_reason(state: Optional[dict]) -> Optional[str]:
        if not isinstance(state, dict):
            return None

        search_state = str(state.get("searchState") or "").strip().lower()
        if search_state == "error":
            return "matchmaking search is in error state"

        errors = state.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0] if isinstance(errors[0], dict) else {}
            penalty = first.get("penaltyTimeRemaining")
            try:
                if penalty is not None and float(penalty) > 0:
                    return "matchmaking penalty is active"
            except (TypeError, ValueError):
                pass
            message = first.get("message") or first.get("errorType")
            return str(message) if message else "matchmaking search has an active error"

        low_priority = state.get("lowPriorityData")
        if isinstance(low_priority, dict):
            raw_penalty = (
                low_priority.get("penaltyTime")
                or low_priority.get("penaltyTimeRemaining")
                or low_priority.get("remainingTime")
            )
            try:
                if raw_penalty is not None and float(raw_penalty) > 0:
                    return "low-priority matchmaking penalty is active"
            except (TypeError, ValueError):
                pass
        return None

    @staticmethod
    def _response_ok(response) -> bool:
        status_code = getattr(response, "status_code", None)
        return isinstance(status_code, int) and 200 <= status_code < 300

    # ------------------------------------------------------------------
    # Timer cleanup
    # ------------------------------------------------------------------
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

    def _cancel_pending_queue_timer_locked(self) -> None:
        timer = self._pending_queue_timer
        self._pending_queue_timer = None
        self._queue_attempt_generation += 1
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass
