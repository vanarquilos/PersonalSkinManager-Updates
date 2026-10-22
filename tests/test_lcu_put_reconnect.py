#!/usr/bin/env python3
"""LCU reconnection regression checks for League Client restarts."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import requests

from lcu.core.lcu_api import LCUAPI


class LcuPutReconnectTests(unittest.TestCase):
    def test_retry_targets_refreshed_client_port_and_preserves_payload(self):
        old, new = Mock(), Mock()
        old.put.side_effect = requests.ConnectionError("client restarted")
        response = new.put.return_value
        connection = SimpleNamespace(ok=True, base="https://127.0.0.1:1000", session=old)

        def refresh(force=False):
            self.assertTrue(force)
            connection.base = "https://127.0.0.1:2000"
            connection.session = new

        connection.refresh_if_needed = Mock(side_effect=refresh)
        api = LCUAPI(connection)
        api._cache_put("/lol-champ-select/v1/session", {"stale": True}, 60)

        payload = [{"skinId": 1}]
        headers = {"X-Test": "value"}
        self.assertIs(
            api.put("/lol-champ-select/v1/session", payload, 2.5, headers),
            response,
        )
        old.put.assert_called_once_with(
            "https://127.0.0.1:1000/lol-champ-select/v1/session",
            json=payload,
            timeout=2.5,
            headers=headers,
        )
        new.put.assert_called_once_with(
            "https://127.0.0.1:2000/lol-champ-select/v1/session",
            json=payload,
            timeout=2.5,
            headers=headers,
        )
        self.assertEqual(api._cache, {})

    def test_retry_failure_returns_none(self):
        session = Mock()
        session.put.side_effect = requests.ConnectionError("offline")
        connection = SimpleNamespace(
            ok=True, base="https://127.0.0.1:1000",
            session=session, refresh_if_needed=Mock(),
        )
        self.assertIsNone(LCUAPI(connection).put("/resource", {}, 1))
        self.assertEqual(session.put.call_count, 2)


if __name__ == "__main__":
    unittest.main()
