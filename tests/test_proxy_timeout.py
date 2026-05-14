"""Tests for apicache_proxy.proxy_timeout."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from apicache_proxy.cache import InMemoryCache
from apicache_proxy.proxy import CachingProxy
from apicache_proxy.proxy_timeout import TimeoutProxy
from apicache_proxy.timeout import TimeoutConfig


def _make_proxy(connect=5.0, read=30.0):
    cache = InMemoryCache()
    inner = CachingProxy(cache=cache)
    cfg = TimeoutConfig(connect=connect, read=read)
    return TimeoutProxy(proxy=inner, timeout=cfg)


def _mock_response(status=200, body=b"ok"):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.headers = {"Content-Type": "text/plain"}
    resp.content = body
    return resp


def test_default_timeout_config_used_when_none_given():
    inner = CachingProxy(cache=InMemoryCache())
    tp = TimeoutProxy(proxy=inner)
    assert tp.timeout.connect == 5.0
    assert tp.timeout.read == 30.0


def test_custom_timeout_stored():
    proxy = _make_proxy(connect=2.0, read=10.0)
    assert proxy.timeout.as_tuple == (2.0, 10.0)


def test_timeout_injected_into_request():
    proxy = _make_proxy(connect=1.0, read=7.0)
    with patch("requests.Session.request", return_value=_mock_response()) as mock_req:
        proxy.get("http://example.com/api")
    _, kwargs = mock_req.call_args
    assert kwargs["timeout"] == (1.0, 7.0)


def test_caller_timeout_not_overridden_if_explicit():
    """If caller passes its own timeout, it should win (setdefault semantics)."""
    proxy = _make_proxy(connect=1.0, read=7.0)
    with patch("requests.Session.request", return_value=_mock_response()) as mock_req:
        proxy.request("GET", "http://example.com/api", timeout=(99.0, 99.0))
    _, kwargs = mock_req.call_args
    assert kwargs["timeout"] == (99.0, 99.0)


def test_requests_timeout_converted_to_timeout_error():
    proxy = _make_proxy(connect=0.1, read=0.1)
    with patch(
        "requests.Session.request",
        side_effect=requests.exceptions.Timeout("timed out"),
    ):
        with pytest.raises(TimeoutError, match="timed out"):
            proxy.get("http://slow.example.com/")


def test_timeout_error_message_includes_url():
    proxy = _make_proxy(connect=1.0, read=2.0)
    with patch(
        "requests.Session.request",
        side_effect=requests.exceptions.Timeout,
    ):
        with pytest.raises(TimeoutError, match="http://slow.example.com/"):
            proxy.get("http://slow.example.com/")


def test_stats_delegated_to_inner_proxy():
    inner = MagicMock()
    inner.stats.return_value = {"hits": 3}
    tp = TimeoutProxy(proxy=inner)
    assert tp.stats() == {"hits": 3}


def test_stats_returns_empty_dict_when_inner_has_no_stats():
    inner = MagicMock(spec=["request"])  # no stats attr
    tp = TimeoutProxy(proxy=inner)
    assert tp.stats() == {}
