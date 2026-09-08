#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic coverage for Phase G/H settings contract and queue role adapter."""

import unittest

from automation.config import ClientAutomationConfig
from automation.lcu_adapter import AutomationLCUAdapter
from automation.settings_contract import (
    config_payload,
    encode_settings_for_storage,
    normalize_champion_catalog,
    normalize_queue_catalog,
    normalize_settings_payload,
    status_payload,
)


class FakeResponse:
    def __init__(self, status_code=204):
        self.status_code = status_code


class FakeAutomationLCU:
    def __init__(self, role_status=204):
        self.role_status = role_status
        self.calls = []

    def set_matchmaking_position_preferences(self, primary, secondary):
        self.calls.append(("roles", primary, secondary))
        return FakeResponse(self.role_status)

    def start_matchmaking(self):
        self.calls.append(("start",))
        return FakeResponse(204)


class AutomationLCUAdapterTests(unittest.TestCase):
    def test_role_preferences_are_applied_before_search(self):
        lcu = FakeAutomationLCU()
        config = ClientAutomationConfig(
            enabled=True,
            auto_queue_enabled=True,
            queue_id=420,
            primary_position="JUNGLE",
            secondary_position="MIDDLE",
        )
        adapter = AutomationLCUAdapter(lcu, config_loader=lambda: config)

        response = adapter.start_matchmaking()

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            lcu.calls,
            [("roles", "JUNGLE", "MIDDLE"), ("start",)],
        )

    def test_role_rejection_fails_closed_without_starting_search(self):
        lcu = FakeAutomationLCU(role_status=400)
        config = ClientAutomationConfig(
            enabled=True,
            auto_queue_enabled=True,
            queue_id=420,
            primary_position="TOP",
            secondary_position="JUNGLE",
        )
        adapter = AutomationLCUAdapter(lcu, config_loader=lambda: config)

        response = adapter.start_matchmaking()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(lcu.calls, [("roles", "TOP", "JUNGLE")])

    def test_no_role_preferences_starts_search_directly(self):
        lcu = FakeAutomationLCU()
        config = ClientAutomationConfig(
            enabled=True,
            auto_queue_enabled=True,
            queue_id=450,
        )
        adapter = AutomationLCUAdapter(lcu, config_loader=lambda: config)

        response = adapter.start_matchmaking()

        self.assertEqual(response.status_code, 204)
        self.assertEqual(lcu.calls, [("start",)])


class ClientAutomationSettingsContractTests(unittest.TestCase):
    def test_normalizer_requires_queue_and_valid_role_pair(self):
        with self.assertRaisesRegex(ValueError, "Choose a queue"):
            normalize_settings_payload({
                "enabled": True,
                "autoQueueEnabled": True,
                "queueId": None,
            })

        with self.assertRaisesRegex(ValueError, "both primary and secondary"):
            normalize_settings_payload({
                "primaryPosition": "JUNGLE",
                "secondaryPosition": None,
            })

        with self.assertRaisesRegex(ValueError, "must be different"):
            normalize_settings_payload({
                "primaryPosition": "TOP",
                "secondaryPosition": "TOP",
            })

    def test_normalizer_validates_priorities_and_preserves_order(self):
        result = normalize_settings_payload({
            "enabled": True,
            "autoQueueEnabled": True,
            "queueId": 420,
            "primaryPosition": "JUNGLE",
            "secondaryPosition": "MIDDLE",
            "autoAcceptEnabled": True,
            "autoAcceptDelayMs": 500,
            "autoRequeueEnabled": True,
            "autoPickEnabled": True,
            "pickPriority": [234, 141, 234],
            "autoBanEnabled": True,
            "banPriority": [33, 64],
            "protectAllyIntents": True,
        })

        self.assertEqual(result["queue_id"], 420)
        self.assertEqual(result["primary_position"], "JUNGLE")
        self.assertEqual(result["secondary_position"], "MIDDLE")
        self.assertEqual(result["pick_priority"], (234, 141))
        self.assertEqual(result["ban_priority"], (33, 64))
        self.assertEqual(result["auto_accept_delay_ms"], 500)

    def test_storage_encoding_matches_existing_config_contract(self):
        normalized = normalize_settings_payload({
            "enabled": True,
            "autoQueueEnabled": True,
            "queueId": 420,
            "autoAcceptEnabled": True,
            "autoAcceptDelayMs": 1000,
            "autoPickEnabled": True,
            "pickPriority": [234, 141],
            "autoBanEnabled": True,
            "banPriority": [33],
            "protectAllyIntents": True,
        })

        stored = encode_settings_for_storage(normalized)

        self.assertEqual(stored["enabled"], "true")
        self.assertEqual(stored["queue_id"], "420")
        self.assertEqual(stored["pick_priority"], "234,141")
        self.assertEqual(stored["ban_priority"], "33")
        self.assertEqual(stored["primary_position"], "")
        self.assertEqual(stored["secondary_position"], "")

    def test_payload_and_status_keep_ui_contract_stable(self):
        config = ClientAutomationConfig(
            enabled=True,
            auto_queue_enabled=True,
            queue_id=420,
            auto_pick_enabled=True,
            pick_priority=(234,),
            auto_ban_enabled=True,
            ban_priority=(33,),
        )

        payload = config_payload(config)
        runtime = status_payload(config, "ReadyCheck")

        self.assertEqual(payload["queueId"], 420)
        self.assertEqual(payload["pickPriority"], [234])
        self.assertEqual(payload["banPriority"], [33])
        self.assertEqual(runtime["status"], "Match found")
        self.assertEqual(runtime["phase"], "ReadyCheck")

    def test_queue_catalog_keeps_only_usable_specific_matchmaking_choices(self):
        queues = normalize_queue_catalog([
            {
                "id": 420,
                "name": "CLASSIC",
                "type": "RANKED_SOLO_5x5",
                "description": "5v5 Ranked Solo games",
                "queueAvailability": "Available",
                "isVisible": True,
                "isRanked": True,
                "mapId": 11,
            },
            {
                "id": 440,
                "name": "CLASSIC RIFT",
                "type": "RANKED_FLEX_SR",
                "description": "5v5 Ranked Flex games",
                "queueAvailability": "Available",
                "isVisible": True,
                "isRanked": True,
                "mapId": 11,
            },
            {
                "id": 450,
                "name": "ARAM",
                "type": "ARAM_UNRANKED_5x5",
                "queueAvailability": "Available",
                "isVisible": True,
            },
            {
                "id": 2400,
                "name": "ARAM: Mayhem",
                "type": "ARAM_UNRANKED_5x5",
                "queueAvailability": "Available",
                "isVisible": True,
            },
            {
                "id": 3260,
                "name": "Classic (Custom Blind Pick)",
                "type": "CUSTOM",
                "queueAvailability": "Available",
                "isVisible": True,
                "isCustom": True,
            },
            {
                "id": 999,
                "name": "Hidden",
                "isVisible": False,
            },
            {
                "id": 998,
                "name": "Disabled",
                "queueAvailability": "PlatformDisabled",
                "isVisible": True,
            },
        ])

        self.assertEqual(
            [(item["id"], item["name"]) for item in queues],
            [
                (450, "ARAM"),
                (2400, "ARAM: Mayhem"),
                (440, "Ranked Flex"),
                (420, "Ranked Solo/Duo"),
            ],
        )
        ranked_solo = next(item for item in queues if item["id"] == 420)
        self.assertEqual(ranked_solo["queueType"], "RANKED SOLO 5x5")
        self.assertEqual(ranked_solo["description"], "5v5 Ranked Solo games")
        self.assertTrue(ranked_solo["isRanked"])

    def test_champion_catalog_labels_modern_and_league_classic_pairs(self):
        champions = normalize_champion_catalog([
            {
                "id": 89,
                "name": "Leona",
                "title": "The Radiant Dawn",
                "squarePortraitPath": "/lol-game-data/assets/v1/champion-icons/89.png",
            },
            {
                "id": 60089,
                "name": "Leona",
                "title": "The Radiant Dawn",
                "squarePortraitPath": "/lol-game-data/assets/v1/champion-icons/60089.png",
            },
            {"id": 29, "name": "Twitch", "title": "The Plague Rat"},
            {"id": 60029, "name": "Twitch", "title": "The Plague Rat"},
            {"id": 0, "name": "Invalid"},
        ])

        self.assertEqual(
            [(item["id"], item["variant"]) for item in champions],
            [(89, "modern"), (60089, "classic"), (29, "modern"), (60029, "classic")],
        )
        modern_leona = next(item for item in champions if item["id"] == 89)
        classic_leona = next(item for item in champions if item["id"] == 60089)
        self.assertEqual(modern_leona["title"], "Modern League · The Radiant Dawn")
        self.assertEqual(classic_leona["title"], "League Classic · The Radiant Dawn")
        self.assertEqual(classic_leona["canonicalId"], 89)
        self.assertEqual(
            modern_leona["iconPath"],
            "/lol-game-data/assets/v1/champion-icons/89.png",
        )

    def test_single_roster_champion_defaults_to_modern(self):
        champions = normalize_champion_catalog([
            {"id": 234, "name": "Viego", "title": "The Ruined King"},
        ])
        self.assertEqual(champions[0]["variant"], "modern")
        self.assertEqual(champions[0]["title"], "Modern League · The Ruined King")

    def test_enabled_pick_and_ban_require_priorities(self):
        with self.assertRaisesRegex(ValueError, "Auto Pick"):
            normalize_settings_payload({
                "enabled": True,
                "autoPickEnabled": True,
                "pickPriority": [],
            })

        with self.assertRaisesRegex(ValueError, "Auto Ban"):
            normalize_settings_payload({
                "enabled": True,
                "autoBanEnabled": True,
                "banPriority": [],
            })


if __name__ == "__main__":
    unittest.main()
