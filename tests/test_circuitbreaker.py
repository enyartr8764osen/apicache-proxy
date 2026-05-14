"""Tests for apicache_proxy.circuitbreaker."""

import time
import pytest
from apicache_proxy.circuitbreaker import CircuitBreaker, State


# ---------------------------------------------------------------------------
# construction
# ---------------------------------------------------------------------------

def test_default_state_is_closed():
    cb = CircuitBreaker()
    assert cb.state is State.CLOSED


def test_invalid_threshold_raises():
    with pytest.raises(ValueError):
        CircuitBreaker(failure_threshold=0)


def test_invalid_recovery_timeout_raises():
    with pytest.raises(ValueError):
        CircuitBreaker(recovery_timeout=-1)


# ---------------------------------------------------------------------------
# failure accumulation
# ---------------------------------------------------------------------------

def test_single_failure_does_not_open_by_default():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    assert cb.state is State.CLOSED


def test_reaching_threshold_opens_circuit():
    cb = CircuitBreaker(failure_threshold=3)
    for _ in range(3):
        cb.record_failure()
    assert cb.state is State.OPEN


def test_is_open_reflects_state():
    cb = CircuitBreaker(failure_threshold=2)
    assert not cb.is_open()
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open()


# ---------------------------------------------------------------------------
# success resets failures
# ---------------------------------------------------------------------------

def test_success_before_threshold_resets_failures():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.state is State.CLOSED
    # two more failures should not open (counter was reset)
    cb.record_failure()
    cb.record_failure()
    assert cb.state is State.CLOSED


def test_success_after_open_closes_circuit():
    cb = CircuitBreaker(failure_threshold=2)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.state is State.CLOSED
    assert not cb.is_open()


# ---------------------------------------------------------------------------
# half-open after timeout
# ---------------------------------------------------------------------------

def test_circuit_becomes_half_open_after_timeout(monkeypatch):
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
    cb.record_failure()
    assert cb.state is State.OPEN

    # fast-forward time beyond recovery_timeout
    original = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: original + 11.0)
    assert cb.state is State.HALF_OPEN


def test_circuit_stays_open_before_timeout(monkeypatch):
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)
    cb.record_failure()
    original = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: original + 5.0)
    assert cb.state is State.OPEN


# ---------------------------------------------------------------------------
# manual reset & to_dict
# ---------------------------------------------------------------------------

def test_reset_closes_open_circuit():
    cb = CircuitBreaker(failure_threshold=1)
    cb.record_failure()
    cb.reset()
    assert cb.state is State.CLOSED
    assert not cb.is_open()


def test_to_dict_contains_expected_keys():
    cb = CircuitBreaker(failure_threshold=4, recovery_timeout=15.0)
    cb.record_failure()
    d = cb.to_dict()
    assert d["state"] == "closed"
    assert d["failures"] == 1
    assert d["failure_threshold"] == 4
    assert d["recovery_timeout"] == 15.0
