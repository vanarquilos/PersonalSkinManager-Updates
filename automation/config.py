#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent configuration for Client Automation."""

from dataclasses import dataclass

from config import get_config_option


_SECTION = "ClientAutomation"
_ALLOWED_ACCEPT_DELAYS_MS = {0, 500, 1000, 2000, 3000}


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


@dataclass(frozen=True)
class ClientAutomationConfig:
    """Current persisted Client Automation settings.

    Only the Auto Accept subset is consumed in Phase C. The master toggle and
    child toggle are both required so future feature settings cannot bypass a
    disabled Client Automation master switch.
    """

    enabled: bool = False
    auto_accept_enabled: bool = False
    auto_accept_delay_ms: int = 1000

    @property
    def auto_accept_active(self) -> bool:
        return self.enabled and self.auto_accept_enabled


def load_client_automation_config() -> ClientAutomationConfig:
    """Load Client Automation settings from the existing config.ini store."""
    return ClientAutomationConfig(
        enabled=_read_bool("enabled", False),
        auto_accept_enabled=_read_bool("auto_accept_enabled", False),
        auto_accept_delay_ms=_read_accept_delay_ms(),
    )
