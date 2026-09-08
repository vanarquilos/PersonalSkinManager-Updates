#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LCU adapter that applies Client Automation queue preferences."""

from __future__ import annotations

from typing import Callable

from lcu import LCU
from utils.core.logging import get_logger

from .config import ClientAutomationConfig, load_client_automation_config

log = get_logger()


class _RejectedResponse:
    """Minimal response-like object used when local validation fails closed."""

    def __init__(self, status_code: int = 409) -> None:
        self.status_code = status_code


class AutomationLCUAdapter:
    """Delegate to LCU while applying configured queue role preferences.

    Matchmaking controller logic remains unchanged. Immediately before the
    controller starts search, this adapter applies the persisted primary and
    secondary positions when both are configured. If role configuration is
    incomplete or League rejects the preference update, queue start fails
    closed and the controller's existing suppression logic takes over.
    """

    def __init__(
        self,
        lcu: LCU,
        *,
        config_loader: Callable[[], ClientAutomationConfig] = load_client_automation_config,
    ) -> None:
        self._lcu = lcu
        self._config_loader = config_loader

    def __getattr__(self, name):
        return getattr(self._lcu, name)

    @staticmethod
    def _response_ok(response) -> bool:
        status_code = getattr(response, "status_code", None)
        return isinstance(status_code, int) and 200 <= status_code < 300

    def start_matchmaking(self):
        config = self._config_loader()
        primary = config.primary_position
        secondary = config.secondary_position

        if primary is None and secondary is None:
            return self._lcu.start_matchmaking()

        if primary is None or secondary is None or primary == secondary:
            log.info("[AUTOMATION] Queue start skipped: role preferences are incomplete")
            return _RejectedResponse(409)

        try:
            response = self._lcu.set_matchmaking_position_preferences(primary, secondary)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[AUTOMATION] Role preference update failed (%s)",
                type(exc).__name__,
            )
            return _RejectedResponse(409)

        if not self._response_ok(response):
            log.info(
                "[AUTOMATION] Queue start skipped: role preferences rejected (HTTP %s)",
                getattr(response, "status_code", None),
            )
            return response if response is not None else _RejectedResponse(409)

        log.info("[AUTOMATION] Role preferences applied: %s / %s", primary, secondary)
        return self._lcu.start_matchmaking()
