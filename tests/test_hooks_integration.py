"""Integration: hooks wired through the full proxy lifecycle."""
from unittest.mock import MagicMock, patch
import pytest

from apicache_proxy.hooks import HookRegistry
from apicache_proxy.proxy_hooks import HookedProxy
from apicache_proxy.cache import InMemoryCache


def _resp(status=200, body=b"hello"):
    r = MagicMock()
    r.status_code = status
    r.headers = {"Content-Type": "application/json"}
    r.content = body
    return r


def test_hooks_record_full_request_lifecycle():
    log = []
    reg = HookRegistry()
    reg.register_pre_request(lambda m, u, h: log.append(("pre", m, u)))
    reg.register_post_response(lambda m, u, s, c: log.append(("post", s, c)))

    proxy = HookedProxy(cache=InMemoryCache(), hooks=reg)

    with patch("apicache_proxy.proxy.requests.request", return_value=_resp(200)):
        proxy.request("GET", "http://api.example.com/v1/resource")

    assert log[0] == ("pre", "GET", "http://api.example.com/v1/resource")
    assert log[1] == ("post", 200, False)


def test_hooks_bypass_cache_always_fires_pre_hook():
    pre_calls = []
    reg = HookRegistry()
    reg.register_pre_request(lambda m, u, h: pre_calls.append(1))

    proxy = HookedProxy(cache=InMemoryCache(), hooks=reg)

    with patch("apicache_proxy.proxy.requests.request", return_value=_resp()):
        proxy.request("GET", "http://example.com/r")
        proxy.request("GET", "http://example.com/r", bypass_cache=True)

    assert len(pre_calls) == 2


def test_multiple_hooks_all_receive_same_data():
    a_log, b_log = [], []
    reg = HookRegistry()
    reg.register_post_response(lambda m, u, s, c: a_log.append(s))
    reg.register_post_response(lambda m, u, s, c: b_log.append(s))

    proxy = HookedProxy(cache=InMemoryCache(), hooks=reg)
    with patch("apicache_proxy.proxy.requests.request", return_value=_resp(404)):
        proxy.request("GET", "http://example.com/missing")

    assert a_log == [404]
    assert b_log == [404]


def test_clear_hooks_stops_recording():
    log = []
    reg = HookRegistry()
    reg.register_pre_request(lambda m, u, h: log.append(1))

    proxy = HookedProxy(cache=InMemoryCache(), hooks=reg)
    with patch("apicache_proxy.proxy.requests.request", return_value=_resp()):
        proxy.request("GET", "http://example.com/a")

    reg.clear()
    with patch("apicache_proxy.proxy.requests.request", return_value=_resp()):
        proxy.request("GET", "http://example.com/b")

    assert len(log) == 1  # only the call before clear
