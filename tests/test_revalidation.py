"""Tests for apicache_proxy.revalidation."""

from __future__ import annotations

import pytest

from apicache_proxy.cache import CacheEntry
from apicache_proxy.revalidation import (
    conditional_headers,
    handle_304,
    has_validators,
)


def _entry(
    status: int = 200,
    headers: dict | None = None,
    body: bytes = b"hello",
    ttl: int = 300,
) -> CacheEntry:
    return CacheEntry(
        status_code=status,
        response_headers=headers or {},
        body=body,
        ttl=ttl,
    )


# ---------------------------------------------------------------------------
# conditional_headers()
# ---------------------------------------------------------------------------

def test_etag_becomes_if_none_match():
    entry = _entry(headers={"ETag": '"abc123"'})
    result = conditional_headers(entry)
    assert result == {"If-None-Match": '"abc123"'}


def test_last_modified_becomes_if_modified_since():
    entry = _entry(headers={"Last-Modified": "Wed, 01 Jan 2025 00:00:00 GMT"})
    result = conditional_headers(entry)
    assert result == {"If-Modified-Since": "Wed, 01 Jan 2025 00:00:00 GMT"}


def test_both_validators_included():
    entry = _entry(headers={"ETag": '"x"', "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT"})
    result = conditional_headers(entry)
    assert "If-None-Match" in result
    assert "If-Modified-Since" in result


def test_no_validators_returns_empty_dict():
    entry = _entry(headers={"Content-Type": "application/json"})
    assert conditional_headers(entry) == {}


def test_header_key_matching_is_case_insensitive():
    entry = _entry(headers={"etag": '"lower"'})
    result = conditional_headers(entry)
    assert result["If-None-Match"] == '"lower"'


# ---------------------------------------------------------------------------
# handle_304()
# ---------------------------------------------------------------------------

def test_handle_304_preserves_body():
    cached = _entry(body=b"original body", headers={"ETag": '"v1"'})
    refreshed = handle_304(cached, {"ETag": '"v2"'}, new_ttl=60)
    assert refreshed.body == b"original body"


def test_handle_304_updates_etag():
    cached = _entry(headers={"ETag": '"v1"'})
    refreshed = handle_304(cached, {"ETag": '"v2"'}, new_ttl=60)
    assert refreshed.response_headers["ETag"] == '"v2"'


def test_handle_304_does_not_overwrite_content_length():
    cached = _entry(headers={"Content-Length": "5"})
    refreshed = handle_304(cached, {"content-length": "999"}, new_ttl=60)
    assert refreshed.response_headers["Content-Length"] == "5"


def test_handle_304_sets_new_ttl():
    cached = _entry(ttl=300)
    refreshed = handle_304(cached, {}, new_ttl=120)
    assert refreshed.ttl == 120


# ---------------------------------------------------------------------------
# has_validators()
# ---------------------------------------------------------------------------

def test_has_validators_true_with_etag():
    assert has_validators(_entry(headers={"ETag": '"abc"'})) is True


def test_has_validators_true_with_last_modified():
    assert has_validators(_entry(headers={"Last-Modified": "Thu, 01 Jan 2026 00:00:00 GMT"})) is True


def test_has_validators_false_without_validators():
    assert has_validators(_entry(headers={"Content-Type": "text/plain"})) is False
