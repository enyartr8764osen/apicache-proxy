"""Tests for apicache_proxy.ratelimit."""

import time
import pytest
from unittest.mock import patch

from apicache_proxy.ratelimit import RateLimiter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def unlimited():
    return RateLimiter(requests_per_second=None)


@pytest.fixture()
def limited():
    """2 req/s, burst of 2."""
    return RateLimiter(requests_per_second=2.0, burst=2)


# ---------------------------------------------------------------------------
# is_limited
# ---------------------------------------------------------------------------

def test_unlimited_is_not_limited(unlimited):
    assert unlimited.is_limited() is False


def test_limited_is_limited(limited):
    assert limited.is_limited() is True


# ---------------------------------------------------------------------------
# acquire — unlimited
# ---------------------------------------------------------------------------

def test_unlimited_acquire_returns_zero_immediately(unlimited):
    start = time.monotonic()
    result = unlimited.acquire("api.example.com")
    elapsed = time.monotonic() - start
    assert result == 0.0
    assert elapsed < 0.05  # well under any real threshold


# ---------------------------------------------------------------------------
# acquire — limited (time is mocked so tests stay fast)
# ---------------------------------------------------------------------------

def test_burst_allows_immediate_requests_within_limit():
    """First N requests within burst should not sleep."""
    rl = RateLimiter(requests_per_second=10.0, burst=3)
    # Patch sleep so we don't actually wait
    with patch("apicache_proxy.ratelimit.time.sleep") as mock_sleep:
        for _ in range(3):
            rl.acquire("host.test")
        mock_sleep.assert_not_called()


def test_exceeding_burst_triggers_sleep():
    rl = RateLimiter(requests_per_second=10.0, burst=2)
    with patch("apicache_proxy.ratelimit.time.sleep") as mock_sleep:
        # Fill the burst
        rl.acquire("host.test")
        rl.acquire("host.test")
        # Third call should sleep
        rl.acquire("host.test")
        mock_sleep.assert_called_once()


def test_different_hosts_are_independent():
    rl = RateLimiter(requests_per_second=10.0, burst=1)
    with patch("apicache_proxy.ratelimit.time.sleep") as mock_sleep:
        rl.acquire("host-a.test")
        rl.acquire("host-b.test")  # different host — should NOT sleep
        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

def test_reset_single_host_clears_history():
    rl = RateLimiter(requests_per_second=10.0, burst=1)
    rl.acquire("host.test")  # fills burst
    rl.reset("host.test")
    # After reset the next acquire should not sleep
    with patch("apicache_proxy.ratelimit.time.sleep") as mock_sleep:
        rl.acquire("host.test")
        mock_sleep.assert_not_called()


def test_reset_all_hosts_clears_everything():
    rl = RateLimiter(requests_per_second=10.0, burst=1)
    for host in ("a.test", "b.test", "c.test"):
        rl.acquire(host)
    rl.reset()
    with patch("apicache_proxy.ratelimit.time.sleep") as mock_sleep:
        for host in ("a.test", "b.test", "c.test"):
            rl.acquire(host)
        mock_sleep.assert_not_called()


def test_reset_unknown_host_is_noop():
    rl = RateLimiter(requests_per_second=5.0, burst=5)
    rl.reset("nonexistent.host")  # should not raise
