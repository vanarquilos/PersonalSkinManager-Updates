#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dedicated Pengu bridge messages for Client Automation settings and status."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

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
from utils.core.paths import get_state_dir

from .message_handler import MessageHandler

log = logging.getLogger(__name__)

_SECTION = "ClientAutomation"
_CATALOG_CACHE_VERSION = 1
_CATALOG_CACHE_FILE = "client_automation_catalog.json"
_CHAMPION_CATALOG_PATHS = (
    "/lol-game-data/assets/v1/champion-summary.json",
    # Compatibility fallback for older clients/builds that exposed the larger
    # aggregate asset under this path.
    "/lol-game-data/assets/v1/champions.json",
)


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
            **config_payload(config),
            **self._runtime_status_payload(config),
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
        self._notify_settings_changed()
        self._send_response(json.dumps({
            "type": "client-automation-settings-saved",
            "success": True,
            **config_payload(config),
            **self._runtime_status_payload(config),
        }))
        log.info("[AUTOMATION] Client Automation settings saved and reloaded")

    def _notify_settings_changed(self) -> None:
        callback = getattr(
            self.shared_state,
            "client_automation_settings_changed_callback",
            None,
        )
        if not callable(callback):
            return
        try:
            callback()
        except Exception as exc:  # noqa: BLE001
            # Persistence already succeeded. Do not turn this into a failed save;
            # the controllers will still reload config on their next LCU event.
            log.warning(
                "[AUTOMATION] Settings reload callback failed (%s)",
                type(exc).__name__,
            )

    # ------------------------------------------------------------------
    # Runtime status / catalogs
    # ------------------------------------------------------------------
    def _handle_client_automation_status_request(self) -> None:
        config = load_client_automation_config()
        self._send_response(json.dumps({
            "type": "client-automation-status-data",
            **self._runtime_status_payload(config),
        }))

    def _runtime_status_payload(self, config) -> dict:
        provider = getattr(
            self.shared_state,
            "client_automation_status_provider",
            None,
        )
        if callable(provider):
            try:
                provided = provider()
                if isinstance(provided, dict):
                    phase = provided.get(
                        "phase",
                        getattr(self.shared_state, "phase", None),
                    )
                    runtime = status_payload(config, phase)
                    if config.enabled and provided.get("connected") is False:
                        runtime["status"] = "League disconnected"
                    return {
                        **runtime,
                        **provided,
                        "enabled": config.enabled,
                    }
            except Exception as exc:  # noqa: BLE001
                log.debug(
                    "[AUTOMATION] Runtime status provider unavailable: %s",
                    type(exc).__name__,
                )

        phase = getattr(self.shared_state, "phase", None)
        return status_payload(config, phase)

    def _catalog_cache_path(self) -> Path:
        return get_state_dir() / _CATALOG_CACHE_FILE

    def _load_catalog_cache(self) -> dict:
        path = self._catalog_cache_path()
        try:
            if not path.is_file():
                return {}
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return {}
            if payload.get("version") != _CATALOG_CACHE_VERSION:
                return {}
            return {
                "queues": normalize_queue_catalog(payload.get("queues")),
                "champions": normalize_champion_catalog(payload.get("champions")),
                "updatedAt": safe_positive_int(payload.get("updatedAt")),
            }
        except (OSError, ValueError, TypeError) as exc:
            log.debug("[AUTOMATION] Catalog cache unavailable: %s", type(exc).__name__)
            return {}

    def _save_catalog_cache(self, queues: list[dict], champions: list[dict]) -> int | None:
        if not queues and not champions:
            return None

        previous = self._load_catalog_cache()
        merged_queues = queues or previous.get("queues") or []
        merged_champions = champions or previous.get("champions") or []
        updated_at = int(time.time() * 1000)
        path = self._catalog_cache_path()
        temporary = path.with_suffix(path.suffix + ".tmp")
        payload = {
            "version": _CATALOG_CACHE_VERSION,
            "updatedAt": updated_at,
            "queues": merged_queues,
            "champions": merged_champions,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            temporary.replace(path)
            return updated_at
        except OSError as exc:
            log.debug("[AUTOMATION] Could not persist catalog cache: %s", type(exc).__name__)
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            return previous.get("updatedAt")

    def _fetch_live_champion_catalog(self, lcu) -> list[dict]:
        """Read the current League champion catalog with a compatibility fallback."""
        for path in _CHAMPION_CATALOG_PATHS:
            try:
                raw_champions = lcu.get(path, timeout=3.0)
                champions = normalize_champion_catalog(raw_champions)
            except Exception as exc:  # noqa: BLE001
                log.debug(
                    "[AUTOMATION] Champion catalog path %s unavailable: %s",
                    path,
                    type(exc).__name__,
                )
                continue
            if champions:
                log.debug(
                    "[AUTOMATION] Champion catalog loaded from %s (%d champions)",
                    path,
                    len(champions),
                )
                return champions
        return []

    def _handle_client_automation_catalog_request(self) -> None:
        cached = self._load_catalog_cache()
        cached_queues = cached.get("queues") or []
        cached_champions = cached.get("champions") or []
        cache_updated_at = cached.get("updatedAt")

        live_queues: list[dict] = []
        live_champions: list[dict] = []
        current_queue_id = None
        lcu = getattr(self.skin_scraper, "lcu", None) if self.skin_scraper else None
        league_connected = bool(lcu is not None and getattr(lcu, "ok", False))

        if league_connected:
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
                live_queues = normalize_queue_catalog(raw_queues)
            except Exception as exc:  # noqa: BLE001
                log.debug("[AUTOMATION] Queue catalog unavailable: %s", type(exc).__name__)

            live_champions = self._fetch_live_champion_catalog(lcu)

        if live_queues or live_champions:
            cache_updated_at = self._save_catalog_cache(live_queues, live_champions)
            # Reload so a partial live result can use the last known good data for
            # the catalog that was temporarily unavailable.
            cached = self._load_catalog_cache()
            cached_queues = cached.get("queues") or cached_queues
            cached_champions = cached.get("champions") or cached_champions
            cache_updated_at = cached.get("updatedAt") or cache_updated_at

        queues = live_queues or cached_queues
        champions = live_champions or cached_champions

        if live_queues and live_champions:
            source = "live"
        elif live_queues or live_champions:
            source = "mixed"
        elif queues or champions:
            source = "cache"
        else:
            source = "none"

        self._send_response(json.dumps({
            "type": "client-automation-catalog-data",
            "queues": queues,
            "champions": champions,
            "currentQueueId": current_queue_id,
            "leagueConnected": league_connected,
            "queueCatalogAvailable": bool(live_queues),
            "championCatalogAvailable": bool(live_champions),
            "queueCatalogCached": bool(not live_queues and cached_queues),
            "championCatalogCached": bool(not live_champions and cached_champions),
            "catalogSource": source,
            "catalogUpdatedAt": cache_updated_at,
        }))