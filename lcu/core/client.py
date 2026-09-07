#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
League Client API client
Main orchestrator for LCU API interactions
"""

from typing import Optional

from .lcu_connection import LCUConnection
from .lcu_api import LCUAPI
from ..features.lcu_properties import LCUProperties
from ..features.lcu_skin_selection import LCUSkinSelection
from ..features.lcu_game_mode import LCUGameMode
from ..features.lcu_swiftplay import LCUSwiftplay
from ..features.lcu_matchmaking import LCUMatchmaking
from ..features.lcu_ready_check import LCUReadyCheck
from ..features.lcu_champ_select_automation import LCUChampSelectAutomation


class LCU:
    """League Client API client - main orchestrator"""
    
    def __init__(self, lockfile_path: Optional[str] = None):
        """Initialize LCU client
        
        Args:
            lockfile_path: Optional explicit path to lockfile
        """
        self._connection = LCUConnection(lockfile_path)
        self._api = LCUAPI(self._connection)
        self._properties = LCUProperties(self._api)
        self._skin_selection = LCUSkinSelection(self._api, self._connection)
        self._game_mode = LCUGameMode(self._properties)
        self._swiftplay = LCUSwiftplay(self._api, self._game_mode)
        self._matchmaking = LCUMatchmaking(self._api)
        self._ready_check = LCUReadyCheck(self._api)
        self._champ_select_automation = LCUChampSelectAutomation(self._api)
    
    @property
    def ok(self) -> bool:
        return self._connection.ok
    
    @property
    def port(self) -> Optional[int]:
        return self._connection.port
    
    @property
    def pw(self) -> Optional[str]:
        return self._connection.pw
    
    @property
    def base(self) -> Optional[str]:
        return self._connection.base
    
    @property
    def s(self):
        return self._connection.session
    
    def refresh_if_needed(self, force: bool = False):
        self._connection.refresh_if_needed(force)

    def websocket_credentials(self):
        return self._connection.websocket_credentials()
    
    def get(self, path: str, timeout: float = 1.0):
        return self._api.get(path, timeout)

    def post(self, path: str, json_data=None, timeout: float = 1.0, headers=None):
        return self._api.post(path, json_data, timeout, headers)
    
    @property
    def phase(self) -> Optional[str]:
        return self._properties.phase
    
    @property
    def session(self) -> Optional[dict]:
        return self._properties.session
    
    @property
    def hovered_champion_id(self) -> Optional[int]:
        return self._properties.hovered_champion_id
    
    @property
    def my_selection(self) -> Optional[dict]:
        return self._properties.my_selection
    
    @property
    def unlocked_skins(self) -> Optional[dict]:
        return self._properties.unlocked_skins
    
    def owned_skins(self) -> Optional[list[int]]:
        return self._properties.owned_skins()
    
    @property
    def current_summoner(self) -> Optional[dict]:
        return self._properties.current_summoner
    
    @property
    def region_locale(self) -> Optional[dict]:
        return self._properties.region_locale
    
    @property
    def client_language(self) -> Optional[str]:
        return self._properties.client_language
    
    def set_selected_skin(self, action_id: int, skin_id: int) -> bool:
        return self._skin_selection.set_selected_skin(action_id, skin_id)
    
    def set_my_selection_skin(self, skin_id: int) -> bool:
        return self._skin_selection.set_my_selection_skin(skin_id)
    
    @property
    def game_session(self) -> Optional[dict]:
        return self._properties.game_session
    
    @property
    def game_mode(self) -> Optional[str]:
        return self._game_mode.game_mode
    
    @property
    def map_id(self) -> Optional[int]:
        return self._game_mode.map_id
    
    @property
    def is_aram(self) -> bool:
        return self._game_mode.is_aram
    
    @property
    def is_sr(self) -> bool:
        return self._game_mode.is_sr
    
    @property
    def is_swiftplay(self) -> bool:
        return self._game_mode.is_swiftplay
    
    def get_swiftplay_lobby_data(self) -> Optional[dict]:
        return self._swiftplay.get_swiftplay_lobby_data()
    
    def get_swiftplay_champion_selection(self) -> Optional[dict]:
        return self._swiftplay.get_swiftplay_champion_selection()
    
    def get_swiftplay_dual_champion_selection(self) -> Optional[dict]:
        return self._swiftplay.get_swiftplay_dual_champion_selection()

    def force_swiftplay_base_skins(self, skin_tracking: dict, owned_skin_ids: set = None) -> bool:
        return self._swiftplay.force_base_skin_slots(skin_tracking, owned_skin_ids)

    def matchmaking_lobby(self) -> Optional[dict]:
        return self._matchmaking.get_lobby()

    def matchmaking_search_state(self) -> Optional[dict]:
        return self._matchmaking.get_search_state()

    def create_matchmaking_lobby(self, queue_id: int):
        return self._matchmaking.create_lobby(queue_id)

    def start_matchmaking(self):
        return self._matchmaking.start_search()

    def play_again(self):
        return self._matchmaking.play_again()

    def ready_check(self) -> Optional[dict]:
        return self._ready_check.get()

    def ready_check_is_actionable(self, state: Optional[dict]) -> bool:
        return self._ready_check.is_actionable(state)

    def accept_ready_check(self):
        return self._ready_check.accept()

    def champ_select_session(self) -> Optional[dict]:
        return self._champ_select_automation.get_session()

    def active_local_champ_select_action(
        self,
        session: Optional[dict],
        action_type: Optional[str] = None,
    ) -> Optional[dict]:
        return self._champ_select_automation.find_active_local_action(session, action_type)

    def ally_intended_champion_ids(self, session: Optional[dict]) -> set[int]:
        return self._champ_select_automation.ally_intended_champion_ids(session)

    def selected_champion_ids(self, session: Optional[dict]) -> set[int]:
        return self._champ_select_automation.selected_champion_ids(session)

    def banned_champion_ids(self, session: Optional[dict]) -> set[int]:
        return self._champ_select_automation.banned_champion_ids(session)

    def select_champ_select_action(self, action_id: int, champion_id: int):
        return self._champ_select_automation.select_action(action_id, champion_id)

    def complete_champ_select_action(self, action_id: int):
        return self._champ_select_automation.complete_action(action_id)
    
    def get_champion_name_by_id(self, champion_id: int) -> Optional[str]:
        return self._properties.get_champion_name_by_id(champion_id)
