#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic tests for Phase E Auto Pick."""

import unittest
from unittest.mock import patch

from automation.champ_select import ChampSelectAutomationController
from automation.config import ClientAutomationConfig, load_client_automation_config


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
    def __init__(self):
        self.current_session = None
        self.select_calls = []
        self.complete_calls = []
        self.reject_candidates = set()

    def champ_select_session(self):
        return self.current_session

    @staticmethod
    def active_local_champ_select_action(session, action_type=None):
        if not isinstance(session, dict):
            return None
        local = session.get("localPlayerCellId")
        for round_actions in session.get("actions") or []:
            for action in round_actions or []:
                if action.get("actorCellId") != local:
                    continue
                if action.get("completed") is True or action.get("isInProgress") is not True:
                    continue
                if action_type and action.get("type") != action_type:
                    continue
                return action
        return None

    @staticmethod
    def banned_champion_ids(session):
        bans = session.get("bans") or {}
        return set((bans.get("myTeamBans") or []) + (bans.get("theirTeamBans") or []))

    @staticmethod
    def selected_champion_ids(session):
        out = set()
        for side in ("myTeam", "theirTeam"):
            for member in session.get(side) or []:
                champion_id = member.get("championId") or 0
                if champion_id > 0:
                    out.add(champion_id)
        return out

    def select_champ_select_action(self, action_id, champion_id):
        self.select_calls.append((action_id, champion_id))
        if champion_id in self.reject_candidates:
            return FakeResponse(400)
        if self.current_session:
            action = self.active_local_champ_select_action(self.current_session, "pick")
            if action and action.get("id") == action_id:
                action["championId"] = champion_id
        return FakeResponse(204)

    def complete_champ_select_action(self, action_id):
        self.complete_calls.append(action_id)
        if self.current_session:
            action = self.active_local_champ_select_action(self.current_session, "pick")
            if action and action.get("id") == action_id:
                action["completed"] = True
                action["isInProgress"] = False
        return FakeResponse(204)


def make_session(*, champion_id=0, banned=(), ally_selected=(), action_id=11):
    my_team = [{"cellId": 1, "championId": champion_id}]
    my_team.extend(
        {"cellId": index + 2, "championId": value}
        for index, value in enumerate(ally_selected)
    )
    return {
        "localPlayerCellId": 1,
        "actions": [[{
            "id": action_id,
            "actorCellId": 1,
            "type": "pick",
            "isInProgress": True,
            "completed": False,
            "championId": champion_id,
        }]],
        "myTeam": my_team,
        "theirTeam": [],
        "bans": {"myTeamBans": list(banned), "theirTeamBans": []},
    }


class AutoPickControllerTests(unittest.TestCase):
    @staticmethod
    def enabled_config(priority=(234, 141, 56)):
        return ClientAutomationConfig(
            enabled=True,
            auto_pick_enabled=True,
            pick_priority=priority,
        )

    def make_controller(self, config=None):
        self.lcu = FakeLCU()
        self.timers = TimerFactory()
        chosen = config or self.enabled_config()
        self.controller = ChampSelectAutomationController(
            self.lcu,
            config_loader=lambda: chosen,
            timer_factory=self.timers,
        )
        self.controller.handle_phase_change("ChampSelect")
        return self.controller

    def send_session(self, session):
        self.lcu.current_session = session
        self.controller.handle_session_event({"data": session})

    def test_disabled_master_never_selects(self):
        controller = self.make_controller(
            ClientAutomationConfig(
                enabled=False,
                auto_pick_enabled=True,
                pick_priority=(234,),
            )
        )
        self.send_session(make_session())
        self.assertEqual(self.lcu.select_calls, [])
        self.assertEqual(self.timers.instances, [])

    def test_uses_first_available_fallback_then_completes_once(self):
        self.make_controller(self.enabled_config((234, 141, 56)))
        session = make_session(banned=(234,), ally_selected=(141,))
        self.send_session(session)

        self.assertEqual(self.lcu.select_calls, [(11, 56)])
        self.assertEqual(len(self.timers.instances), 1)
        timer = self.timers.instances[0]
        self.assertAlmostEqual(timer.delay, 0.35)
        self.assertTrue(timer.started)

        timer.fire()
        timer.fire()
        self.assertEqual(self.lcu.complete_calls, [11])

    def test_manual_selection_present_before_automation_wins(self):
        self.make_controller()
        self.send_session(make_session(champion_id=64))
        self.assertEqual(self.lcu.select_calls, [])
        self.assertEqual(self.lcu.complete_calls, [])

    def test_manual_change_during_completion_window_cancels(self):
        self.make_controller(self.enabled_config((234,)))
        session = make_session()
        self.send_session(session)
        timer = self.timers.instances[0]

        action = self.lcu.active_local_champ_select_action(session, "pick")
        action["championId"] = 64
        self.controller.handle_session_event({"data": session})

        self.assertTrue(timer.cancelled)
        timer.fire()
        self.assertEqual(self.lcu.complete_calls, [])
        self.assertEqual(self.lcu.select_calls, [(11, 234)])

    def test_duplicate_session_events_do_not_duplicate_selection(self):
        self.make_controller(self.enabled_config((234,)))
        session = make_session()
        self.send_session(session)
        self.controller.handle_session_event({"data": session})
        self.controller.handle_session_event({"data": session})

        self.assertEqual(self.lcu.select_calls, [(11, 234)])
        self.assertEqual(len(self.timers.instances), 1)

    def test_completed_action_is_not_retried_on_duplicate_event(self):
        self.make_controller(self.enabled_config((234,)))
        session = make_session()
        self.send_session(session)
        self.timers.instances[0].fire()

        # Synthetic duplicate/stale event after completion.
        self.controller.handle_session_event({"data": session})
        self.assertEqual(self.lcu.select_calls, [(11, 234)])
        self.assertEqual(self.lcu.complete_calls, [11])

    def test_no_available_priority_makes_no_mutation(self):
        self.make_controller(self.enabled_config((234, 141)))
        self.send_session(make_session(banned=(234,), ally_selected=(141,)))
        self.assertEqual(self.lcu.select_calls, [])
        self.assertEqual(self.timers.instances, [])

    def test_rejected_candidate_tries_next_configured_candidate(self):
        self.make_controller(self.enabled_config((234, 141)))
        self.lcu.reject_candidates.add(234)
        session = make_session()
        self.send_session(session)

        self.assertEqual(self.lcu.select_calls, [(11, 234), (11, 141)])
        self.assertEqual(len(self.timers.instances), 1)
        self.timers.instances[0].fire()
        self.assertEqual(self.lcu.complete_calls, [11])

    def test_leaving_champ_select_cancels_pending_pick(self):
        self.make_controller(self.enabled_config((234,)))
        self.send_session(make_session())
        timer = self.timers.instances[0]

        self.controller.handle_phase_change("InProgress")
        self.assertTrue(timer.cancelled)
        timer.fire()
        self.assertEqual(self.lcu.complete_calls, [])


class AutoPickConfigTests(unittest.TestCase):
    def test_loader_validates_and_deduplicates_pick_priority(self):
        values = {
            ("ClientAutomation", "enabled"): "true",
            ("ClientAutomation", "auto_pick_enabled"): "true",
            ("ClientAutomation", "pick_priority"): "234, bad, 141, 234, 0, -2, 56",
        }

        with patch(
            "automation.config.get_config_option",
            side_effect=lambda section, option: values.get((section, option)),
        ):
            config = load_client_automation_config()

        self.assertTrue(config.auto_pick_active)
        self.assertEqual(config.pick_priority, (234, 141, 56))

        with patch("automation.config.get_config_option", return_value=None):
            defaults = load_client_automation_config()

        self.assertFalse(defaults.auto_pick_enabled)
        self.assertEqual(defaults.pick_priority, ())
        self.assertFalse(defaults.auto_pick_active)


if __name__ == "__main__":
    unittest.main()
