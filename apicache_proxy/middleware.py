"""WSGI middleware that wraps a CachingProxy for use in HTTP server mode."""
from __future__ import annotations

import json
from typing import Callable, Iterable

from .proxy import CachingProxy


class ProxyMiddleware:
    """Minimal WSGI app that forwards requests through CachingProxy.

    Supported query parameters (passed via the request URL):
      - ``bypass_cache=1``  – skip the cache for this request.
      - ``ttl=<seconds>``   – override the default TTL for this request.
    """

    def __init__(self, proxy: CachingProxy) -> None:
        self.proxy = proxy

    # ------------------------------------------------------------------
    # WSGI entry-point
    # ------------------------------------------------------------------
    def __call__(self, environ: dict, start_response: Callable) -> Iterable[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        query_string = environ.get("QUERY_STRING", "")

        params, bypass_cache, ttl = self._parse_query(query_string)

        # Reconstruct the target URL from X-Target-URL header or PATH_INFO
        target_url = environ.get("HTTP_X_TARGET_URL", "").strip()
        if not target_url:
            target_url = path.lstrip("/")

        if not target_url:
            return self._respond(start_response, 400, {"error": "Missing target URL"})

        try:
            response = self.proxy.request(
                method,
                target_url,
                params=params if params else None,
                bypass_cache=bypass_cache,
                ttl=ttl,
            )
        except Exception as exc:  # pragma: no cover
            return self._respond(start_response, 502, {"error": str(exc)})

        body = response.content
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        status = f"{response.status_code} {self._reason(response.status_code)}"
        headers = [("Content-Type", content_type), ("Content-Length", str(len(body)))]
        start_response(status, headers)
        return [body]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_query(query_string: str) -> tuple[dict, bool, int | None]:
        """Return (params, bypass_cache, ttl) parsed from *query_string*."""
        from urllib.parse import parse_qs

        raw = parse_qs(query_string, keep_blank_values=False)
        bypass_cache = raw.pop("bypass_cache", ["0"])[0] in ("1", "true", "yes")
        ttl_values = raw.pop("ttl", [None])
        ttl: int | None = int(ttl_values[0]) if ttl_values[0] is not None else None
        params = {k: v[0] for k, v in raw.items()}
        return params, bypass_cache, ttl

    @staticmethod
    def _respond(start_response: Callable, status_code: int, body: dict) -> list[bytes]:
        encoded = json.dumps(body).encode()
        start_response(
            f"{status_code} {ProxyMiddleware._reason(status_code)}",
            [("Content-Type", "application/json"), ("Content-Length", str(len(encoded)))],
        )
        return [encoded]

    @staticmethod
    def _reason(code: int) -> str:
        reasons = {200: "OK", 400: "Bad Request", 502: "Bad Gateway"}
        return reasons.get(code, "Unknown")
