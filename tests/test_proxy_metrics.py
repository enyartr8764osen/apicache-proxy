"""Tests that CachingProxy correctly records metrics on each request outcome."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from apicache_proxy.cache import Cache, CacheEntry
from apicache_proxy.metrics import Metrics
from apicache_proxy.proxy import CachingProxy


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture()
def cache() -> Cache:
    return Cache()


@pytest.fixture()
def metrics() -> Metrics:
    return Metrics()


@pytest.fixture()
def proxy(cache, metrics) -> CachingProxy:
    return CachingProxy(cache=cache, default_ttl=60, metrics=metrics)


def _mock_response(status: int = 200, body: str = '{"ok": true}') -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.text = body
    resp.headers = {"Content-Type": "application/json", "Cache-Control": "max-age=60"}
    resp.raise_for_status = MagicMock()
    return resp


# ------------------------------------------------------------------ #
# Tests
# ------------------------------------------------------------------ #

def test_miss_recorded_on_first_request(proxy, metrics):
    with patch("apicache_proxy.proxy.requests.request", return_value=_mock_response()):
        proxy.request("GET", "http://example.com/api")
    assert metrics.misses == 1
    assert metrics.hits == 0


def test_hit_recorded_on_cached_request(proxy, metrics, cache):
    with patch("apicache_proxy.proxy.requests.request", return_value=_mock_response()):
        proxy.request("GET", "http://example.com/api")
    with patch("apicache_proxy.proxy.requests.request", return_value=_mock_response()):
        proxy.request("GET", "http://example.com/api")
    assert metrics.hits == 1
    assert metrics.misses == 1


def test_bypass_recorded_and_not_counted_as_miss(proxy, metrics):
    with patch("apicache_proxy.proxy.requests.request", return_value=_mock_response()):
        proxy.request("GET", "http://example.com/api", bypass_cache=True)
    assert metrics.bypasses == 1
    assert metrics.misses == 0


def test_error_recorded_on_network_failure(proxy, metrics):
    with patch(
        "apicache_proxy.proxy.requests.request",
        side_effect=requests.ConnectionError("down"),
    ):
        with pytest.raises(requests.ConnectionError):
            proxy.request("GET", "http://example.com/api")
    assert metrics.errors == 1


def test_total_and_hit_rate_after_mixed_requests(proxy, metrics):
    with patch("apicache_proxy.proxy.requests.request", return_value=_mock_response()):
        proxy.request("GET", "http://example.com/a")  # miss
        proxy.request("GET", "http://example.com/a")  # hit
        proxy.request("GET", "http://example.com/b")  # miss
    assert metrics.total == 3
    assert abs(metrics.hit_rate - 1 / 3) < 1e-9


def test_proxy_creates_default_metrics_when_none_given(cache):
    p = CachingProxy(cache=cache)
    assert isinstance(p.metrics, Metrics)


def test_proxy_uses_supplied_metrics_instance(cache, metrics):
    p = CachingProxy(cache=cache, metrics=metrics)
    assert p.metrics is metrics
