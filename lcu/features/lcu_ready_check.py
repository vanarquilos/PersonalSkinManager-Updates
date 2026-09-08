#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ready-check primitives for League Client automation."""

from typing import Optional

import requests


class LCUReadyCheck:
    """Read and respond to League matchmaking ready checks."""

    READY_CHECK_PATH = "/lol-matchmaking/v1/ready-check"
    ACCEPT_PATH = "/lol-matchmaking/v1/ready-check/accept"

    def __init__(self, api) -> None:
        self.api = api

    def get(self) -> Optional[dict]:
        """Return the current ready-check state without using the GET cache."""
        return self.api.get(
            self.READY_CHECK_PATH,
            timeout=1.0,
            use_cache=False,
        )

    @staticmethod
    def is_actionable(state: Optional[dict]) -> bool:
        """Return whether a ready check is awaiting the local player's response."""
        if not isinstance(state, dict):
            return False
        return (
            state.get("state") == "InProgress"
            and state.get("playerResponse") in (None, "None")
        )

    def accept(self) -> Optional[requests.Response]:
        """Accept the current ready check.

        The automation controller is responsible for revalidating the state and
        preventing duplicate/stale calls immediately before invoking this
        primitive.
        """
        return self.api.post(
            self.ACCEPT_PATH,
            json_data=None,
            timeout=1.0,
        )
