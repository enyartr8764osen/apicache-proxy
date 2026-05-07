import pytest
from unittest.mock import MagicMock, patch

from apicache_proxy.proxy import CachingProxy


@pytest.fixture
def proxy():
    return CachingProxy(ttl=60)


def _mock_response(status_code=200, json_data=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.ok = status_code < 400
    mock_resp.json.return_value = json_data or {}
    return mock_resp


@patch("apicache_proxy.proxy.requests.request")
def test_first_request_hits_network(mock_request, proxy):
    mock_request.return_value = _mock_response(200, {"data": "value"})

    proxy.get("https://api.example.com/items")

    mock_request.assert_called_once()


@patch("apicache_proxy.proxy.requests.request")
def test_second_request_uses_cache(mock_request, proxy):
    mock_request.return_value = _mock_response(200, {"data": "value"})

    proxy.get("https://api.example.com/items")
    proxy.get("https://api.example.com/items")

    mock_request.assert_called_once()


@patch("apicache_proxy.proxy.requests.request")
def test_bypass_cache_forces_network_call(mock_request, proxy):
    mock_request.return_value = _mock_response(200, {"data": "value"})

    proxy.get("https://api.example.com/items")
    proxy.get("https://api.example.com/items", bypass_cache=True)

    assert mock_request.call_count == 2


@patch("apicache_proxy.proxy.requests.request")
def test_different_params_are_cached_separately(mock_request, proxy):
    mock_request.return_value = _mock_response(200, {})

    proxy.get("https://api.example.com/items", params={"page": 1})
    proxy.get("https://api.example.com/items", params={"page": 2})

    assert mock_request.call_count == 2


@patch("apicache_proxy.proxy.requests.request")
def test_error_response_not_cached(mock_request, proxy):
    mock_request.return_value = _mock_response(500, {})

    proxy.get("https://api.example.com/fail")
    proxy.get("https://api.example.com/fail")

    assert mock_request.call_count == 2


@patch("apicache_proxy.proxy.requests.request")
def test_invalidate_removes_cached_entry(mock_request, proxy):
    mock_request.return_value = _mock_response(200, {"data": "value"})
    url = "https://api.example.com/items"

    proxy.get(url)
    proxy.invalidate("GET", url)
    proxy.get(url)

    assert mock_request.call_count == 2


@patch("apicache_proxy.proxy.requests.request")
def test_clear_removes_all_entries(mock_request, proxy):
    mock_request.return_value = _mock_response(200, {})

    proxy.get("https://api.example.com/a")
    proxy.get("https://api.example.com/b")
    proxy.clear()
    proxy.get("https://api.example.com/a")
    proxy.get("https://api.example.com/b")

    assert mock_request.call_count == 4
