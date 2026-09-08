#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dedicated Pengu bridge messages for Client Automation settings and status."""

from __future__ import annotations

import json
import logging
from typing import Iterable, Optional

from automation.config import ClientAutomationConfig, load_client_automation_config
from config import set_config_option

from .message_handler import MessageHandler

log = logging.getLogger(__name__)

_SECTION = "ClientAutomation"
_ALLOWED_DELAYS = {0, 500, 1000, 2000, 3000}
_ALLOWED_POSITIONS = {"TOP", "JUNGLE", "MIDDLE", "UTILITY", "BOTTOM", "FILL"}
_MAX_PRIORITY = 10


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
        payload = {
            "type": "client-automation-settings-data",
            **self._config_payload(config),
            **self._status_payload(config),
        }
        self._send_response(json.dumps(payload))

    def _handle_client_automation_settings_save(self, payload: dict) -> None:
        try:
            normalized = self._normalize_settings_payload(payload)
        except ValueError as exc:
            self._send_response(json.dumps({
                "type": "client-automation-settings-saved",
                "success": False,
                "error": str(exc),
            }))
            return

        try:
            for key, value in normalized.items():
                if isinstance(value, bool):
                    stored = "true" if value else "false"
                elif isinstance(value, tuple):
                    stored = ",".join(str(item) for item in value)
                elif value is None:
                    stored = ""
                else:
                    stored = str(value)
                set_config_option(_SECTION, key, stored)
        except Exception as exc:  # noqa: BLE001
            log.error("[AUTOMATION] Failed to persist Client Automation settings: %s", exc)
            self._send_response(json.dumps({
                "type": "client-automation-settings-saved",
                "success": False,
                "error": "Could not save Client Automation settings.",
            }))
            return

        config = load_client_automation_config()
        self._send_response(json.dumps({
            "type": "client-automation-settings-saved",
            "success": True,
            **self._config_payload(config),
            **self._status_payload(config),
        }))
        log.info("[AUTOMATION] Client Automation settings saved")

    @classmethod
    def _normalize_settings_payload(cls, payload: dict) -> dict:
        enabled = cls._as_bool(payload.get("enabled"), False)
        auto_queue = cls._as_bool(payload.get("autoQueueEnabled"), False)
        auto_accept = cls._as_bool(payload.get("autoAcceptEnabled"), False)
        auto_requeue = cls._as_bool(payload.get("autoRequeueEnabled"), False)
        auto_pick = cls._as_bool(payload.get("autoPickEnabled"), False)
        auto_ban = cls._as_bool(payload.get("autoBanEnabled"), False)
        protect_ally = cls._as_bool(payload.get("protectAllyIntents"), True)

        queue_id = cls._positive_int_or_none(payload.get("queueId"))
        primary = cls._position_or_none(payload.get("primaryPosition"))
        secondary = cls._position_or_none(payload.get("secondaryPosition"))

        if (primary is None) != (secondary is None):
            raise ValueError("Choose both primary and secondary roles, or leave both unset.")
        if primary is not None and primary == secondary:
            raise ValueError("Primary and secondary roles must be different.")
        if (auto_queue or auto_requeue) and queue_id is None:
            raise ValueError("Choose a queue before enabling Auto Queue or Auto Requeue.")

        try:
            delay = int(payload.get("autoAcceptDelayMs", 1000))
        except (TypeError, ValueError):
            raise ValueError("Auto Accept delay is invalid.") from None
        if delay not in _ALLOWED_DELAYS:
            raise ValueError("Auto Accept delay must use one of the supported presets.")

        pick_priority = cls._priority(payload.get("pickPriority"))
        ban_priority = cls._priority(payload.get("banPriority"))
        if auto_pick and not pick_priority:
            raise ValueError("Add at least one champion before enabling Auto Pick.")
        if auto_ban and not ban_priority:
            raise ValueError("Add at least one champion before enabling Auto Ban.")

        return {
            "enabled": enabled,
            "auto_queue_enabled": auto_queue,
            "queue_id": queue_id,
            "primary_position": primary,
            "secondary_position": secondary,
            "auto_accept_enabled": auto_accept,
            "auto_accept_delay_ms": delay,
            "auto_requeue_enabled": auto_requeue,
            "auto_pick_enabled": auto_pick,
            "pick_priority": pick_priority,
            "auto_ban_enabled": auto_ban,
            "ban_priority": ban_priority,
            "protect_ally_intents": protect_ally,
        }

    @staticmethod
    def _as_bool(value, fallback: bool) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return fallback
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return fallback

    @staticmethod
    def _positive_int_or_none(value) -> Optional[int]:
        if value is None or str(value).strip() == "":
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise ValueError("Queue ID must be a positive integer.") from None
        if parsed <= 0:
            raise ValueError("Queue ID must be a positive integer.")
        return parsed

    @staticmethod
    def _position_or_none(value) -> Optional[str]:
        if value is None or str(value).strip() == "":
            return None
        normalized = str(value).strip().upper()
        if normalized not in _ALLOWED_POSITIONS:
            raise ValueError("Role preference is invalid.")
        return normalized

    @staticmethod
    def _priority(value) -> tuple[int, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            values: Iterable = value.split(",")
        elif isinstance(value, (list, tuple)):
            values = value
        else:
            raise ValueError("Champion priority must be a list of champion IDs.")

        out: list[int] = []
        seen: set[int] = set()
        for raw in values:
            try:
                champion_id = int(str(raw).strip())
            except (TypeError, ValueError):
                raise ValueError("Champion priorities may contain only valid champion IDs.") from None
            if champion_id <= 0:
                raise ValueError("Champion IDs must be positive integers.")
            if champion_id in seen:
                continue
            out.append(champion_id)
            seen.add(champion_id)
            if len(out) >= _MAX_PRIORITY:
                break
        return tuple(out)

    @staticmethod
    def _config_payload(config: ClientAutomationConfig) -> dict:
        return {
            "enabled": config.enabled,
            "autoQueueEnabled": config.auto_queue_enabled,
            "queueId": config.queue_id,
            "primaryPosition": config.primary_position,
            "secondaryPosition": config.secondary_position,
            "autoAcceptEnabled": config.auto_accept_enabled,
            "autoAcceptDelayMs": config.auto_accept_delay_ms,
            "autoRequeueEnabled": config.auto_requeue_enabled,
            "autoPickEnabled": config.auto_pick_enabled,
            "pickPriority": list(config.pick_priority),
            "autoBanEnabled": config.auto_ban_enabled,
            "banPriority": list(config.ban_priority),
            "protectAllyIntents": config.protect_ally_intents,
        }

    # ------------------------------------------------------------------
    # Runtime status / catalogs
    # ------------------------------------------------------------------
    def _handle_client_automation_status_request(self) -> None:
        config = load_client_automation_config()
        self._send_response(json.dumps({
            "type": "client-automation-status-data",
            **self._status_payload(config),
        }))

    def _status_payload(self, config: ClientAutomationConfig) -> dict:
        phase = getattr(self.shared_state, "phase", None)
        return {
            "phase": phase,
            "status": self._status_label(config, phase),
            "enabled": config.enabled,
        }

    @staticmethod
    def _status_label(config: ClientAutomationConfig, phase: Optional[str]) -> str:
        if not config.enabled:
            return "Disabled"
        labels = {
            "Lobby": "Lobby ready",
            "Matchmaking": "Searching for match",
            "ReadyCheck": "Match found",
            "ChampSelect": "Champion Select",
            "InProgress": "In game",
            "PreEndOfGame": "Finishing game",
            "EndOfGame": "Post-game",
            "WaitingForStats": "Post-game",
        }
        return labels.get(phase, "Waiting for League")

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
                    current_queue_id = self._safe_positive_int(
                        game_config.get("queueId", lobby.get("queueId"))
                    )
            except Exception:
                pass

            try:
                raw_queues = lcu.get("/lol-game-queues/v1/queues", timeout=2.0)
                if isinstance(raw_queues, list):
                    seen = set()
                    for item in raw_queues:
                        if not isinstance(item, dict):
                            continue
                        queue_id = self._safe_positive_int(item.get("id") or item.get("queueId"))
                        if queue_id is None or queue_id in seen:
                            continue
                        if item.get("isVisible") is False or item.get("isEnabled") is False:
                            continue
                        name = (
                            item.get("name")
                            or item.get("shortName")
                            or item.get("description")
                            or f"Queue {queue_id}"
                        )
                        queues.append({"id": queue_id, "name": str(name)})
                        seen.add(queue_id)
            except Exception as exc:  # noqa: BLE001
                log.debug("[AUTOMATION] Queue catalog unavailable: %s", type(exc).__name__)

            try:
                raw_champions = lcu.get("/lol-game-data/assets/v1/champions.json", timeout=3.0)
                if isinstance(raw_champions, dict):
                    raw_champions = list(raw_champions.values())
                if isinstance(raw_champions, list):
                    seen = set()
                    for item in raw_champions:
                        if not isinstance(item, dict):
                            continue
                        champion_id = self._safe_positive_int(item.get("id") or item.get("key"))
                        name = item.get("name")
                        if champion_id is None or not name or champion_id in seen:
                            continue
                        champions.append({"id": champion_id, "name": str(name)})
                        seen.add(champion_id)
            except Exception as exc:  # noqa: BLE001
                log.debug("[AUTOMATION] Champion catalog unavailable: %s", type(exc).__name__)

        queues.sort(key=lambda item: (item["name"].lower(), item["id"]))
        champions.sort(key=lambda item: item["name"].lower())

        self._send_response(json.dumps({
            "type": "client-automation-catalog-data",
            "queues": queues,
            "champions": champions,
            "currentQueueId": current_queue_id,
        }))

    @staticmethod
    def _safe_positive_int(value) -> Optional[int]:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None
