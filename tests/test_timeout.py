"""Tests for apicache_proxy.timeout."""
import pytest
from apicache_proxy.timeout import (
    TimeoutConfig,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
)


def test_default_values():
    cfg = TimeoutConfig()
    assert cfg.connect == DEFAULT_CONNECT_TIMEOUT
    assert cfg.read == DEFAULT_READ_TIMEOUT


def test_custom_values():
    cfg = TimeoutConfig(connect=2.5, read=10.0)
    assert cfg.connect == 2.5
    assert cfg.read == 10.0


def test_as_tuple():
    cfg = TimeoutConfig(connect=1.0, read=5.0)
    assert cfg.as_tuple == (1.0, 5.0)


def test_zero_connect_raises():
    with pytest.raises(ValueError, match="connect timeout"):
        TimeoutConfig(connect=0)


def test_negative_read_raises():
    with pytest.raises(ValueError, match="read timeout"):
        TimeoutConfig(read=-1.0)


def test_to_dict_roundtrip():
    cfg = TimeoutConfig(connect=3.0, read=15.0)
    restored = TimeoutConfig.from_dict(cfg.to_dict())
    assert restored == cfg


def test_from_args_defaults():
    cfg = TimeoutConfig.from_args()
    assert cfg.connect == DEFAULT_CONNECT_TIMEOUT
    assert cfg.read == DEFAULT_READ_TIMEOUT


def test_from_args_partial_override():
    cfg = TimeoutConfig.from_args(connect=1.0)
    assert cfg.connect == 1.0
    assert cfg.read == DEFAULT_READ_TIMEOUT


def test_equality():
    a = TimeoutConfig(connect=2.0, read=8.0)
    b = TimeoutConfig(connect=2.0, read=8.0)
    assert a == b


def test_inequality():
    a = TimeoutConfig(connect=2.0, read=8.0)
    b = TimeoutConfig(connect=2.0, read=9.0)
    assert a != b


def test_equality_non_timeout_returns_not_implemented():
    cfg = TimeoutConfig()
    assert cfg.__eq__("not a timeout") is NotImplemented
