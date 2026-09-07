#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic tests for the Phase D Auto Queue / Auto Requeue controller."""

import copy
import unittest
from unittest.mock import patch

from automation.config import ClientAutomationConfig, load_client_automation_config
from automation.controller import AutomationController


class FakeResponse:
    def __init__(self, status_code=204):
        self.status_code = status_code


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


class FakeLCU:
    def __init__(self, lobby=None):
        self.lobby = lobby if lobby is not None else make_lobby()
        self.search_state = {
            "isCurrentlyInQueue": False,
            "searchState": "Invalid",
            "errors": [],
        }
        self.create_calls = []
        self.start_calls = 0
        self.lobby_reads = 0
        self.search_reads = 0

    # Auto Accept surface remains present because the same controller owns it.
    @staticmethod
    def ready_check_is_actionable(state):
        return False

    def ready_check(self):
        return None

    def accept_ready_check(self):
        return FakeResponse(204)

    def matchmaking_lobby(self):
        self.lobby_reads += 1
        return copy.deepcopy(self.lobby) if isinstance(self.lobby, dict) else self.lobby

    def matchmaking_search_state(self):
        self.search_reads += 1
        return copy.deepcopy(self.search_state)

    def create_matchmaking_lobby(self, queue_id):
        self.create_calls.append(int(queue_id))
        if not isinstance(self.lobby, dict):
            self.lobby = make_lobby(queue_id=int(queue_id), party_id="created-party")
        else:
            self.lobby = copy.deepcopy(self.lobby)
            self.lobby.setdefault("gameConfig", {})["queueId"] = int(queue_id)
        return FakeResponse(200)

    def start_matchmaking(self):
        self.start_calls += 1
        self.search_state = {
            "isCurrentlyInQueue": True,
            "searchState": "Searching",
            "errors": [],
        }
        return FakeResponse(204)


def make_lobby(
    *,
    queue_id=420,
    party_id="party-1",
    member_count=1,
    is_leader=True,
    can_start=True,
    allowed_start=True,
    allowed_change=True,
):
    members = []
    for index in range(member_count):
        members.append(
            {
                "puuid": f"member-{index}",
                "summonerId": 1000 + index,
                "isLeader": is_leader if index == 0 else False,
                "isLocalMember": index == 0,
            }
        )

    return {
        "partyId": party_id,
        "canStartActivity": can_start,
        "gameConfig": {"queueId": queue_id},
        "localMember": {
            "puuid": "member-0",
            "summonerId": 1000,
            "isLeader": is_leader,
            "allowedStartActivity": allowed_start,
            "allowedChangeActivity": allowed_change,
        },
        "members": members,
        "restrictions": [],
    }


class AutoQueueControllerTests(unittest.TestCase):
    @staticmethod
    def config(*, auto_queue=True, auto_requeue=False, queue_id=420):
        return ClientAutomationConfig(
            enabled=True,
            auto_queue_enabled=auto_queue,
            queue_id=queue_id,
            auto_requeue_enabled=auto_requeue,
        )

    def make_controller(self, config=None, lobby=None):
        self.lcu = FakeLCU(lobby=lobby)
        self.timers = TimerFactory()
        chosen = config or self.config()
        self.controller = AutomationController(
            self.lcu,
            config_loader=lambda: chosen,
            timer_factory=self.timers,
        )
        return self.controller

    def fire_last_timer(self):
        self.assertTrue(self.timers.instances)
        timer = self.timers.instances[-1]
        self.assertTrue(timer.started)
        timer.fire()
        return timer

    def test_valid_solo_lobby_auto_queues_once(self):
        controller = self.make_controller()

        controller.handle_phase_change("Lobby")
        timer = self.fire_last_timer()

        self.assertEqual(timer.delay, 0.0)
        self.assertEqual(self.lcu.start_calls, 1)

        # Same lobby events while search is active cannot duplicate the POST.
        controller.handle_lobby_event({"data": make_lobby()})
        self.assertEqual(len(self.timers.instances), 1)
        self.assertEqual(self.lcu.start_calls, 1)

    def test_already_matchmaking_does_not_start_again(self):
        controller = self.make_controller()
        self.lcu.search_state = {
            "isCurrentlyInQueue": True,
            "searchState": "Searching",
            "errors": [],
        }

        controller.handle_phase_change("Lobby")
        self.fire_last_timer()

        self.assertEqual(self.lcu.start_calls, 0)

    def test_premade_non_leader_never_starts_search(self):
        controller = self.make_controller(
            lobby=make_lobby(member_count=2, is_leader=False)
        )

        controller.handle_phase_change("Lobby")
        self.fire_last_timer()

        self.assertEqual(self.lcu.start_calls, 0)

    def test_blocking_penalty_suppresses_same_lobby(self):
        controller = self.make_controller()
        self.lcu.search_state = {
            "isCurrentlyInQueue": False,
            "searchState": "Error",
            "errors": [
                {
                    "errorType": "QUEUE_DODGER",
                    "message": "Penalty active",
                    "penaltyTimeRemaining": 120,
                }
            ],
        }

        controller.handle_phase_change("Lobby")
        self.fire_last_timer()
        self.assertEqual(self.lcu.start_calls, 0)

        # A duplicate event for the same material lobby must not create a retry loop.
        controller.handle_lobby_event({"data": make_lobby()})
        self.assertEqual(len(self.timers.instances), 1)

    def test_manual_cancel_does_not_immediately_requeue(self):
        controller = self.make_controller()

        controller.handle_phase_change("Lobby")
        self.fire_last_timer()
        self.assertEqual(self.lcu.start_calls, 1)

        controller.handle_phase_change("Matchmaking")
        self.lcu.search_state = {
            "isCurrentlyInQueue": False,
            "searchState": "Invalid",
            "errors": [],
        }
        controller.handle_phase_change("Lobby")

        self.assertEqual(len(self.timers.instances), 1)
        self.assertEqual(self.lcu.start_calls, 1)

    def test_material_lobby_change_recovers_after_manual_cancel(self):
        controller = self.make_controller()

        controller.handle_phase_change("Lobby")
        self.fire_last_timer()
        controller.handle_phase_change("Matchmaking")
        self.lcu.search_state = {
            "isCurrentlyInQueue": False,
            "searchState": "Invalid",
            "errors": [],
        }
        controller.handle_phase_change("Lobby")

        changed = make_lobby(party_id="party-2")
        self.lcu.lobby = changed
        controller.handle_lobby_event({"data": changed})
        self.assertEqual(len(self.timers.instances), 2)
        self.fire_last_timer()

        self.assertEqual(self.lcu.start_calls, 2)

    def test_post_game_requeues_when_auto_requeue_enabled(self):
        controller = self.make_controller(
            config=self.config(auto_queue=False, auto_requeue=True)
        )

        controller.handle_phase_change("InProgress")
        controller.handle_phase_change("EndOfGame")
        controller.handle_phase_change("Lobby")
        self.fire_last_timer()

        self.assertEqual(self.lcu.start_calls, 1)

    def test_post_game_does_not_use_auto_queue_as_requeue(self):
        controller = self.make_controller(
            config=self.config(auto_queue=True, auto_requeue=False)
        )

        controller.handle_phase_change("InProgress")
        controller.handle_phase_change("EndOfGame")
        controller.handle_phase_change("Lobby")

        self.assertEqual(self.timers.instances, [])
        self.assertEqual(self.lcu.start_calls, 0)

    def test_solo_lobby_can_switch_to_configured_queue_then_start(self):
        controller = self.make_controller(
            lobby=make_lobby(queue_id=430, member_count=1)
        )

        controller.handle_phase_change("Lobby")
        self.fire_last_timer()

        self.assertEqual(self.lcu.create_calls, [420])
        self.assertEqual(self.lcu.start_calls, 1)

    def test_premade_queue_is_never_silently_changed(self):
        controller = self.make_controller(
            lobby=make_lobby(queue_id=430, member_count=2, is_leader=True)
        )

        controller.handle_phase_change("Lobby")
        self.fire_last_timer()

        self.assertEqual(self.lcu.create_calls, [])
        self.assertEqual(self.lcu.start_calls, 0)

    def test_no_lobby_creates_configured_solo_lobby_then_starts(self):
        controller = self.make_controller(lobby=None)
        self.lcu.lobby = None

        controller.handle_phase_change("Lobby")
        self.fire_last_timer()

        self.assertEqual(self.lcu.create_calls, [420])
        self.assertEqual(self.lcu.start_calls, 1)


class AutoQueueConfigTests(unittest.TestCase):
    def test_loader_validates_queue_and_position_settings(self):
        values = {
            ("ClientAutomation", "enabled"): "true",
            ("ClientAutomation", "auto_queue_enabled"): "yes",
            ("ClientAutomation", "queue_id"): "420",
            ("ClientAutomation", "primary_position"): "jungle",
            ("ClientAutomation", "secondary_position"): "middle",
            ("ClientAutomation", "auto_requeue_enabled"): "on",
        }

        with patch(
            "automation.config.get_config_option",
            side_effect=lambda section, option: values.get((section, option)),
        ):
            config = load_client_automation_config()

        self.assertTrue(config.auto_queue_active)
        self.assertTrue(config.auto_requeue_active)
        self.assertEqual(config.queue_id, 420)
        self.assertEqual(config.primary_position, "JUNGLE")
        self.assertEqual(config.secondary_position, "MIDDLE")

        values[("ClientAutomation", "queue_id")] = "-1"
        values[("ClientAutomation", "primary_position")] = "INVALID"
        with patch(
            "automation.config.get_config_option",
            side_effect=lambda section, option: values.get((section, option)),
        ):
            invalid = load_client_automation_config()

        self.assertIsNone(invalid.queue_id)
        self.assertIsNone(invalid.primary_position)
        self.assertFalse(invalid.auto_queue_active)
        self.assertFalse(invalid.auto_requeue_active)


if __name__ == "__main__":
    unittest.main()
