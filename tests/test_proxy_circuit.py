"""Integration tests for CircuitBreakerProxy."""

import pytest
from unittest.mock import MagicMock, patch

from apicache_proxy.circuitbreaker import CircuitBreaker, State
from apicache_proxy.proxy_circuit import CircuitBreakerProxy


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_proxy(threshold: int = 3, recovery: float = 30.0):
    inner = MagicMock()
    breaker = CircuitBreaker(failure_threshold=threshold, recovery_timeout=recovery)
    return CircuitBreakerProxy(proxy=inner, breaker=breaker), inner, breaker


def _ok_response():
    return {"status_code": 200, "headers": {}, "body": b"ok", "from_cache": False}


def _error_response():
    return {"status_code": 503, "headers": {}, "body": b"err", "from_cache": False}


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------

def test_successful_request_passes_through():
    cbp, inner, breaker = _make_proxy()
    inner.request.return_value = _ok_response()
    resp = cbp.request("GET", "http://example.com/api")
    assert resp["status_code"] == 200
    inner.request.assert_called_once_with("GET", "http://example.com/api")


def test_success_keeps_circuit_closed():
    cbp, inner, breaker = _make_proxy()
    inner.request.return_value = _ok_response()
    cbp.request("GET", "http://example.com/api")
    assert breaker.state is State.CLOSED


# ---------------------------------------------------------------------------
# failure accumulation
# ---------------------------------------------------------------------------

def test_5xx_response_records_failure():
    cbp, inner, breaker = _make_proxy(threshold=3)
    inner.request.return_value = _error_response()
    cbp.request("GET", "http://example.com/api")
    assert breaker._failures == 1


def test_threshold_reached_opens_circuit():
    cbp, inner, breaker = _make_proxy(threshold=2)
    inner.request.return_value = _error_response()
    cbp.request("GET", "http://example.com/api")
    cbp.request("GET", "http://example.com/api")
    assert breaker.state is State.OPEN


def test_exception_records_failure_and_reraises():
    cbp, inner, breaker = _make_proxy(threshold=1)
    inner.request.side_effect = OSError("network down")
    with pytest.raises(OSError):
        cbp.request("GET", "http://example.com/api")
    assert breaker.state is State.OPEN


# ---------------------------------------------------------------------------
# open circuit short-circuits
# ---------------------------------------------------------------------------

def test_open_circuit_returns_503_without_network_call():
    cbp, inner, breaker = _make_proxy(threshold=1)
    breaker.record_failure()  # open immediately
    resp = cbp.request("GET", "http://example.com/api")
    assert resp["status_code"] == 503
    inner.request.assert_not_called()


def test_get_shortcut_also_blocked_when_open():
    cbp, inner, breaker = _make_proxy(threshold=1)
    breaker.record_failure()
    resp = cbp.get("http://example.com/api")
    assert resp["status_code"] == 503


# ---------------------------------------------------------------------------
# half-open probe
# ---------------------------------------------------------------------------

def test_successful_probe_closes_circuit(monkeypatch):
    import time
    cbp, inner, breaker = _make_proxy(threshold=1, recovery=10.0)
    breaker.record_failure()
    t0 = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: t0 + 11.0)
    inner.request.return_value = _ok_response()
    resp = cbp.request("GET", "http://example.com/api")
    assert resp["status_code"] == 200
    assert breaker.state is State.CLOSED


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

def test_stats_returns_breaker_dict():
    cbp, _, breaker = _make_proxy(threshold=5, recovery=60.0)
    s = cbp.stats()
    assert s["failure_threshold"] == 5
    assert s["recovery_timeout"] == 60.0
    assert "state" in s
