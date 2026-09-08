#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dedicated Pengu bridge messages for Client Automation settings and status."""

from __future__ import annotations

import json
import logging

from automation.config import load_client_automation_config
from automation.settings_contract import (
    config_payload,
    encode_settings_for_storage,
    normalize_champion_catalog,
    normalize_queue_catalog,
    normalize_settings_payload,
    safe_positive_int,
    status_payload,
)
from config import set_config_option

from .message_handler import MessageHandler

log = logging.getLogger(__name__)

_SECTION = "ClientAutomation"


class ClientAutomationMessageHandler(MessageHandler):
    """Extend the existing bridge without growing the legacy settings handler."""

    def handle_message(self, message: str) -> None:
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            super().handle_message(message)
            return

        payload_type = payload.get("type") if isinstance(payload, dict) else None
        if payload_type == "client-automation-settings-request":
            self._handle_client_automation_settings_request()
            return
        if payload_type == "client-automation-settings-save":
            self._handle_client_automation_settings_save(payload)
            return
        if payload_type == "client-automation-status-request":
            self._handle_client_automation_status_request()
            return
        if payload_type == "client-automation-catalog-request":
            self._handle_client_automation_catalog_request()
            return

        super().handle_message(message)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def _handle_client_automation_settings_request(self) -> None:
        config = load_client_automation_config()
        phase = getattr(self.shared_state, "phase", None)
        payload = {
            "type": "client-automation-settings-data",
            **config_payload(config),
            **status_payload(config, phase),
        }
        self._send_response(json.dumps(payload))

    def _handle_client_automation_settings_save(self, payload: dict) -> None:
        try:
            normalized = normalize_settings_payload(payload)
            stored = encode_settings_for_storage(normalized)
        except ValueError as exc:
            self._send_response(json.dumps({
                "type": "client-automation-settings-saved",
                "success": False,
                "error": str(exc),
            }))
            return

        try:
            for key, value in stored.items():
                set_config_option(_SECTION, key, value)
        except Exception as exc:  # noqa: BLE001
            log.error("[AUTOMATION] Failed to persist Client Automation settings: %s", exc)
            self._send_response(json.dumps({
                "type": "client-automation-settings-saved",
                "success": False,
                "error": "Could not save Client Automation settings.",
            }))
            return

        config = load_client_automation_config()
        phase = getattr(self.shared_state, "phase", None)
        self._send_response(json.dumps({
            "type": "client-automation-settings-saved",
            "success": True,
            **config_payload(config),
            **status_payload(config, phase),
        }))
        log.info("[AUTOMATION] Client Automation settings saved")

    # ------------------------------------------------------------------
    # Runtime status / catalogs
    # ------------------------------------------------------------------
    def _handle_client_automation_status_request(self) -> None:
        config = load_client_automation_config()
        phase = getattr(self.shared_state, "phase", None)
        self._send_response(json.dumps({
            "type": "client-automation-status-data",
            **status_payload(config, phase),
        }))

    def _handle_client_automation_catalog_request(self) -> None:
        queues = []
        champions = []
        current_queue_id = None
        lcu = getattr(self.skin_scraper, "lcu", None) if self.skin_scraper else None

        if lcu is not None and getattr(lcu, "ok", False):
            try:
                lobby = lcu.matchmaking_lobby()
                if isinstance(lobby, dict):
                    game_config = lobby.get("gameConfig") or {}
                    current_queue_id = safe_positive_int(
                        game_config.get("queueId", lobby.get("queueId"))
                    )
            except Exception:
                pass

            try:
                raw_queues = lcu.get("/lol-game-queues/v1/queues", timeout=2.0)
                queues = normalize_queue_catalog(raw_queues)
            except Exception as exc:  # noqa: BLE001
                log.debug("[AUTOMATION] Queue catalog unavailable: %s", type(exc).__name__)

            try:
                raw_champions = lcu.get(
                    "/lol-game-data/assets/v1/champions.json",
                    timeout=3.0,
                )
                champions = normalize_champion_catalog(raw_champions)
            except Exception as exc:  # noqa: BLE001
                log.debug("[AUTOMATION] Champion catalog unavailable: %s", type(exc).__name__)

        self._send_response(json.dumps({
            "type": "client-automation-catalog-data",
            "queues": queues,
            "champions": champions,
            "currentQueueId": current_queue_id,
        }))
