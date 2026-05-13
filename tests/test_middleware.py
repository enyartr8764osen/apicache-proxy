"""Tests for ProxyMiddleware WSGI application."""
from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from apicache_proxy.middleware import ProxyMiddleware
from apicache_proxy.proxy import CachingProxy


@pytest.fixture()
def proxy(tmp_path):
    return CachingProxy(cache_dir=str(tmp_path), default_ttl=60)


@pytest.fixture()
def app(proxy):
    return ProxyMiddleware(proxy)


def _make_environ(path="/", query_string="", method="GET", target_url=""):
    env = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "wsgi.input": BytesIO(),
    }
    if target_url:
        env["HTTP_X_TARGET_URL"] = target_url
    return env


def _start_response():
    calls = []

    def _inner(status, headers):
        calls.append((status, headers))

    _inner.calls = calls
    return _inner


def _mock_response(status_code=200, body=b'{"ok": true}', content_type="application/json"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = body
    resp.headers = {"Content-Type": content_type}
    return resp


def test_missing_target_url_returns_400(app):
    sr = _start_response()
    body = b"".join(app(_make_environ(path="/"), sr))
    assert sr.calls[0][0].startswith("400")
    assert b"error" in body


def test_target_url_via_header(app, proxy):
    mock_resp = _mock_response()
    with patch.object(proxy, "request", return_value=mock_resp) as mock_req:
        sr = _start_response()
        env = _make_environ(target_url="https://api.example.com/data")
        app(env, sr)
        mock_req.assert_called_once()
        assert mock_req.call_args.args[1] == "https://api.example.com/data"


def test_target_url_via_path(app, proxy):
    mock_resp = _mock_response()
    with patch.object(proxy, "request", return_value=mock_resp) as mock_req:
        sr = _start_response()
        env = _make_environ(path="/https://api.example.com/items")
        app(env, sr)
        assert mock_req.call_args.args[1] == "https://api.example.com/items"


def test_bypass_cache_forwarded(app, proxy):
    mock_resp = _mock_response()
    with patch.object(proxy, "request", return_value=mock_resp) as mock_req:
        sr = _start_response()
        env = _make_environ(
            query_string="bypass_cache=1",
            target_url="https://api.example.com/",
        )
        app(env, sr)
        assert mock_req.call_args.kwargs["bypass_cache"] is True


def test_ttl_forwarded(app, proxy):
    mock_resp = _mock_response()
    with patch.object(proxy, "request", return_value=mock_resp) as mock_req:
        sr = _start_response()
        env = _make_environ(
            query_string="ttl=120",
            target_url="https://api.example.com/",
        )
        app(env, sr)
        assert mock_req.call_args.kwargs["ttl"] == 120


def test_response_status_and_body(app, proxy):
    mock_resp = _mock_response(status_code=200, body=b'{"result": 1}')
    with patch.object(proxy, "request", return_value=mock_resp):
        sr = _start_response()
        env = _make_environ(target_url="https://api.example.com/")
        chunks = app(env, sr)
        assert b"".join(chunks) == b'{"result": 1}'
        assert sr.calls[0][0] == "200 OK"
