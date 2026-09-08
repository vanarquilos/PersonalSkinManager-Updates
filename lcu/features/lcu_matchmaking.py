#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lobby and matchmaking primitives for Client Automation."""

from typing import Optional

import requests


class LCUMatchmaking:
    """Small LCU surface used by Auto Queue and Auto Requeue."""

    LOBBY_PATH = "/lol-lobby/v2/lobby"
    SEARCH_PATH = "/lol-lobby/v2/lobby/matchmaking/search"
    SEARCH_STATE_PATH = "/lol-lobby/v2/lobby/matchmaking/search-state"
    POSITION_PREFERENCES_PATH = "/lol-lobby/v2/lobby/members/localMember/position-preferences"
    PLAY_AGAIN_PATH = "/lol-lobby/v2/play-again"
    ALLOWED_POSITIONS = {"TOP", "JUNGLE", "MIDDLE", "UTILITY", "BOTTOM", "FILL"}

    def __init__(self, api) -> None:
        self.api = api

    def get_lobby(self) -> Optional[dict]:
        """Return the current lobby, bypassing cached state."""
        return self.api.get(
            self.LOBBY_PATH,
            timeout=1.0,
            use_cache=False,
        )

    def get_search_state(self) -> Optional[dict]:
        """Return the current matchmaking search state."""
        return self.api.get(
            self.SEARCH_STATE_PATH,
            timeout=1.0,
            use_cache=False,
        )

    def create_lobby(self, queue_id: int) -> Optional[requests.Response]:
        """Create/switch to a lobby for ``queue_id``."""
        queue_id = int(queue_id)
        if queue_id <= 0:
            raise ValueError("queue_id must be a positive integer")
        return self.api.post(
            self.LOBBY_PATH,
            json_data={"queueId": queue_id},
            timeout=2.0,
        )

    def set_position_preferences(
        self,
        primary_position: str,
        secondary_position: str,
    ) -> Optional[requests.Response]:
        """Apply local lobby role preferences before matchmaking starts."""
        primary = str(primary_position or "").strip().upper()
        secondary = str(secondary_position or "").strip().upper()
        if primary not in self.ALLOWED_POSITIONS:
            raise ValueError("primary_position is invalid")
        if secondary not in self.ALLOWED_POSITIONS:
            raise ValueError("secondary_position is invalid")
        if primary == secondary:
            raise ValueError("primary and secondary positions must differ")

        return self.api.put(
            self.POSITION_PREFERENCES_PATH,
            {
                "firstPreference": primary,
                "secondPreference": secondary,
            },
            timeout=1.5,
        )

    def start_search(self) -> Optional[requests.Response]:
        """Start matchmaking for the current eligible lobby."""
        return self.api.post(
            self.SEARCH_PATH,
            json_data=None,
            timeout=2.0,
        )

    def play_again(self) -> Optional[requests.Response]:
        """Return to a reusable post-game lobby when League permits it."""
        return self.api.post(
            self.PLAY_AGAIN_PATH,
            json_data=None,
            timeout=2.0,
        )
