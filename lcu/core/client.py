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
        # Initialize connection
        self._connection = LCUConnection(lockfile_path)
        
        # Initialize API handler
        self._api = LCUAPI(self._connection)
        
        # Initialize property/feature handlers
        self._properties = LCUProperties(self._api)
        self._skin_selection = LCUSkinSelection(self._api, self._connection)
        self._game_mode = LCUGameMode(self._properties)
        self._swiftplay = LCUSwiftplay(self._api, self._game_mode)
        self._matchmaking = LCUMatchmaking(self._api)
        self._ready_check = LCUReadyCheck(self._api)
        self._champ_select_automation = LCUChampSelectAutomation(self._api)
    
    # Connection properties (delegated to connection)
    @property
    def ok(self) -> bool:
        """Check if LCU connection is active"""
        return self._connection.ok
    
    @property
    def port(self) -> Optional[int]:
        """Get LCU port"""
        return self._connection.port
    
    @property
    def pw(self) -> Optional[str]:
        """Get LCU password"""
        return self._connection.pw
    
    @property
    def base(self) -> Optional[str]:
        """Get LCU base URL"""
        return self._connection.base
    
    @property
    def s(self):
        """Get requests session (for backward compatibility)"""
        return self._connection.session
    
    def refresh_if_needed(self, force: bool = False):
        """Refresh connection if needed"""
        self._connection.refresh_if_needed(force)

    def websocket_credentials(self):
        """Return a consistent port/password snapshot for the LCU WebSocket."""
        return self._connection.websocket_credentials()
    
    def get(self, path: str, timeout: float = 1.0):
        """Make GET request to LCU API"""
        return self._api.get(path, timeout)

    def post(self, path: str, json_data=None, timeout: float = 1.0, headers=None):
        """Make POST request to LCU API."""
        return self._api.post(path, json_data, timeout, headers)
    
    # Properties (delegated to properties handler)
    @property
    def phase(self) -> Optional[str]:
        """Get current gameflow phase"""
        return self._properties.phase
    
    @property
    def session(self) -> Optional[dict]:
        """Get current session"""
        return self._properties.session
    
    @property
    def hovered_champion_id(self) -> Optional[int]:
        """Get hovered champion ID"""
        return self._properties.hovered_champion_id
    
    @property
    def my_selection(self) -> Optional[dict]:
        """Get my selection"""
        return self._properties.my_selection
    
    @property
    def unlocked_skins(self) -> Optional[dict]:
        """Get unlocked skins"""
        return self._properties.unlocked_skins
    
    def owned_skins(self) -> Optional[list[int]]:
        """Get owned skins (returns list of skin IDs)"""
        return self._properties.owned_skins()
    
    @property
    def current_summoner(self) -> Optional[dict]:
        """Get current summoner info"""
        return self._properties.current_summoner
    
    @property
    def region_locale(self) -> Optional[dict]:
        """Get client region and locale information"""
        return self._properties.region_locale
    
    @property
    def client_language(self) -> Optional[str]:
        """Get client language from LCU API"""
        return self._properties.client_language
    
    # Skin selection methods (delegated to skin selection handler)
    def set_selected_skin(self, action_id: int, skin_id: int) -> bool:
        """Set the selected skin for a champion select action"""
        return self._skin_selection.set_selected_skin(action_id, skin_id)
    
    def set_my_selection_skin(self, skin_id: int) -> bool:
        """Set the selected skin using my-selection endpoint"""
        return self._skin_selection.set_my_selection_skin(skin_id)
    
    # Game mode properties (delegated to game mode handler)
    @property
    def game_session(self) -> Optional[dict]:
        """Get current game session with mode and map info"""
        return self._properties.game_session
    
    @property
    def game_mode(self) -> Optional[str]:
        """Get current game mode (e.g., 'ARAM', 'CLASSIC')"""
        return self._game_mode.game_mode
    
    @property
    def map_id(self) -> Optional[int]:
        """Get current map ID (12 = Howling Abyss, 11 = Summoner's Rift)"""
        return self._game_mode.map_id
    
    @property
    def is_aram(self) -> bool:
        """Check if currently in ARAM (Howling Abyss)"""
        return self._game_mode.is_aram
    
    @property
    def is_sr(self) -> bool:
        """Check if currently in Summoner's Rift"""
        return self._game_mode.is_sr
    
    @property
    def is_swiftplay(self) -> bool:
        """Check if currently in Swiftplay mode"""
        return self._game_mode.is_swiftplay
    
    # Swiftplay methods (delegated to swiftplay handler)
    def get_swiftplay_lobby_data(self) -> Optional[dict]:
        """Get Swiftplay lobby data with champion selection"""
        return self._swiftplay.get_swiftplay_lobby_data()
    
    def get_swiftplay_champion_selection(self) -> Optional[dict]:
        """Get champion selection data from Swiftplay lobby (single champion)"""
        return self._swiftplay.get_swiftplay_champion_selection()
    
    def get_swiftplay_dual_champion_selection(self) -> Optional[dict]:
        """Get both champion selections from Swiftplay lobby"""
        return self._swiftplay.get_swiftplay_dual_champion_selection()

    def force_swiftplay_base_skins(self, skin_tracking: dict, owned_skin_ids: set = None) -> bool:
        """Force base skins on swiftplay player slots for tracked champions"""
        return self._swiftplay.force_base_skin_slots(skin_tracking, owned_skin_ids)

    # Client Automation primitives (decision-making remains in the controller)
    def matchmaking_lobby(self) -> Optional[dict]:
        """Return the current matchmaking lobby."""
        return self._matchmaking.get_lobby()

    def matchmaking_search_state(self) -> Optional[dict]:
        """Return the current matchmaking search state."""
        return self._matchmaking.get_search_state()

    def create_matchmaking_lobby(self, queue_id: int):
        """Create a lobby for the configured queue."""
        return self._matchmaking.create_lobby(queue_id)

    def start_matchmaking(self):
        """Start matchmaking in the current lobby."""
        return self._matchmaking.start_search()

    def play_again(self):
        """Return to a reusable post-game lobby when available."""
        return self._matchmaking.play_again()

    def ready_check(self) -> Optional[dict]:
        """Return the current ready-check state."""
        return self._ready_check.get()

    def ready_check_is_actionable(self, state: Optional[dict]) -> bool:
        """Return whether the local player still needs to answer."""
        return self._ready_check.is_actionable(state)

    def accept_ready_check(self):
        """Accept the current ready check."""
        return self._ready_check.accept()

    def champ_select_session(self) -> Optional[dict]:
        """Return the current champion-select session."""
        return self._champ_select_automation.get_session()

    def active_local_champ_select_action(
        self,
        session: Optional[dict],
        action_type: Optional[str] = None,
    ) -> Optional[dict]:
        """Return the local player's active pick/ban action."""
        return self._champ_select_automation.find_active_local_action(session, action_type)

    def ally_intended_champion_ids(self, session: Optional[dict]) -> set[int]:
        """Return ally pick intents/hovered champions."""
        return self._champ_select_automation.ally_intended_champion_ids(session)

    def selected_champion_ids(self, session: Optional[dict]) -> set[int]:
        """Return champions currently selected by either team."""
        return self._champ_select_automation.selected_champion_ids(session)

    def banned_champion_ids(self, session: Optional[dict]) -> set[int]:
        """Return champions already banned in champion select."""
        return self._champ_select_automation.banned_champion_ids(session)

    def select_champ_select_action(self, action_id: int, champion_id: int):
        """Set a champion on the local pick/ban action."""
        return self._champ_select_automation.select_action(action_id, champion_id)

    def complete_champ_select_action(self, action_id: int):
        """Complete the local pick/ban action."""
        return self._champ_select_automation.complete_action(action_id)
    
    # Champion name lookup (delegated to properties handler)
    def get_champion_name_by_id(self, champion_id: int) -> Optional[str]:
        """Get champion name by champion ID"""
        return self._properties.get_champion_name_by_id(champion_id)
