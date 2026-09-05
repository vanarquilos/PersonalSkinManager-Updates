#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security helpers for Rose's localhost bridge.
"""

from urllib.parse import urlparse


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def is_loopback_origin(origin: str | None) -> bool:
    """Return True only for browser origins hosted on the local machine."""
    if not origin:
        return False

    try:
        parsed = urlparse(origin)
    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    host = parsed.hostname
    if not host:
        return False

    return host.lower() in _LOOPBACK_HOSTS


def cors_headers_for_origin(origin: str | None) -> dict[str, str]:
    """Build CORS headers for an allowed loopback origin."""
    if not is_loopback_origin(origin):
        return {}

    return {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
    }
