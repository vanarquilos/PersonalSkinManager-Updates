#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic tests for the Phase C Auto Accept controller."""

import unittest
from unittest.mock import patch

from automation.config import ClientAutomationConfig, load_client_automation_config
from automation.controller import AutomationController


class FakeResponse:
    def __init__(self, status_code=204):
        self.status_code = status_code


class FakeLCU:
    def __init__(self):
        self.current_ready_check = {"state": "InProgress", "playerResponse": "None"}
        self.accept_calls = 0
        self.ready_check_reads = 0
        self.accept_response = FakeResponse(204)

    @staticmethod
    def ready_check_is_actionable(state):
        return (
            isinstance(state, dict)
            and state.get("state") == "InProgress"
            and state.get("playerResponse") in (None, "None")
        )

    def ready_check(self):
        self.ready_check_reads += 1
        return self.current_ready_check

    def accept_ready_check(self):
        self.accept_calls += 1
        return self.accept_response


class FakeTimer:
    def __init__(self, delay, callback, args=()):
        self.delay = delay
        self.callback = callback
        self.args = args
        self.started = False
        self.cancelled = False
        self.daemon = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        if not self.cancelled:
            self.callback(*self.args)


class TimerFactory:
    def __init__(self):
        self.instances = []

    def __call__(self, delay, callback, args=()):
        timer = FakeTimer(delay, callback, args)
        self.instances.append(timer)
        return timer


class AutoAcceptControllerTests(unittest.TestCase):
    @staticmethod
    def enabled_config(delay_ms=1000):
        return ClientAutomationConfig(
            enabled=True,
            auto_accept_enabled=True,
            auto_accept_delay_ms=delay_ms,
        )

    def make_controller(self, config=None):
        self.lcu = FakeLCU()
        self.timers = TimerFactory()
        chosen = config or self.enabled_config()
        self.controller = AutomationController(
            self.lcu,
            config_loader=lambda: chosen,
            timer_factory=self.timers,
        )
        return self.controller

    def test_disabled_master_never_schedules(self):
        controller = self.make_controller(
            ClientAutomationConfig(
                enabled=False,
                auto_accept_enabled=True,
                auto_accept_delay_ms=1000,
            )
        )

        controller.handle_ready_check_event(
            {"data": {"state": "InProgress", "playerResponse": "None"}}
        )

        self.assertEqual(self.timers.instances, [])
        self.assertEqual(self.lcu.accept_calls, 0)

    def test_actionable_event_schedules_once_and_honors_delay(self):
        controller = self.make_controller(self.enabled_config(2000))
        payload = {"data": {"state": "InProgress", "playerResponse": "None"}}

        controller.handle_ready_check_event(payload)
        controller.handle_ready_check_event(payload)

        self.assertEqual(len(self.timers.instances), 1)
        timer = self.timers.instances[0]
        self.assertTrue(timer.started)
        self.assertTrue(timer.daemon)
        self.assertEqual(timer.delay, 2.0)

    def test_timer_revalidates_then_accepts_exactly_once(self):
        controller = self.make_controller()
        payload = {"data": {"state": "InProgress", "playerResponse": "None"}}

        controller.handle_ready_check_event(payload)
        timer = self.timers.instances[0]
        timer.fire()
        timer.fire()

        self.assertEqual(self.lcu.ready_check_reads, 1)
        self.assertEqual(self.lcu.accept_calls, 1)

    def test_manual_response_during_delay_wins(self):
        controller = self.make_controller()
        controller.handle_ready_check_event(
            {"data": {"state": "InProgress", "playerResponse": "None"}}
        )
        timer = self.timers.instances[0]

        self.lcu.current_ready_check = {
            "state": "InProgress",
            "playerResponse": "Declined",
        }
        timer.fire()

        self.assertEqual(self.lcu.ready_check_reads, 1)
        self.assertEqual(self.lcu.accept_calls, 0)

    def test_non_actionable_event_cancels_pending_accept(self):
        controller = self.make_controller()
        controller.handle_ready_check_event(
            {"data": {"state": "InProgress", "playerResponse": "None"}}
        )
        timer = self.timers.instances[0]

        controller.handle_ready_check_event(
            {"data": {"state": "InProgress", "playerResponse": "Accepted"}}
        )

        self.assertTrue(timer.cancelled)
        timer.fire()
        self.assertEqual(self.lcu.accept_calls, 0)

    def test_ready_check_phase_reconciles_missed_event(self):
        controller = self.make_controller()

        controller.handle_phase_change("ReadyCheck")

        self.assertEqual(self.lcu.ready_check_reads, 1)
        self.assertEqual(len(self.timers.instances), 1)

    def test_leaving_ready_check_phase_cancels_pending_accept(self):
        controller = self.make_controller()
        controller.handle_ready_check_event(
            {"data": {"state": "InProgress", "playerResponse": "None"}}
        )
        timer = self.timers.instances[0]

        controller.handle_phase_change("ChampSelect")

        self.assertTrue(timer.cancelled)


class AutoAcceptConfigTests(unittest.TestCase):
    def test_loader_is_default_off_and_rejects_unknown_delay(self):
        values = {
            ("ClientAutomation", "enabled"): "true",
            ("ClientAutomation", "auto_accept_enabled"): "yes",
            ("ClientAutomation", "auto_accept_delay_ms"): "750",
        }

        with patch(
            "automation.config.get_config_option",
            side_effect=lambda section, option: values.get((section, option)),
        ):
            config = load_client_automation_config()

        self.assertTrue(config.enabled)
        self.assertTrue(config.auto_accept_enabled)
        self.assertEqual(config.auto_accept_delay_ms, 1000)

        with patch("automation.config.get_config_option", return_value=None):
            defaults = load_client_automation_config()

        self.assertFalse(defaults.enabled)
        self.assertFalse(defaults.auto_accept_enabled)
        self.assertEqual(defaults.auto_accept_delay_ms, 1000)


if __name__ == "__main__":
    unittest.main()
