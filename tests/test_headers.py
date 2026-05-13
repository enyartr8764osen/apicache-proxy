"""Tests for apicache_proxy.headers."""

import pytest

from apicache_proxy.headers import (
    filter_hop_by_hop,
    headers_for_cache_key,
    normalise,
)


# ---------------------------------------------------------------------------
# filter_hop_by_hop
# ---------------------------------------------------------------------------


def test_filter_hop_by_hop_removes_connection():
    result = filter_hop_by_hop({"Connection": "keep-alive", "Content-Type": "application/json"})
    assert "Connection" not in result
    assert result["Content-Type"] == "application/json"


def test_filter_hop_by_hop_case_insensitive():
    result = filter_hop_by_hop({"Transfer-Encoding": "chunked", "Accept": "*/*"})
    assert "Transfer-Encoding" not in result
    assert "Accept" in result


def test_filter_hop_by_hop_empty_input():
    assert filter_hop_by_hop({}) == {}


def test_filter_hop_by_hop_all_hop_headers_removed():
    hop_headers = {
        "Connection": "x",
        "Keep-Alive": "x",
        "Proxy-Authenticate": "x",
        "Proxy-Authorization": "x",
        "TE": "x",
        "Trailers": "x",
        "Transfer-Encoding": "x",
        "Upgrade": "x",
    }
    assert filter_hop_by_hop(hop_headers) == {}


# ---------------------------------------------------------------------------
# normalise
# ---------------------------------------------------------------------------


def test_normalise_lowercases_keys():
    result = normalise({"Content-Type": "application/json", "X-Custom": "val"})
    assert "content-type" in result
    assert "x-custom" in result


def test_normalise_strips_whitespace():
    result = normalise({"  Accept  ": "  text/html  "})
    assert result["accept"] == "text/html"


# ---------------------------------------------------------------------------
# headers_for_cache_key
# ---------------------------------------------------------------------------


def test_headers_for_cache_key_excludes_user_agent():
    headers = {"User-Agent": "test-agent", "Authorization": "Bearer tok"}
    result = headers_for_cache_key(headers)
    assert "user-agent" not in result
    assert result["authorization"] == "Bearer tok"


def test_headers_for_cache_key_is_sorted():
    headers = {"Z-Header": "z", "A-Header": "a", "M-Header": "m"}
    keys = list(headers_for_cache_key(headers).keys())
    assert keys == sorted(keys)


def test_headers_for_cache_key_extra_exclude():
    headers = {"Authorization": "secret", "Accept": "application/json"}
    result = headers_for_cache_key(headers, extra_exclude=["Authorization"])
    assert "authorization" not in result
    assert result["accept"] == "application/json"


def test_headers_for_cache_key_empty():
    assert headers_for_cache_key({}) == {}
