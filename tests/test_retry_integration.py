"""Integration-level tests: CachingProxy uses RetryConfig on transient errors."""

import pytest
from unittest.mock import MagicMock, patch

from apicache_proxy.proxy import CachingProxy
from apicache_proxy.retry import RetryConfig


def _mock_response(status: int = 200, body: bytes = b"{}", headers: dict = None):
    resp = MagicMock()
    resp.status_code = status
    resp.content = body
    resp.headers = headers or {"Content-Type": "application/json"}
    return resp


@pytest.fixture()
def retry_proxy():
    cfg = RetryConfig(max_attempts=3, backoff_base=0.0)
    return CachingProxy(retry_config=cfg)


def test_proxy_retries_503_until_success(retry_proxy):
    responses = [_mock_response(503), _mock_response(503), _mock_response(200)]
    with patch.object(retry_proxy._session, "request", side_effect=responses) as mock_req:
        resp = retry_proxy.request("GET", "http://example.com/api")
    assert resp.status_code == 200
    assert mock_req.call_count == 3


def test_proxy_retries_on_os_error_then_succeeds(retry_proxy):
    ok = _mock_response(200)
    with patch.object(
        retry_proxy._session, "request", side_effect=[OSError("reset"), ok]
    ) as mock_req:
        resp = retry_proxy.request("GET", "http://example.com/api")
    assert resp.status_code == 200
    assert mock_req.call_count == 2


def test_proxy_raises_after_all_retries_exhausted(retry_proxy):
    with patch.object(
        retry_proxy._session, "request", side_effect=OSError("gone")
    ):
        with pytest.raises(OSError, match="gone"):
            retry_proxy.request("GET", "http://example.com/api")


def test_proxy_records_error_metric_on_exception(retry_proxy):
    with patch.object(
        retry_proxy._session, "request", side_effect=OSError("fail")
    ):
        with pytest.raises(OSError):
            retry_proxy.request("GET", "http://example.com/api")
    assert retry_proxy._metrics.errors == 1


def test_proxy_without_retry_config_does_not_retry():
    proxy = CachingProxy()  # no retry_config
    responses = [_mock_response(503), _mock_response(200)]
    with patch.object(proxy._session, "request", side_effect=responses) as mock_req:
        resp = proxy.request("GET", "http://example.com/api")
    # Without retry, only one call is made and the 503 is returned
    assert resp.status_code == 503
    assert mock_req.call_count == 1


def test_bypass_cache_still_retries(retry_proxy):
    responses = [_mock_response(502), _mock_response(200)]
    with patch.object(retry_proxy._session, "request", side_effect=responses) as mock_req:
        resp = retry_proxy.request("GET", "http://example.com/api", bypass_cache=True)
    assert resp.status_code == 200
    assert mock_req.call_count == 2
