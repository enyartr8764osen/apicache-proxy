"""Tests for apicache_proxy.retry."""

import pytest
from unittest.mock import MagicMock, call

from apicache_proxy.retry import RetryConfig, with_retry


# ---------------------------------------------------------------------------
# RetryConfig
# ---------------------------------------------------------------------------

def test_default_config_values():
    cfg = RetryConfig()
    assert cfg.max_attempts == 3
    assert cfg.backoff_base == 0.5
    assert cfg.backoff_max == 10.0
    assert 503 in cfg.retryable_statuses


def test_invalid_max_attempts_raises():
    with pytest.raises(ValueError, match="max_attempts"):
        RetryConfig(max_attempts=0)


def test_invalid_backoff_base_raises():
    with pytest.raises(ValueError, match="backoff_base"):
        RetryConfig(backoff_base=-1)


def test_delay_for_first_attempt_is_zero():
    cfg = RetryConfig(backoff_base=1.0)
    assert cfg.delay_for(0) == 0.0


def test_delay_doubles_each_attempt():
    cfg = RetryConfig(backoff_base=1.0, backoff_max=100.0)
    assert cfg.delay_for(1) == 1.0
    assert cfg.delay_for(2) == 2.0
    assert cfg.delay_for(3) == 4.0


def test_delay_capped_at_backoff_max():
    cfg = RetryConfig(backoff_base=1.0, backoff_max=3.0)
    assert cfg.delay_for(10) == 3.0


# ---------------------------------------------------------------------------
# with_retry — success paths
# ---------------------------------------------------------------------------

def _resp(status: int):
    r = MagicMock()
    r.status_code = status
    return r


def test_success_on_first_attempt_no_sleep():
    sleep = MagicMock()
    fn = MagicMock(return_value=_resp(200))
    result = with_retry(fn, RetryConfig(max_attempts=3), _sleep=sleep)
    assert result.status_code == 200
    fn.assert_called_once()
    sleep.assert_not_called()


def test_retries_on_503_then_succeeds():
    sleep = MagicMock()
    fn = MagicMock(side_effect=[_resp(503), _resp(200)])
    cfg = RetryConfig(max_attempts=3, backoff_base=1.0)
    result = with_retry(fn, cfg, _sleep=sleep)
    assert result.status_code == 200
    assert fn.call_count == 2
    sleep.assert_called_once_with(1.0)


def test_retries_on_exception_then_succeeds():
    sleep = MagicMock()
    fn = MagicMock(side_effect=[OSError("timeout"), _resp(200)])
    result = with_retry(fn, RetryConfig(max_attempts=3, backoff_base=0.1), _sleep=sleep)
    assert result.status_code == 200


# ---------------------------------------------------------------------------
# with_retry — exhaustion paths
# ---------------------------------------------------------------------------

def test_returns_last_bad_response_when_exhausted():
    sleep = MagicMock()
    fn = MagicMock(return_value=_resp(502))
    cfg = RetryConfig(max_attempts=3, backoff_base=0.0)
    result = with_retry(fn, cfg, _sleep=sleep)
    assert result.status_code == 502
    assert fn.call_count == 3


def test_raises_last_exception_when_exhausted():
    sleep = MagicMock()
    fn = MagicMock(side_effect=OSError("gone"))
    with pytest.raises(OSError, match="gone"):
        with_retry(fn, RetryConfig(max_attempts=2, backoff_base=0.0), _sleep=sleep)
    assert fn.call_count == 2


def test_non_retryable_status_returned_immediately():
    sleep = MagicMock()
    fn = MagicMock(return_value=_resp(404))
    result = with_retry(fn, RetryConfig(max_attempts=3), _sleep=sleep)
    assert result.status_code == 404
    fn.assert_called_once()
