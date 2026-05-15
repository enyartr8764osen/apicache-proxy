"""Tests for apicache_proxy.throttle."""

import time
import pytest
from unittest.mock import MagicMock

from apicache_proxy.throttle import ThrottleConfig, ThrottledProxy, _extract_host


# ------------------------------------------------------------------ #
# ThrottleConfig
# ------------------------------------------------------------------ #

def test_default_delay_is_zero():
    cfg = ThrottleConfig()
    assert cfg.delay == 0.0


def test_negative_delay_raises():
    with pytest.raises(ValueError, match="delay must be >= 0"):
        ThrottleConfig(delay=-0.1)


def test_negative_per_host_delay_raises():
    with pytest.raises(ValueError, match="per-host delay"):
        ThrottleConfig(per_host={"api.example.com": -1.0})


def test_delay_for_returns_global_default():
    cfg = ThrottleConfig(delay=0.5)
    assert cfg.delay_for("https://other.example.com/data") == 0.5


def test_delay_for_returns_per_host_override():
    cfg = ThrottleConfig(delay=0.5, per_host={"slow.example.com": 2.0})
    assert cfg.delay_for("https://slow.example.com/endpoint") == 2.0


def test_delay_for_falls_back_when_host_not_in_per_host():
    cfg = ThrottleConfig(delay=0.3, per_host={"other.com": 1.0})
    assert cfg.delay_for("https://api.example.com/v1") == 0.3


def test_to_dict_roundtrip():
    cfg = ThrottleConfig(delay=1.0, per_host={"x.com": 0.5})
    restored = ThrottleConfig.from_dict(cfg.to_dict())
    assert restored.delay == cfg.delay
    assert restored.per_host == cfg.per_host


def test_from_dict_defaults():
    cfg = ThrottleConfig.from_dict({})
    assert cfg.delay == 0.0
    assert cfg.per_host == {}


# ------------------------------------------------------------------ #
# _extract_host
# ------------------------------------------------------------------ #

def test_extract_host_strips_scheme():
    assert _extract_host("https://api.example.com/path") == "api.example.com"


def test_extract_host_no_scheme():
    assert _extract_host("api.example.com/path") == "api.example.com"


def test_extract_host_with_query():
    assert _extract_host("https://api.example.com?foo=bar") == "api.example.com"


# ------------------------------------------------------------------ #
# ThrottledProxy
# ------------------------------------------------------------------ #

@pytest.fixture()
def inner():
    mock = MagicMock()
    mock.request.return_value = {"status": 200, "body": "ok"}
    return mock


def test_no_delay_does_not_sleep(inner, monkeypatch):
    slept = []
    monkeypatch.setattr("apicache_proxy.throttle.time.sleep", slept.append)
    proxy = ThrottledProxy(inner, ThrottleConfig(delay=0.0))
    proxy.get("https://api.example.com/data")
    assert slept == []


def test_delay_is_applied(inner, monkeypatch):
    slept = []
    monkeypatch.setattr("apicache_proxy.throttle.time.sleep", slept.append)
    proxy = ThrottledProxy(inner, ThrottleConfig(delay=0.25))
    proxy.get("https://api.example.com/data")
    assert slept == [0.25]


def test_per_host_delay_applied(inner, monkeypatch):
    slept = []
    monkeypatch.setattr("apicache_proxy.throttle.time.sleep", slept.append)
    cfg = ThrottleConfig(delay=0.1, per_host={"slow.example.com": 1.5})
    proxy = ThrottledProxy(inner, cfg)
    proxy.request("GET", "https://slow.example.com/endpoint")
    assert slept == [1.5]


def test_get_delegates_to_inner(inner):
    proxy = ThrottledProxy(inner, ThrottleConfig())
    result = proxy.get("https://api.example.com/")
    inner.request.assert_called_once_with("GET", "https://api.example.com/")
    assert result == {"status": 200, "body": "ok"}


def test_default_config_used_when_none_given(inner, monkeypatch):
    slept = []
    monkeypatch.setattr("apicache_proxy.throttle.time.sleep", slept.append)
    proxy = ThrottledProxy(inner)  # no config
    proxy.get("https://api.example.com/")
    assert slept == []
