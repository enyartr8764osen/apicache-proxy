"""Tests for ReplayEntry and ReplayLibrary."""
import json
import pytest
from pathlib import Path

from apicache_proxy.replay import ReplayEntry, ReplayLibrary


def _entry(method="GET", url="https://api.example.com/v1/items",
           status=200, headers=None, body='{"ok": true}'):
    return ReplayEntry(method, url, status, headers or {"Content-Type": "application/json"}, body)


def test_entry_to_dict_round_trips():
    e = _entry()
    assert ReplayEntry.from_dict(e.to_dict()).url == e.url


def test_entry_method_normalised_to_upper():
    e = ReplayEntry("get", "https://x.com", 200, {}, "")
    assert e.method == "GET"


def test_library_starts_empty():
    lib = ReplayLibrary()
    assert len(lib) == 0


def test_library_record_and_find():
    lib = ReplayLibrary()
    lib.record(_entry())
    found = lib.find("GET", "https://api.example.com/v1/items")
    assert found is not None
    assert found.status == 200


def test_library_find_returns_none_for_unknown():
    lib = ReplayLibrary()
    assert lib.find("GET", "https://missing.example.com") is None


def test_library_find_is_method_sensitive():
    lib = ReplayLibrary()
    lib.record(_entry(method="POST"))
    assert lib.find("GET", "https://api.example.com/v1/items") is None


def test_library_save_and_load_roundtrip(tmp_path):
    lib = ReplayLibrary()
    lib.record(_entry())
    lib.record(_entry(method="POST", status=201, body='{"id": 42}'))
    dest = tmp_path / "fixtures.json"
    lib.save(dest)
    loaded = ReplayLibrary.from_file(dest)
    assert len(loaded) == 2
    assert loaded.find("POST", "https://api.example.com/v1/items").status == 201


def test_library_from_file_empty_entries(tmp_path):
    dest = tmp_path / "empty.json"
    dest.write_text(json.dumps({"entries": []}), encoding="utf-8")
    lib = ReplayLibrary.from_file(dest)
    assert len(lib) == 0
