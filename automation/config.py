#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent configuration for Client Automation."""

from dataclasses import dataclass
from typing import Optional

from config import get_config_option


_SECTION = "ClientAutomation"
_ALLOWED_ACCEPT_DELAYS_MS = {0, 500, 1000, 2000, 3000}
_ALLOWED_POSITIONS = {"TOP", "JUNGLE", "MIDDLE", "UTILITY", "BOTTOM", "FILL"}


def _read_bool(option: str, fallback: bool = False) -> bool:
    value = get_config_option(_SECTION, option)
    if value is None:
        return fallback
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return fallback


def _read_accept_delay_ms() -> int:
    raw = get_config_option(_SECTION, "auto_accept_delay_ms")
    if raw is None:
        return 1000
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1000
    return value if value in _ALLOWED_ACCEPT_DELAYS_MS else 1000


def _read_positive_int(option: str) -> Optional[int]:
    raw = get_config_option(_SECTION, option)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _read_position(option: str) -> Optional[str]:
    raw = get_config_option(_SECTION, option)
    if raw is None:
        return None
    value = str(raw).strip().upper()
    return value if value in _ALLOWED_POSITIONS else None


@dataclass(frozen=True)
class ClientAutomationConfig:
    """Current persisted Client Automation settings.

    Every child feature is gated by the master ``enabled`` switch. Queue and
    requeue additionally require a positive configured queue ID. Position
    preferences are persisted now so the Phase G UI can expose the complete
    Matchmaking settings without changing the config contract again.
    """

    enabled: bool = False

    auto_queue_enabled: bool = False
    queue_id: Optional[int] = None
    primary_position: Optional[str] = None
    secondary_position: Optional[str] = None

    auto_accept_enabled: bool = False
    auto_accept_delay_ms: int = 1000

    auto_requeue_enabled: bool = False

    @property
    def auto_queue_active(self) -> bool:
        return self.enabled and self.auto_queue_enabled and self.queue_id is not None

    @property
    def auto_accept_active(self) -> bool:
        return self.enabled and self.auto_accept_enabled

    @property
    def auto_requeue_active(self) -> bool:
        return self.enabled and self.auto_requeue_enabled and self.queue_id is not None


def load_client_automation_config() -> ClientAutomationConfig:
    """Load Client Automation settings from the existing config.ini store."""
    return ClientAutomationConfig(
        enabled=_read_bool("enabled", False),
        auto_queue_enabled=_read_bool("auto_queue_enabled", False),
        queue_id=_read_positive_int("queue_id"),
        primary_position=_read_position("primary_position"),
        secondary_position=_read_position("secondary_position"),
        auto_accept_enabled=_read_bool("auto_accept_enabled", False),
        auto_accept_delay_ms=_read_accept_delay_ms(),
        auto_requeue_enabled=_read_bool("auto_requeue_enabled", False),
    )
