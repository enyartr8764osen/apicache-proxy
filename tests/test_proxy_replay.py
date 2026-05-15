"""Tests for ReplayProxy."""
import pytest

from apicache_proxy.replay import ReplayEntry, ReplayLibrary
from apicache_proxy.proxy_replay import ReplayProxy


def _library(*pairs):
    """Build a library from (method, url, status, body) tuples."""
    lib = ReplayLibrary()
    for method, url, status, body in pairs:
        lib.record(ReplayEntry(method, url, status,
                               {"Content-Type": "application/json"}, body))
    return lib


@pytest.fixture
def proxy():
    lib = _library(
        ("GET", "https://api.example.com/items", 200, '[{"id": 1}]'),
        ("POST", "https://api.example.com/items", 201, '{"id": 2}'),
    )
    return ReplayProxy(lib)


def test_get_returns_recorded_response(proxy):
    resp = proxy.get("https://api.example.com/items")
    assert resp.status_code == 200


def test_response_body_accessible(proxy):
    resp = proxy.get("https://api.example.com/items")
    assert resp.json() == [{"id": 1}]


def test_post_returns_correct_status(proxy):
    resp = proxy.request("POST", "https://api.example.com/items")
    assert resp.status_code == 201


def test_strict_mode_raises_on_unknown(proxy):
    with pytest.raises(KeyError, match="No replay entry"):
        proxy.get("https://api.example.com/unknown")


def test_miss_count_increments_in_strict_mode():
    lib = ReplayLibrary()
    p = ReplayProxy(lib, strict=False)
    p.get("https://api.example.com/x")
    p.get("https://api.example.com/y")
    assert p.miss_count == 2


def test_non_strict_returns_404_on_unknown():
    lib = ReplayLibrary()
    p = ReplayProxy(lib, strict=False)
    resp = p.get("https://api.example.com/unknown")
    assert resp.status_code == 404


def test_headers_preserved(proxy):
    resp = proxy.get("https://api.example.com/items")
    assert resp.headers["Content-Type"] == "application/json"
