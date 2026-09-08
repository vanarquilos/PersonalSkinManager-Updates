#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure validation/serialization contract for Client Automation settings UI."""

from __future__ import annotations

from typing import Iterable, Optional

from .config import ClientAutomationConfig

ALLOWED_DELAYS_MS = {0, 500, 1000, 2000, 3000}
ALLOWED_POSITIONS = {"TOP", "JUNGLE", "MIDDLE", "UTILITY", "BOTTOM", "FILL"}
MAX_PRIORITY = 10


def as_bool(value, fallback: bool) -> bool:
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


def positive_int_or_none(value) -> Optional[int]:
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("Queue ID must be a positive integer.") from None
    if parsed <= 0:
        raise ValueError("Queue ID must be a positive integer.")
    return parsed


def safe_positive_int(value) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def position_or_none(value) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    normalized = str(value).strip().upper()
    if normalized not in ALLOWED_POSITIONS:
        raise ValueError("Role preference is invalid.")
    return normalized


def normalize_priority(value) -> tuple[int, ...]:
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
        if len(out) >= MAX_PRIORITY:
            break
    return tuple(out)


def normalize_settings_payload(payload: dict) -> dict:
    """Validate UI payload and return config.ini field names/typed values."""
    if not isinstance(payload, dict):
        raise ValueError("Client Automation settings payload is invalid.")

    enabled = as_bool(payload.get("enabled"), False)
    auto_queue = as_bool(payload.get("autoQueueEnabled"), False)
    auto_accept = as_bool(payload.get("autoAcceptEnabled"), False)
    auto_requeue = as_bool(payload.get("autoRequeueEnabled"), False)
    auto_pick = as_bool(payload.get("autoPickEnabled"), False)
    auto_ban = as_bool(payload.get("autoBanEnabled"), False)
    protect_ally = as_bool(payload.get("protectAllyIntents"), True)

    queue_id = positive_int_or_none(payload.get("queueId"))
    primary = position_or_none(payload.get("primaryPosition"))
    secondary = position_or_none(payload.get("secondaryPosition"))

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
    if delay not in ALLOWED_DELAYS_MS:
        raise ValueError("Auto Accept delay must use one of the supported presets.")

    pick_priority = normalize_priority(payload.get("pickPriority"))
    ban_priority = normalize_priority(payload.get("banPriority"))
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


def encode_settings_for_storage(normalized: dict) -> dict[str, str]:
    """Serialize validated settings for the existing config.ini writer."""
    stored: dict[str, str] = {}
    for key, value in normalized.items():
        if isinstance(value, bool):
            stored[key] = "true" if value else "false"
        elif isinstance(value, tuple):
            stored[key] = ",".join(str(item) for item in value)
        elif value is None:
            stored[key] = ""
        else:
            stored[key] = str(value)
    return stored


def config_payload(config: ClientAutomationConfig) -> dict:
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


def status_label(config: ClientAutomationConfig, phase: Optional[str]) -> str:
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


def status_payload(config: ClientAutomationConfig, phase: Optional[str]) -> dict:
    return {
        "phase": phase,
        "status": status_label(config, phase),
        "enabled": config.enabled,
    }


def normalize_queue_catalog(raw_queues) -> list[dict]:
    queues: list[dict] = []
    if not isinstance(raw_queues, list):
        return queues

    seen: set[int] = set()
    for item in raw_queues:
        if not isinstance(item, dict):
            continue
        queue_id = safe_positive_int(item.get("id") or item.get("queueId"))
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

    queues.sort(key=lambda item: (item["name"].lower(), item["id"]))
    return queues


def normalize_champion_catalog(raw_champions) -> list[dict]:
    if isinstance(raw_champions, dict):
        raw_champions = list(raw_champions.values())
    if not isinstance(raw_champions, list):
        return []

    champions: list[dict] = []
    seen: set[int] = set()
    for item in raw_champions:
        if not isinstance(item, dict):
            continue
        champion_id = safe_positive_int(item.get("id") or item.get("key"))
        name = item.get("name")
        if champion_id is None or not name or champion_id in seen:
            continue

        normalized = {
            "id": champion_id,
            "name": str(name),
        }
        title = item.get("title")
        if title:
            normalized["title"] = str(title)

        icon_path = (
            item.get("squarePortraitPath")
            or item.get("iconPath")
            or item.get("icon")
        )
        if isinstance(icon_path, str) and icon_path.strip():
            normalized["iconPath"] = icon_path.strip()

        champions.append(normalized)
        seen.add(champion_id)

    champions.sort(key=lambda item: item["name"].lower())
    return champions