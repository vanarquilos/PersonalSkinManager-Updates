#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic coverage for Phase G settings bridge and queue role adapter."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from automation.config import ClientAutomationConfig
from automation.lcu_adapter import AutomationLCUAdapter
from pengu.communication.client_automation_message_handler import (
    ClientAutomationMessageHandler,
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


class FakeCatalogLCU:
    ok = True

    def matchmaking_lobby(self):
        return {"gameConfig": {"queueId": 420}}

    def get(self, path, timeout=1.0):
        if path == "/lol-game-queues/v1/queues":
            return [
                {"id": 420, "name": "Ranked Solo/Duo", "isVisible": True},
                {"id": 450, "name": "ARAM", "isVisible": True},
                {"id": 999, "name": "Hidden", "isVisible": False},
            ]
        if path == "/lol-game-data/assets/v1/champions.json":
            return [
                {"id": 234, "name": "Viego"},
                {"id": 141, "name": "Kayn"},
            ]
        return None


class ClientAutomationSettingsBridgeTests(unittest.TestCase):
    def make_handler(self, *, phase="Lobby", lcu=None):
        handler = ClientAutomationMessageHandler.__new__(ClientAutomationMessageHandler)
        handler.shared_state = SimpleNamespace(phase=phase)
        handler.skin_scraper = SimpleNamespace(lcu=lcu) if lcu is not None else None
        handler.sent = []
        handler._send_response = lambda message: handler.sent.append(json.loads(message))
        return handler

    def test_normalizer_requires_queue_and_valid_role_pair(self):
        with self.assertRaisesRegex(ValueError, "Choose a queue"):
            ClientAutomationMessageHandler._normalize_settings_payload({
                "enabled": True,
                "autoQueueEnabled": True,
                "queueId": None,
            })

        with self.assertRaisesRegex(ValueError, "both primary and secondary"):
            ClientAutomationMessageHandler._normalize_settings_payload({
                "primaryPosition": "JUNGLE",
                "secondaryPosition": None,
            })

        with self.assertRaisesRegex(ValueError, "must be different"):
            ClientAutomationMessageHandler._normalize_settings_payload({
                "primaryPosition": "TOP",
                "secondaryPosition": "TOP",
            })

    def test_normalizer_validates_priorities_and_preserves_order(self):
        result = ClientAutomationMessageHandler._normalize_settings_payload({
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

    def test_save_persists_dedicated_client_automation_section(self):
        handler = self.make_handler()
        saved = {}
        loaded = ClientAutomationConfig(
            enabled=True,
            auto_queue_enabled=True,
            queue_id=420,
            auto_accept_enabled=True,
            auto_accept_delay_ms=1000,
            auto_requeue_enabled=False,
            auto_pick_enabled=True,
            pick_priority=(234,),
            auto_ban_enabled=True,
            ban_priority=(33,),
            protect_ally_intents=True,
        )

        payload = {
            "enabled": True,
            "autoQueueEnabled": True,
            "queueId": 420,
            "primaryPosition": None,
            "secondaryPosition": None,
            "autoAcceptEnabled": True,
            "autoAcceptDelayMs": 1000,
            "autoRequeueEnabled": False,
            "autoPickEnabled": True,
            "pickPriority": [234],
            "autoBanEnabled": True,
            "banPriority": [33],
            "protectAllyIntents": True,
        }

        with patch(
            "pengu.communication.client_automation_message_handler.set_config_option",
            side_effect=lambda section, key, value: saved.__setitem__((section, key), value),
        ), patch(
            "pengu.communication.client_automation_message_handler.load_client_automation_config",
            return_value=loaded,
        ):
            handler._handle_client_automation_settings_save(payload)

        self.assertEqual(saved[("ClientAutomation", "enabled")], "true")
        self.assertEqual(saved[("ClientAutomation", "queue_id")], "420")
        self.assertEqual(saved[("ClientAutomation", "pick_priority")], "234")
        self.assertEqual(saved[("ClientAutomation", "ban_priority")], "33")
        self.assertTrue(handler.sent[-1]["success"])
        self.assertEqual(handler.sent[-1]["type"], "client-automation-settings-saved")

    def test_status_uses_shared_gameflow_phase(self):
        handler = self.make_handler(phase="ReadyCheck")
        config = ClientAutomationConfig(enabled=True)

        with patch(
            "pengu.communication.client_automation_message_handler.load_client_automation_config",
            return_value=config,
        ):
            handler._handle_client_automation_status_request()

        self.assertEqual(handler.sent[-1]["status"], "Match found")
        self.assertEqual(handler.sent[-1]["phase"], "ReadyCheck")

    def test_catalog_is_normalized_from_current_lcu_data(self):
        handler = self.make_handler(lcu=FakeCatalogLCU())

        handler._handle_client_automation_catalog_request()

        payload = handler.sent[-1]
        self.assertEqual(payload["type"], "client-automation-catalog-data")
        self.assertEqual(payload["currentQueueId"], 420)
        self.assertEqual(
            {item["id"] for item in payload["queues"]},
            {420, 450},
        )
        self.assertEqual(
            [item["name"] for item in payload["champions"]],
            ["Kayn", "Viego"],
        )


if __name__ == "__main__":
    unittest.main()
