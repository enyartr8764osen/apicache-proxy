"""Integration tests: TimeoutProxy sitting in front of a real CachingProxy."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from apicache_proxy.cache import InMemoryCache
from apicache_proxy.proxy import CachingProxy
from apicache_proxy.proxy_timeout import TimeoutProxy
from apicache_proxy.timeout import TimeoutConfig


def _resp(status=200, body=b"hello", content_type="application/json"):
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.headers = {"Content-Type": content_type, "Cache-Control": "max-age=60"}
    r.content = body
    return r


@pytest.fixture()
def proxy():
    cache = InMemoryCache()
    inner = CachingProxy(cache=cache)
    return TimeoutProxy(proxy=inner, timeout=TimeoutConfig(connect=5.0, read=20.0))


def test_cache_hit_bypasses_network(proxy):
    """Second request should not touch the network at all."""
    with patch("requests.Session.request", return_value=_resp()) as mock_req:
        proxy.get("http://api.example.com/data")
        proxy.get("http://api.example.com/data")
    assert mock_req.call_count == 1


def test_timeout_applied_on_miss(proxy):
    with patch("requests.Session.request", return_value=_resp()) as mock_req:
        proxy.get("http://api.example.com/items")
    _, kwargs = mock_req.call_args
    assert kwargs["timeout"] == (5.0, 20.0)


def test_timeout_not_applied_on_cache_hit(proxy):
    """On a cache hit the inner proxy returns without calling Session.request."""
    with patch("requests.Session.request", return_value=_resp()) as mock_req:
        proxy.get("http://api.example.com/items")
        mock_req.reset_mock()
        proxy.get("http://api.example.com/items")
    mock_req.assert_not_called()


def test_timeout_error_propagates(proxy):
    with patch(
        "requests.Session.request",
        side_effect=requests.exceptions.Timeout,
    ):
        with pytest.raises(TimeoutError):
            proxy.get("http://api.example.com/slow")
