"""Tests for DiskStorage persistence backend."""

import pytest
from datetime import datetime, timezone

from apicache_proxy.cache import CacheEntry
from apicache_proxy.storage import DiskStorage


@pytest.fixture
def storage(tmp_path):
    return DiskStorage(cache_dir=str(tmp_path / "test_cache"))


def _make_entry(ttl: int = 60) -> CacheEntry:
    return CacheEntry(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=b'{"key": "value"}',
        ttl=ttl,
        created_at=datetime.now(timezone.utc),
    )


def test_get_missing_key_returns_none(storage):
    assert storage.get("GET:https://example.com/missing") is None


def test_set_and_get_roundtrip(storage):
    key = "GET:https://example.com/data"
    entry = _make_entry()
    storage.set(key, entry)
    result = storage.get(key)
    assert result is not None
    assert result.status_code == 200
    assert result.body == b'{"key": "value"}'


def test_expired_entry_is_not_returned(storage):
    key = "GET:https://example.com/old"
    entry = _make_entry(ttl=0)
    storage.set(key, entry)
    # TTL=0 means immediately expired
    result = storage.get(key)
    assert result is None


def test_expired_entry_file_is_removed(storage, tmp_path):
    key = "GET:https://example.com/old"
    entry = _make_entry(ttl=0)
    storage.set(key, entry)
    assert storage.size() == 1
    storage.get(key)  # triggers removal
    assert storage.size() == 0


def test_delete_existing_key(storage):
    key = "GET:https://example.com/item"
    storage.set(key, _make_entry())
    assert storage.delete(key) is True
    assert storage.get(key) is None


def test_delete_nonexistent_key_returns_false(storage):
    assert storage.delete("GET:https://example.com/ghost") is False


def test_clear_removes_all_entries(storage):
    for i in range(3):
        storage.set(f"GET:https://example.com/item{i}", _make_entry())
    assert storage.size() == 3
    removed = storage.clear()
    assert removed == 3
    assert storage.size() == 0


def test_size_reflects_stored_entries(storage):
    assert storage.size() == 0
    storage.set("GET:https://example.com/a", _make_entry())
    storage.set("GET:https://example.com/b", _make_entry())
    assert storage.size() == 2
