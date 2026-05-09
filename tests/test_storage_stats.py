"""Tests for DiskStorage.clear() and DiskStorage.stats()."""

import json
import time
import pytest
from pathlib import Path

from apicache_proxy.storage import DiskStorage
from apicache_proxy.cache import CacheEntry


@pytest.fixture
def storage(tmp_path):
    return DiskStorage(cache_dir=str(tmp_path / "cache"))


def _make_entry(body: dict, ttl: int = 60) -> CacheEntry:
    return CacheEntry(
        url="https://api.example.com/items",
        method="GET",
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=body,
        ttl=ttl,
    )


def test_clear_removes_all_entries(storage):
    storage.set("key1", _make_entry({"a": 1}))
    storage.set("key2", _make_entry({"b": 2}))
    storage.set("key3", _make_entry({"c": 3}))
    removed = storage.clear()
    assert removed == 3
    assert storage.get("key1") is None
    assert storage.get("key2") is None


def test_clear_empty_cache_returns_zero(storage):
    assert storage.clear() == 0


def test_stats_empty_cache(storage):
    stats = storage.stats()
    assert stats["total_entries"] == 0
    assert stats["valid_entries"] == 0
    assert stats["expired_entries"] == 0
    assert stats["total_size_bytes"] == 0


def test_stats_with_valid_entries(storage):
    storage.set("k1", _make_entry({"x": 1}, ttl=300))
    storage.set("k2", _make_entry({"y": 2}, ttl=300))
    stats = storage.stats()
    assert stats["total_entries"] == 2
    assert stats["valid_entries"] == 2
    assert stats["expired_entries"] == 0
    assert stats["total_size_bytes"] > 0


def test_stats_counts_expired_entries(storage):
    entry = _make_entry({"z": 99}, ttl=1)
    storage.set("expired_key", entry)
    # Manually rewrite with past timestamp
    path = storage._entry_path("expired_key")
    data = json.loads(path.read_text())
    data["expires_at"] = time.time() - 10
    path.write_text(json.dumps(data))

    storage.set("valid_key", _make_entry({"ok": True}, ttl=300))
    stats = storage.stats()
    assert stats["total_entries"] == 2
    assert stats["expired_entries"] == 1
    assert stats["valid_entries"] == 1


def test_stats_cache_dir_is_reported(storage):
    stats = storage.stats()
    assert "cache" in stats["cache_dir"]
