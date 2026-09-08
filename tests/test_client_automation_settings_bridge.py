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

    def test_catalog_normalizers_filter_hidden_sort_and_preserve_display_metadata(self):
        queues = normalize_queue_catalog([
            {"id": 420, "name": "Ranked Solo/Duo", "isVisible": True},
            {"id": 450, "name": "ARAM", "isVisible": True},
            {"id": 999, "name": "Hidden", "isVisible": False},
            {"id": 450, "name": "Duplicate", "isVisible": True},
        ])
        champions = normalize_champion_catalog([
            {
                "id": 234,
                "name": "Viego",
                "title": "The Ruined King",
                "squarePortraitPath": "/lol-game-data/assets/v1/champion-icons/234.png",
            },
            {"id": 141, "name": "Kayn"},
            {"id": 141, "name": "Duplicate Kayn"},
            {"id": 0, "name": "Invalid"},
        ])

        self.assertEqual([item["id"] for item in queues], [450, 420])
        self.assertEqual([item["name"] for item in champions], ["Kayn", "Viego"])
        viego = next(item for item in champions if item["id"] == 234)
        self.assertEqual(viego["title"], "The Ruined King")
        self.assertEqual(
            viego["iconPath"],
            "/lol-game-data/assets/v1/champion-icons/234.png",
        )

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