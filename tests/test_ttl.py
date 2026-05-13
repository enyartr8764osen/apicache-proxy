"""Tests for apicache_proxy.ttl."""

from __future__ import annotations

import time
import email.utils

import pytest

from apicache_proxy.ttl import resolve, is_cacheable, DEFAULT_TTL


# ---------------------------------------------------------------------------
# resolve()
# ---------------------------------------------------------------------------

def test_explicit_ttl_wins_over_headers():
    headers = {"Cache-Control": "max-age=60"}
    assert resolve(headers, explicit_ttl=120) == 120


def test_explicit_ttl_zero_is_respected():
    assert resolve({}, explicit_ttl=0) == 0


def test_explicit_ttl_negative_clamped_to_zero():
    assert resolve({}, explicit_ttl=-10) == 0


def test_max_age_parsed_from_cache_control():
    headers = {"Cache-Control": "public, max-age=45"}
    assert resolve(headers) == 45


def test_max_age_case_insensitive_header_key():
    headers = {"cache-control": "max-age=30"}
    assert resolve(headers) == 30


def test_max_age_zero_clamped():
    headers = {"Cache-Control": "max-age=0"}
    assert resolve(headers) == 0


def test_expires_header_used_when_no_max_age():
    future = time.time() + 200
    expires_str = email.utils.formatdate(future, usegmt=True)
    ttl = resolve({"Expires": expires_str})
    # Allow a couple of seconds of slack
    assert 195 <= ttl <= 205


def test_past_expires_header_returns_zero():
    past = time.time() - 100
    expires_str = email.utils.formatdate(past, usegmt=True)
    assert resolve({"Expires": expires_str}) == 0


def test_invalid_expires_falls_back_to_default():
    assert resolve({"Expires": "not-a-date"}) == DEFAULT_TTL


def test_no_headers_returns_default_ttl():
    assert resolve({}) == DEFAULT_TTL


def test_custom_default_ttl_used_as_fallback():
    assert resolve({}, default_ttl=999) == 999


# ---------------------------------------------------------------------------
# is_cacheable()
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("directive", ["no-store", "no-cache", "private"])
def test_non_cacheable_directives(directive):
    assert is_cacheable({"Cache-Control": directive}) is False


def test_public_max_age_is_cacheable():
    assert is_cacheable({"Cache-Control": "public, max-age=60"}) is True


def test_empty_headers_is_cacheable():
    assert is_cacheable({}) is True
