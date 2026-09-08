#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase H source-level invariants for Client Automation integration glue."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ClientAutomationHardeningTests(unittest.TestCase):
    def test_legacy_jade_auto_accept_is_inert(self):
        source = (ROOT / "Pengu Loader/plugins/ROSE-Jade/config/js/addons/AA.js").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("/lol-matchmaking/v1/ready-check/accept", source)
        self.assertNotIn("class RoseAA", source)
        self.assertNotIn("settingsUtils", source)
        self.assertNotIn("setInterval(", source)
        self.assertIn("Legacy Rose/Jade AutoAccept is disabled", source)

    def test_websocket_connection_invokes_open_consumer_after_subscription(self):
        source = (ROOT / "threads/websocket/websocket_connection.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('ws.send(\'[5,"OnJsonApiEvent"]\')', source)
        self.assertIn("if subscribed and self.on_open:", source)
        self.assertIn("self.on_open(ws)", source)

    def test_websocket_thread_cancels_and_reconciles_automation(self):
        source = (ROOT / "threads/core/websocket_thread.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("on_open=self._on_connection_open", source)
        self.assertIn("on_close=self._on_connection_close", source)
        self.assertIn('handle_phase_change("__Disconnected__")', source)
        self.assertIn("champ_select_automation_controller.reconcile_session()", source)
        self.assertIn("def handle_automation_settings_changed", source)
        self.assertIn("def automation_status_snapshot", source)

    def test_settings_bridge_hot_reload_callback_is_wired(self):
        bridge = (
            ROOT / "pengu/communication/client_automation_message_handler.py"
        ).read_text(encoding="utf-8")
        bootstrap = (ROOT / "main/core/threads.py").read_text(encoding="utf-8")

        self.assertIn("self._notify_settings_changed()", bridge)
        self.assertIn("client_automation_settings_changed_callback", bridge)
        self.assertIn("client_automation_status_provider", bridge)
        self.assertIn(
            "state.client_automation_settings_changed_callback = t_ws.handle_automation_settings_changed",
            bootstrap,
        )
        self.assertIn(
            "state.client_automation_status_provider = t_ws.automation_status_snapshot",
            bootstrap,
        )

    def test_catalog_payload_reports_connection_and_availability(self):
        source = (
            ROOT / "pengu/communication/client_automation_message_handler.py"
        ).read_text(encoding="utf-8")

        self.assertIn('"leagueConnected": league_connected', source)
        self.assertIn('"queueCatalogAvailable": bool(queues)', source)
        self.assertIn('"championCatalogAvailable": bool(champions)', source)


if __name__ == "__main__":
    unittest.main()
