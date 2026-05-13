"""Tests for the server module (make_app, serve)."""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from apicache_proxy.middleware import ProxyMiddleware
from apicache_proxy.proxy import CachingProxy
from apicache_proxy import server as server_module


@pytest.fixture()
def proxy(tmp_path):
    return CachingProxy(cache_dir=str(tmp_path), default_ttl=60)


def test_make_app_returns_middleware(proxy):
    app = server_module.make_app(proxy)
    assert isinstance(app, ProxyMiddleware)
    assert app.proxy is proxy


def test_serve_creates_proxy_when_none_given(tmp_path):
    """serve() should instantiate a CachingProxy if none is supplied."""
    mock_httpd = MagicMock()
    mock_httpd.serve_forever.side_effect = KeyboardInterrupt

    with patch("apicache_proxy.server.make_server", return_value=mock_httpd) as mk:
        server_module.serve(
            host="127.0.0.1",
            port=19999,
            cache_dir=str(tmp_path),
            default_ttl=30,
        )
        mk.assert_called_once()
        # First positional arg is host, second is port
        assert mk.call_args.args[0] == "127.0.0.1"
        assert mk.call_args.args[1] == 19999


def test_serve_uses_supplied_proxy(proxy, tmp_path):
    mock_httpd = MagicMock()
    mock_httpd.serve_forever.side_effect = KeyboardInterrupt

    with patch("apicache_proxy.server.make_server", return_value=mock_httpd):
        server_module.serve(proxy=proxy, host="127.0.0.1", port=19998)

    mock_httpd.server_close.assert_called_once()


def test_serve_calls_server_close_on_keyboard_interrupt(proxy):
    mock_httpd = MagicMock()
    mock_httpd.serve_forever.side_effect = KeyboardInterrupt

    with patch("apicache_proxy.server.make_server", return_value=mock_httpd):
        server_module.serve(proxy=proxy)

    mock_httpd.server_close.assert_called_once()
