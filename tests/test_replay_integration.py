"""Integration: record real-looking interactions then replay them."""
import pytest

from apicache_proxy.replay import ReplayEntry, ReplayLibrary
from apicache_proxy.proxy_replay import ReplayProxy


def _build_library():
    lib = ReplayLibrary()
    lib.record(ReplayEntry(
        "GET", "https://api.example.com/users/1",
        200, {"Content-Type": "application/json"},
        '{"id": 1, "name": "Alice"}',
    ))
    lib.record(ReplayEntry(
        "GET", "https://api.example.com/users/2",
        200, {"Content-Type": "application/json"},
        '{"id": 2, "name": "Bob"}',
    ))
    lib.record(ReplayEntry(
        "DELETE", "https://api.example.com/users/1",
        204, {}, "",
    ))
    return lib


@pytest.fixture
def proxy():
    return ReplayProxy(_build_library())


def test_two_different_users_resolved_independently(proxy):
    r1 = proxy.get("https://api.example.com/users/1")
    r2 = proxy.get("https://api.example.com/users/2")
    assert r1.json()["name"] == "Alice"
    assert r2.json()["name"] == "Bob"


def test_delete_returns_204(proxy):
    resp = proxy.request("DELETE", "https://api.example.com/users/1")
    assert resp.status_code == 204
    assert resp.text == ""


def test_save_and_reload_preserves_all_entries(tmp_path, proxy):
    lib = _build_library()
    dest = tmp_path / "recorded.json"
    lib.save(dest)
    loaded_proxy = ReplayProxy(ReplayLibrary.from_file(dest))
    assert loaded_proxy.get("https://api.example.com/users/2").json()["name"] == "Bob"


def test_strict_proxy_raises_for_unrecorded_url(proxy):
    with pytest.raises(KeyError):
        proxy.get("https://api.example.com/users/99")
