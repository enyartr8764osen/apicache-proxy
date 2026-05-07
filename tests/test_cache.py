"""Tests for the FileCache module."""

import os
import time
import tempfile
import pytest

from apicache_proxy.cache import FileCache, CacheEntry


@pytest.fixture
def cache(tmp_path):
    return FileCache(cache_dir=str(tmp_path), ttl=10)


def test_cache_miss_returns_none(cache):
    result = cache.get("GET", "https://api.example.com/data")
    assert result is None


def test_cache_set_and_get(cache):
    cache.set(
        method="GET",
        url="https://api.example.com/data",
        status_code=200,
        headers={"Content-Type": "application/json"},
        body='{"key": "value"}',
    )
    entry = cache.get("GET", "https://api.example.com/data")
    assert entry is not None
    assert entry.status_code == 200
    assert entry.body == '{"key": "value"}'
    assert entry.headers["Content-Type"] == "application/json"


def test_cache_key_is_method_and_url_sensitive(cache):
    cache.set("GET", "https://api.example.com/a", 200, {}, "body-a")
    cache.set("POST", "https://api.example.com/a", 201, {}, "body-post")

    get_entry = cache.get("GET", "https://api.example.com/a")
    post_entry = cache.get("POST", "https://api.example.com/a")

    assert get_entry.body == "body-a"
    assert post_entry.body == "body-post"


def test_expired_entry_returns_none(tmp_path):
    cache = FileCache(cache_dir=str(tmp_path), ttl=1)
    cache.set("GET", "https://api.example.com/ttl", 200, {}, "data")
    time.sleep(1.1)
    result = cache.get("GET", "https://api.example.com/ttl")
    assert result is None


def test_cache_clear(cache):
    cache.set("GET", "https://api.example.com/1", 200, {}, "one")
    cache.set("GET", "https://api.example.com/2", 200, {}, "two")
    removed = cache.clear()
    assert removed == 2
    assert cache.get("GET", "https://api.example.com/1") is None


def test_cache_entry_not_expired():
    entry = CacheEntry(200, {}, "body", time.time(), ttl=60)
    assert not entry.is_expired()


def test_cache_entry_expired():
    entry = CacheEntry(200, {}, "body", time.time() - 100, ttl=10)
    assert entry.is_expired()


def test_cache_creates_directory(tmp_path):
    cache_dir = str(tmp_path / "nested" / "cache")
    cache = FileCache(cache_dir=cache_dir, ttl=60)
    assert os.path.isdir(cache_dir)
