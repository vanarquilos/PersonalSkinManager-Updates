#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LCU Features Package
Contains feature-specific handlers for game modes, properties, skin selection,
Swiftplay, matchmaking, ready checks, and champion-select automation.
"""

from .lcu_properties import LCUProperties
from .lcu_skin_selection import LCUSkinSelection
from .lcu_game_mode import LCUGameMode
from .lcu_swiftplay import LCUSwiftplay
from .lcu_matchmaking import LCUMatchmaking
from .lcu_ready_check import LCUReadyCheck
from .lcu_champ_select_automation import LCUChampSelectAutomation

__all__ = [
    "LCUProperties",
    "LCUSkinSelection",
    "LCUGameMode",
    "LCUSwiftplay",
    "LCUMatchmaking",
    "LCUReadyCheck",
    "LCUChampSelectAutomation",
]
