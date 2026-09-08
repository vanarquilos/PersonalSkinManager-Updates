#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic tests for Client Automation LCU primitives."""

import unittest
from unittest.mock import Mock

import requests

from lcu.core.lcu_api import LCUAPI
from lcu.features.lcu_champ_select_automation import LCUChampSelectAutomation
from lcu.features.lcu_matchmaking import LCUMatchmaking
from lcu.features.lcu_ready_check import LCUReadyCheck


class FakeResponse:
    def __init__(self, status_code=204):
        self.status_code = status_code


class FakeFeatureAPI:
    def __init__(self):
        self.calls = []
        self.responses = {}

    def get(self, path, timeout=1.0, cache_ttl=None, use_cache=True):
        self.calls.append(("get", path, timeout, use_cache))
        return self.responses.get(path)

    def post(self, path, json_data=None, timeout=1.0, headers=None):
        self.calls.append(("post", path, json_data, timeout))
        return FakeResponse()

    def put(self, path, json_data, timeout=1.0, headers=None):
        self.calls.append(("put", path, json_data, timeout))
        return FakeResponse()

    def patch(self, path, json_data, timeout=1.0):
        self.calls.append(("patch", path, json_data, timeout))
        return FakeResponse()


class LCUAPIPostTests(unittest.TestCase):
    def test_post_sends_json_headers_and_invalidates_parent_cache(self):
        response = FakeResponse(201)
        session = Mock()
        session.post.return_value = response
        connection = Mock()
        connection.ok = True
        connection.base = "https://127.0.0.1:1234"
        connection.session = session

        api = LCUAPI(connection)
        api._cache["/lol-matchmaking/v1/ready-check"] = (
            float("inf"),
            {"state": "InProgress"},
        )

        result = api.post(
            "/lol-matchmaking/v1/ready-check/accept",
            {"source": "test"},
            timeout=2.0,
            headers={"X-Test": "1"},
        )

        self.assertIs(result, response)
        session.post.assert_called_once_with(
            "https://127.0.0.1:1234/lol-matchmaking/v1/ready-check/accept",
            json={"source": "test"},
            timeout=2.0,
            headers={"X-Test": "1"},
        )
        self.assertNotIn("/lol-matchmaking/v1/ready-check", api._cache)

    def test_post_refreshes_once_and_retries_against_new_base_url(self):
        response = FakeResponse(204)
        session = Mock()
        session.post.side_effect = [
            requests.ConnectionError("first attempt failed"),
            response,
        ]

        connection = Mock()
        connection.ok = True
        connection.base = "https://127.0.0.1:1111"
        connection.session = session

        def refresh(force=False):
            self.assertTrue(force)
            connection.base = "https://127.0.0.1:2222"
            connection.ok = True

        connection.refresh_if_needed.side_effect = refresh

        api = LCUAPI(connection)
        result = api.post("/example", timeout=1.0)

        self.assertIs(result, response)
        self.assertEqual(session.post.call_count, 2)
        self.assertEqual(
            session.post.call_args_list[0].args[0],
            "https://127.0.0.1:1111/example",
        )
        self.assertEqual(
            session.post.call_args_list[1].args[0],
            "https://127.0.0.1:2222/example",
        )


class ReadyCheckTests(unittest.TestCase):
    def test_ready_check_is_actionable_only_while_waiting_for_local_response(self):
        self.assertTrue(
            LCUReadyCheck.is_actionable(
                {"state": "InProgress", "playerResponse": "None"}
            )
        )
        self.assertTrue(
            LCUReadyCheck.is_actionable(
                {"state": "InProgress", "playerResponse": None}
            )
        )
        self.assertFalse(
            LCUReadyCheck.is_actionable(
                {"state": "InProgress", "playerResponse": "Accepted"}
            )
        )
        self.assertFalse(
            LCUReadyCheck.is_actionable(
                {"state": "EveryoneReady", "playerResponse": "None"}
            )
        )

    def test_accept_uses_ready_check_accept_endpoint(self):
        api = FakeFeatureAPI()
        feature = LCUReadyCheck(api)

        feature.accept()

        self.assertEqual(
            api.calls,
            [("post", "/lol-matchmaking/v1/ready-check/accept", None, 1.0)],
        )


class MatchmakingTests(unittest.TestCase):
    def test_create_lobby_requires_positive_queue_id(self):
        feature = LCUMatchmaking(FakeFeatureAPI())
        with self.assertRaises(ValueError):
            feature.create_lobby(0)

    def test_create_lobby_and_start_search_use_expected_endpoints(self):
        api = FakeFeatureAPI()
        feature = LCUMatchmaking(api)

        feature.create_lobby(420)
        feature.start_search()

        self.assertEqual(
            api.calls,
            [
                ("post", "/lol-lobby/v2/lobby", {"queueId": 420}, 2.0),
                ("post", "/lol-lobby/v2/lobby/matchmaking/search", None, 2.0),
            ],
        )

    def test_position_preferences_validate_and_use_expected_endpoint(self):
        api = FakeFeatureAPI()
        feature = LCUMatchmaking(api)

        feature.set_position_preferences("JUNGLE", "MIDDLE")

        self.assertEqual(
            api.calls,
            [
                (
                    "put",
                    "/lol-lobby/v2/lobby/members/localMember/position-preferences",
                    {"firstPreference": "JUNGLE", "secondPreference": "MIDDLE"},
                    1.5,
                )
            ],
        )

        with self.assertRaises(ValueError):
            feature.set_position_preferences("JUNGLE", "JUNGLE")
        with self.assertRaises(ValueError):
            feature.set_position_preferences("INVALID", "MIDDLE")


class ChampSelectAutomationTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeFeatureAPI()
        self.feature = LCUChampSelectAutomation(self.api)
        self.session = {
            "localPlayerCellId": 2,
            "myTeam": [
                {"cellId": 1, "championPickIntent": 64, "championId": 0},
                {"cellId": 2, "championPickIntent": 0, "championId": 11},
                {"cellId": 3, "championPickIntent": 0, "championId": 22},
            ],
            "theirTeam": [
                {"cellId": 5, "championId": 103},
            ],
            "bans": {
                "myTeamBans": [55],
                "theirTeamBans": [99],
            },
            "actions": [
                [
                    {
                        "id": 10,
                        "actorCellId": 2,
                        "type": "ban",
                        "championId": 55,
                        "completed": True,
                        "isInProgress": False,
                    }
                ],
                [
                    {
                        "id": 11,
                        "actorCellId": 2,
                        "type": "pick",
                        "championId": 0,
                        "completed": False,
                        "isInProgress": True,
                    }
                ],
            ],
        }

    def test_finds_only_active_local_action(self):
        action = self.feature.find_active_local_action(self.session, "pick")
        self.assertIsNotNone(action)
        self.assertEqual(action["id"], 11)
        self.assertIsNone(self.feature.find_active_local_action(self.session, "ban"))

    def test_collects_ally_intents_selected_and_banned_champions(self):
        self.assertEqual(
            self.feature.ally_intended_champion_ids(self.session),
            {64, 22},
        )
        self.assertEqual(
            self.feature.selected_champion_ids(self.session),
            {11, 22, 103},
        )
        self.assertEqual(
            self.feature.banned_champion_ids(self.session),
            {55, 99},
        )

    def test_select_and_complete_action_use_separate_mutations(self):
        self.feature.select_action(11, 234)
        self.feature.complete_action(11)

        self.assertEqual(
            self.api.calls,
            [
                (
                    "patch",
                    "/lol-champ-select/v1/session/actions/11",
                    {"championId": 234},
                    1.0,
                ),
                (
                    "post",
                    "/lol-champ-select/v1/session/actions/11/complete",
                    None,
                    1.0,
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
