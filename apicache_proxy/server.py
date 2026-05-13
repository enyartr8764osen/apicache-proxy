"""Simple HTTP server that exposes CachingProxy over a local port."""
from __future__ import annotations

import logging
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

from .middleware import ProxyMiddleware
from .proxy import CachingProxy

logger = logging.getLogger(__name__)


class _QuietHandler(WSGIRequestHandler):
    """Suppress the default per-request log lines unless DEBUG is active."""

    def log_message(self, fmt: str, *args: object) -> None:  # type: ignore[override]
        logger.debug(fmt, *args)


def make_app(proxy: CachingProxy) -> ProxyMiddleware:
    """Return a WSGI application wrapping *proxy*."""
    return ProxyMiddleware(proxy)


def serve(
    host: str = "127.0.0.1",
    port: int = 8080,
    proxy: CachingProxy | None = None,
    *,
    cache_dir: str = ".apicache",
    default_ttl: int = 300,
) -> None:
    """Start a blocking HTTP server on *host*:*port*.

    If *proxy* is ``None`` a new :class:`~apicache_proxy.proxy.CachingProxy`
    is created with *cache_dir* and *default_ttl*.
    """
    if proxy is None:
        proxy = CachingProxy(cache_dir=cache_dir, default_ttl=default_ttl)

    app = make_app(proxy)
    httpd: WSGIServer = make_server(host, port, app, handler_class=_QuietHandler)
    logger.info("apicache-proxy listening on http://%s:%d", host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        httpd.server_close()
