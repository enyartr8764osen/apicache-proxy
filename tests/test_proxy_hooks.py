"""Tests for HookedProxy lifecycle hooks."""
from unittest.mock import MagicMock, patch
import pytest

from apicache_proxy.hooks import HookRegistry
from apicache_proxy.proxy_hooks import HookedProxy
from apicache_proxy.cache import InMemoryCache


def _mock_response(status=200, body=b"ok"):
    r = MagicMock()
    r.status_code = status
    r.headers = {"Content-Type": "text/plain"}
    r.content = body
    return r


@pytest.fixture()
def hooks():
    return HookRegistry()


@pytest.fixture()
def proxy(hooks):
    cache = InMemoryCache()
    return HookedProxy(cache=cache, hooks=hooks)


# ---------------------------------------------------------------------------
# pre_request hook
# ---------------------------------------------------------------------------

def test_pre_request_hook_fired_on_network_call(proxy, hooks):
    calls = []
    hooks.register_pre_request(lambda m, u, h: calls.append(m))

    with patch("apicache_proxy.proxy.requests.request", return_value=_mock_response()):
        proxy.request("GET", "http://example.com/data")

    assert calls == ["GET"]


def test_pre_request_hook_not_fired_on_cache_hit(proxy, hooks):
    calls = []
    hooks.register_pre_request(lambda m, u, h: calls.append(m))

    with patch("apicache_proxy.proxy.requests.request", return_value=_mock_response()):
        proxy.request("GET", "http://example.com/cached")
        proxy.request("GET", "http://example.com/cached")  # cache hit

    assert len(calls) == 1  # only the first (network) call


# ---------------------------------------------------------------------------
# post_response hook
# ---------------------------------------------------------------------------

def test_post_response_hook_fired_after_network_call(proxy, hooks):
    statuses = []
    hooks.register_post_response(lambda m, u, s, c: statuses.append(s))

    with patch("apicache_proxy.proxy.requests.request", return_value=_mock_response(201)):
        proxy.request("GET", "http://example.com/new")

    assert statuses == [201]


def test_post_response_hook_fired_on_cache_hit_with_cached_true(proxy, hooks):
    cached_flags = []
    hooks.register_post_response(lambda m, u, s, c: cached_flags.append(c))

    with patch("apicache_proxy.proxy.requests.request", return_value=_mock_response()):
        proxy.request("GET", "http://example.com/item")
        proxy.request("GET", "http://example.com/item")

    assert cached_flags == [False, True]


# ---------------------------------------------------------------------------
# Default (no hooks) still works
# ---------------------------------------------------------------------------

def test_hooked_proxy_without_hooks_works():
    cache = InMemoryCache()
    p = HookedProxy(cache=cache)  # no hooks kwarg
    with patch("apicache_proxy.proxy.requests.request", return_value=_mock_response()):
        resp = p.request("GET", "http://example.com/plain")
    assert resp.status_code == 200
