#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Champion-select primitives and inspection helpers for Client Automation."""

from typing import Iterable, Optional

import requests


class LCUChampSelectAutomation:
    """Inspect and mutate only the local player's champion-select actions."""

    SESSION_PATH = "/lol-champ-select/v1/session"

    def __init__(self, api) -> None:
        self.api = api

    def get_session(self) -> Optional[dict]:
        """Return the current champion-select session without cached state."""
        return self.api.get(
            self.SESSION_PATH,
            timeout=1.0,
            use_cache=False,
        )

    @staticmethod
    def _iter_actions(session: Optional[dict]) -> Iterable[dict]:
        if not isinstance(session, dict):
            return ()
        rounds = session.get("actions") or []
        return (
            action
            for round_actions in rounds
            if isinstance(round_actions, list)
            for action in round_actions
            if isinstance(action, dict)
        )

    @staticmethod
    def local_cell_id(session: Optional[dict]) -> Optional[int]:
        if not isinstance(session, dict):
            return None
        value = session.get("localPlayerCellId")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def find_active_local_action(
        self,
        session: Optional[dict],
        action_type: Optional[str] = None,
    ) -> Optional[dict]:
        """Find the local player's currently active pick/ban action.

        League marks the actionable turn with ``isInProgress``. Requiring that
        flag prevents automation from pre-committing a future action.
        """
        local_cell = self.local_cell_id(session)
        if local_cell is None:
            return None

        normalized_type = action_type.lower() if action_type else None
        for action in self._iter_actions(session):
            try:
                actor_cell = int(action.get("actorCellId"))
            except (TypeError, ValueError):
                continue
            if actor_cell != local_cell:
                continue
            if action.get("completed") is True:
                continue
            if action.get("isInProgress") is not True:
                continue

            current_type = str(action.get("type") or "").lower()
            if current_type not in {"pick", "ban"}:
                continue
            if normalized_type and current_type != normalized_type:
                continue
            return action
        return None

    @staticmethod
    def ally_intended_champion_ids(session: Optional[dict]) -> set[int]:
        """Return non-local ally champion intents/hovered champions when exposed."""
        if not isinstance(session, dict):
            return set()

        local_cell = LCUChampSelectAutomation.local_cell_id(session)
        out: set[int] = set()
        for player in session.get("myTeam") or []:
            if not isinstance(player, dict):
                continue
            try:
                cell_id = int(player.get("cellId"))
            except (TypeError, ValueError):
                cell_id = None
            if local_cell is not None and cell_id == local_cell:
                continue

            for field in ("championPickIntent", "championId"):
                try:
                    champion_id = int(player.get(field) or 0)
                except (TypeError, ValueError):
                    continue
                if champion_id > 0:
                    out.add(champion_id)
        return out

    @staticmethod
    def selected_champion_ids(session: Optional[dict]) -> set[int]:
        """Return champion IDs currently selected by either team."""
        if not isinstance(session, dict):
            return set()

        out: set[int] = set()
        for side in ("myTeam", "theirTeam"):
            for player in session.get(side) or []:
                if not isinstance(player, dict):
                    continue
                try:
                    champion_id = int(player.get("championId") or 0)
                except (TypeError, ValueError):
                    continue
                if champion_id > 0:
                    out.add(champion_id)
        return out

    @classmethod
    def banned_champion_ids(cls, session: Optional[dict]) -> set[int]:
        """Return champion IDs already banned in the current session."""
        if not isinstance(session, dict):
            return set()

        out: set[int] = set()
        bans = session.get("bans") or {}
        if isinstance(bans, dict):
            for key in ("myTeamBans", "theirTeamBans"):
                for value in bans.get(key) or []:
                    try:
                        champion_id = int(value or 0)
                    except (TypeError, ValueError):
                        continue
                    if champion_id > 0:
                        out.add(champion_id)

        for action in cls._iter_actions(session):
            if str(action.get("type") or "").lower() != "ban":
                continue
            if action.get("completed") is not True:
                continue
            try:
                champion_id = int(action.get("championId") or 0)
            except (TypeError, ValueError):
                continue
            if champion_id > 0:
                out.add(champion_id)

        return out

    def select_action(
        self,
        action_id: int,
        champion_id: int,
    ) -> Optional[requests.Response]:
        """Set a champion on an existing local pick/ban action."""
        action_id = int(action_id)
        champion_id = int(champion_id)
        if action_id <= 0:
            raise ValueError("action_id must be a positive integer")
        if champion_id <= 0:
            raise ValueError("champion_id must be a positive integer")

        return self.api.patch(
            f"{self.SESSION_PATH}/actions/{action_id}",
            {"championId": champion_id},
            timeout=1.0,
        )

    def complete_action(self, action_id: int) -> Optional[requests.Response]:
        """Complete an existing local champion-select action."""
        action_id = int(action_id)
        if action_id <= 0:
            raise ValueError("action_id must be a positive integer")

        return self.api.post(
            f"{self.SESSION_PATH}/actions/{action_id}/complete",
            json_data=None,
            timeout=1.0,
        )
