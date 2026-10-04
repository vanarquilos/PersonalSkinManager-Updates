#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase Handler
Handles phase-specific logic and UI management
"""

import logging
import threading
from lcu import LCU
from lcu.core.lockfile import SWIFTPLAY_QUEUE_ID
from state import SharedState
from ui.chroma.selector import get_chroma_selector
from utils.core.logging import get_logger, log_action

log = get_logger()

_SWIFTPLAY_ACTIVE_PHASES = {"Matchmaking", "ReadyCheck", "ChampSelect", "FINALIZATION", "GameStart"}


class PhaseHandler:
    """Handles phase-specific logic"""
    
    def __init__(
        self,
        lcu: LCU,
        state: SharedState,
        injection_manager=None,
        skin_scraper=None,
        swiftplay_handler=None,
    ):
        """Initialize phase handler
        
        Args:
            lcu: LCU client instance
            state: Shared application state
            injection_manager: Injection manager instance
            skin_scraper: Skin scraper instance
            swiftplay_handler: Swiftplay handler instance
        """
        self.lcu = lcu
        self.state = state
        self.injection_manager = injection_manager
        self.skin_scraper = skin_scraper
        self.swiftplay_handler = swiftplay_handler
    
    def handle_phase_change(self, phase: str, previous_phase: str):
        """Handle phase change"""
        from threads.handlers.champ_select_reset import note_phase_for_reset
        note_phase_for_reset(self.state, phase)
        log.info(f"[phase] Phase transition: {previous_phase} → {phase} (swiftplay={self.state.is_swiftplay_mode}, extracted={len(self.state.swiftplay_extracted_mods)}, queue={self.state.current_queue_id})")
        if phase == "Matchmaking":
            if self.state.is_swiftplay_mode:
                log.info("[phase] Matchmaking phase detected in Swiftplay mode - triggering injection")
                if self.swiftplay_handler:
                    self.swiftplay_handler.monitor_swiftplay_matchmaking()
                    if not self.swiftplay_handler._injection_triggered:
                        self.swiftplay_handler.trigger_swiftplay_injection()
        
        elif phase == "ChampSelect":
            # Queue ID 480 fallback - handles race condition where game_mode_detector
            # hasn't set is_swiftplay_mode yet when we enter ChampSelect
            if not self.state.is_swiftplay_mode and self.state.current_queue_id == SWIFTPLAY_QUEUE_ID:
                log.info("[phase] ChampSelect - queue ID 480 detected, setting Swiftplay mode")
                self.state.is_swiftplay_mode = True
                # Ensure handler state is initialized
                if self.swiftplay_handler:
                    self.swiftplay_handler._injection_triggered = False
                    self.swiftplay_handler._last_matchmaking_state = None

            log.debug(f"[phase] ChampSelect detected - is_swiftplay_mode={self.state.is_swiftplay_mode}, extracted_mods={len(self.state.swiftplay_extracted_mods)}")
            if self.state.is_swiftplay_mode:
                # Matchmaking can race the Swiftplay skin monitor. This helper
                # prepares the newly arrived selection if necessary and starts
                # the same overlay path exactly once.
                try:
                    from ui.core.user_interface import get_user_interface
                    user_interface = get_user_interface(self.state, self.skin_scraper)
                    if (
                        not user_interface.is_ui_initialized()
                        and not user_interface._pending_ui_initialization
                    ):
                        log.info(
                            "[phase] ChampSelect in Swiftplay mode - "
                            "requesting UI initialization"
                        )
                        user_interface.request_ui_initialization()
                except Exception as e:
                    log.warning(
                        f"[phase] Failed to request UI initialization in "
                        f"Swiftplay ChampSelect: {e}"
                    )

                if self.swiftplay_handler:
                    self.swiftplay_handler.start_swiftplay_overlay_async("ChampSelect")
            else:
                # Normal ChampSelect handling
                from threads.handlers.champ_select_reset import perform_champ_select_reset
                perform_champ_select_reset(self.state, self.lcu)
                self.state.locked_champ_id = None
                self.state.locked_champ_timestamp = 0.0
                self.state.champion_exchange_triggered = False
                self.state.own_champion_locked = False

                # Backup UI initialization
                try:
                    from ui.core.user_interface import get_user_interface
                    user_interface = get_user_interface(self.state, self.skin_scraper)
                    if not user_interface.is_ui_initialized() and not user_interface._pending_ui_initialization:
                        log.info("[phase] ChampSelect detected - requesting UI initialization (backup)")
                        user_interface.request_ui_initialization()
                except Exception as e:
                    log.warning(f"[phase] Failed to request UI initialization in ChampSelect: {e}")
        
        elif phase == "GameStart":
            if self.state.is_swiftplay_mode and self.swiftplay_handler:
                log.info("[phase] GameStart fallback - ensuring Swiftplay overlay is active")
                self.swiftplay_handler.start_swiftplay_overlay_async("GameStart")
            log_action(log, "GameStart detected - UI will be destroyed after injection", "🚀")
        
        elif phase == "InProgress":
            if (
                self.state.is_swiftplay_mode
                and self.swiftplay_handler
                and not self.swiftplay_handler._overlay_done
            ):
                log.info(
                    "[phase] InProgress last-resort fallback - "
                    "ensuring Swiftplay overlay is active"
                )
                self.swiftplay_handler.start_swiftplay_overlay_async("InProgress")
            self._handle_in_progress()
        
        elif phase == "EndOfGame":
            self._handle_end_of_game()
        
        elif phase == "ReadyCheck":
            if not self.state.is_swiftplay_mode:
                self._request_ui_destruction()
        
        else:
            # Exit champ select or other phases
            if not self.state.is_swiftplay_mode and phase is not None:
                self._request_ui_destruction()
                self._reset_state()
        
        # Handle lobby exit
        # Don't cleanup Swiftplay if we're transitioning to Matchmaking/ChampSelect (need extracted mods)
        if previous_phase == "Lobby" and phase != "Lobby":
            if self.state.is_swiftplay_mode and self.swiftplay_handler:
                # Only cleanup if we're not going to Matchmaking/ChampSelect (where we need extracted mods)
                if phase not in ["Matchmaking", "ReadyCheck", "ChampSelect", "FINALIZATION", "GameStart", "InProgress"]:
                    self.swiftplay_handler.cleanup_swiftplay_exit()

        # Handle returning to Lobby from a Swiftplay game flow (dodge, decline, etc.)
        # Only cleanup if we're NOT returning to a Swiftplay lobby (queue ID 480).
        # If queue ID is still 480, user wants to requeue with same skins — preserve tracking.
        if phase == "Lobby" and previous_phase in _SWIFTPLAY_ACTIVE_PHASES:
            if self.state.is_swiftplay_mode and self.swiftplay_handler:
                # Check if we're still in a Swiftplay lobby (queue ID 480)
                if self.state.current_queue_id == SWIFTPLAY_QUEUE_ID:
                    log.info(f"[phase] Returned to Lobby from {previous_phase} - still in Swiftplay queue (480), preserving skin tracking")
                else:
                    log.info(f"[phase] Returned to Lobby from {previous_phase} - queue changed, cleaning up Swiftplay state")
                    self.swiftplay_handler.cleanup_swiftplay_exit()
    
    def _handle_in_progress(self):
        """Handle InProgress without blocking phase processing on Swiftplay."""
        if (
            self.state.is_swiftplay_mode
            and self.swiftplay_handler
            and self.swiftplay_handler.overlay_work_active()
        ):
            log.info(
                "[phase] InProgress - Swiftplay overlay active; "
                "deferring UI destruction"
            )

            def _wait_then_destroy():
                try:
                    worker = self.swiftplay_handler._overlay_thread
                    if worker is not None and worker.is_alive():
                        worker.join(timeout=30)
                    elif self.swiftplay_handler._overlay_lock.locked():
                        lock = self.swiftplay_handler._overlay_lock
                        if lock.acquire(timeout=30):
                            lock.release()
                except Exception as e:
                    log.debug(f"[phase] Error waiting for Swiftplay overlay worker: {e}")
                self._destroy_ui_for_in_progress()

            threading.Thread(
                target=_wait_then_destroy,
                daemon=True,
                name="SwiftplayInProgressUICleanup",
            ).start()
            return

        self._destroy_ui_for_in_progress()

    def _destroy_ui_for_in_progress(self):
        """Destroy champ-select UI after the Swiftplay overlay is safely started."""
        try:
            from ui.core.user_interface import get_user_interface
            user_interface = get_user_interface(self.state, self.skin_scraper)
            user_interface.request_ui_destruction()
            log_action(log, "UI destruction requested for InProgress", "")
        except Exception as e:
            log.warning(f"[phase] Failed to request UI destruction for InProgress: {e}")

        chroma_selector = get_chroma_selector()
        if chroma_selector:
            try:
                chroma_selector.panel.request_destroy()
                log.debug("[phase] Chroma panel destroy requested for InProgress")
            except Exception as e:
                log.debug(f"[phase] Error destroying chroma panel: {e}")
    
    def _handle_end_of_game(self):
        """Handle EndOfGame phase"""
        try:
            from ui.core.user_interface import get_user_interface
            user_interface = get_user_interface(self.state, self.skin_scraper)
            user_interface.request_ui_destruction()
            log_action(log, "UI destruction requested for EndOfGame", "")
        except Exception as e:
            log.warning(f"[phase] Failed to request UI destruction for EndOfGame: {e}")

        if self.injection_manager:
            try:
                self.injection_manager.stop_overlay_process()
                log_action(log, "Stopped overlay process for EndOfGame", "🛑")
            except Exception as e:
                log.warning(f"[phase] Failed to stop overlay process: {e}")

        # Clean up Swiftplay state after game ends to prevent stale data
        if self.state.is_swiftplay_mode and self.swiftplay_handler:
            log.info("[phase] EndOfGame - cleaning up Swiftplay state")
            self.swiftplay_handler.cleanup_swiftplay_exit()
    
    def _request_ui_destruction(self):
        """Request UI destruction"""
        try:
            from ui.core.user_interface import get_user_interface
            user_interface = get_user_interface(self.state, self.skin_scraper)
            user_interface.request_ui_destruction()
            log_action(log, "UI destruction requested", "")
        except Exception as e:
            log.warning(f"[phase] Failed to request UI destruction: {e}")
    
    def _reset_state(self):
        """Reset state for phase exit"""
        self.state.hovered_champ_id = None
        self.state.locked_champ_id = None
        self.state.locked_champ_timestamp = 0.0
        self.state.players_visible = 0
        self.state.locks_by_cell.clear()
        self.state.all_locked_announced = False
        self.state.loadout_countdown_active = False
        self.state.last_hover_written = False
        # Note: is_swiftplay_mode is NOT cleared here.  It is only cleared
        # via cleanup_swiftplay_exit() which also handles the associated
        # tracking/mods state atomically.  Clearing the flag alone would
        # leave orphaned swiftplay_extracted_mods / swiftplay_skin_tracking.

