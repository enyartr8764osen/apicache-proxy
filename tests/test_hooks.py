"""Tests for apicache_proxy.hooks."""
import pytest
from apicache_proxy.hooks import HookRegistry


@pytest.fixture()
def registry():
    return HookRegistry()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_register_pre_request_increments_count(registry):
    registry.register_pre_request(lambda m, u, h: None)
    assert registry.pre_request_count() == 1


def test_register_post_response_increments_count(registry):
    registry.register_post_response(lambda m, u, s, c: None)
    assert registry.post_response_count() == 1


def test_register_non_callable_pre_request_raises(registry):
    with pytest.raises(TypeError):
        registry.register_pre_request("not_a_function")  # type: ignore[arg-type]


def test_register_non_callable_post_response_raises(registry):
    with pytest.raises(TypeError):
        registry.register_post_response(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Firing hooks
# ---------------------------------------------------------------------------

def test_fire_pre_request_calls_hook(registry):
    calls = []
    registry.register_pre_request(lambda m, u, h: calls.append((m, u)))
    registry.fire_pre_request("GET", "http://example.com", {})
    assert calls == [("GET", "http://example.com")]


def test_fire_pre_request_passes_headers(registry):
    received = {}
    def hook(m, u, h):
        received.update(h)
    registry.register_pre_request(hook)
    registry.fire_pre_request("GET", "http://x.com", {"Authorization": "Bearer t"})
    assert received["Authorization"] == "Bearer t"


def test_fire_pre_request_defaults_empty_headers(registry):
    received = {}
    registry.register_pre_request(lambda m, u, h: received.update({"h": h}))
    registry.fire_pre_request("GET", "http://x.com")
    assert received["h"] == {}


def test_fire_post_response_calls_hook(registry):
    calls = []
    registry.register_post_response(lambda m, u, s, c: calls.append((s, c)))
    registry.fire_post_response("GET", "http://example.com", 200, True)
    assert calls == [(200, True)]


def test_multiple_hooks_all_called(registry):
    log = []
    registry.register_pre_request(lambda m, u, h: log.append("a"))
    registry.register_pre_request(lambda m, u, h: log.append("b"))
    registry.fire_pre_request("GET", "http://x.com")
    assert log == ["a", "b"]


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------

def test_clear_removes_all_hooks(registry):
    registry.register_pre_request(lambda m, u, h: None)
    registry.register_post_response(lambda m, u, s, c: None)
    registry.clear()
    assert registry.pre_request_count() == 0
    assert registry.post_response_count() == 0


def test_fire_after_clear_does_nothing(registry):
    calls = []
    registry.register_pre_request(lambda m, u, h: calls.append(1))
    registry.clear()
    registry.fire_pre_request("GET", "http://x.com")
    assert calls == []
