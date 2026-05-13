"""Caching proxy that wraps an HTTP client and stores responses locally."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional

import urllib.request
import urllib.error

from .cache import Cache
from .headers import filter_hop_by_hop, headers_for_cache_key


class CachingProxy:
    """Fetch URLs through a local cache.

    Parameters
    ----------
    cache:
        A :class:`~apicache_proxy.cache.Cache` instance used for storage.
    ttl:
        Default time-to-live in seconds for cached responses (default 300).
    include_headers_in_key:
        When *True*, request headers (after filtering) are folded into the
        cache key so that different auth tokens produce separate entries.
    """

    def __init__(
        self,
        cache: Cache,
        ttl: int = 300,
        include_headers_in_key: bool = False,
    ) -> None:
        self._cache = cache
        self._ttl = ttl
        self._include_headers_in_key = include_headers_in_key

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_cache_key(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        parts: Dict[str, Any] = {"method": method.upper(), "url": url}
        if self._include_headers_in_key and headers:
            parts["headers"] = headers_for_cache_key(headers)
        raw = json.dumps(parts, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _fetch(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        req = urllib.request.Request(url, method=method.upper(), headers=headers or {})
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode(errors="replace")
            resp_headers = dict(resp.headers)
        return {
            "status": resp.status,
            "headers": filter_hop_by_hop(resp_headers),
            "body": body,
            "fetched_at": time.time(),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        bypass_cache: bool = False,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Perform *method* request to *url*, returning a response dict.

        The response dict has keys ``status``, ``headers``, ``body``,
        ``fetched_at``, and ``cached`` (bool).
        """
        key = self._build_cache_key(method, url, headers)
        if not bypass_cache:
            cached = self._cache.get(key)
            if cached is not None:
                cached["cached"] = True
                return cached

        response = self._fetch(method, url, headers)
        effective_ttl = ttl if ttl is not None else self._ttl
        self._cache.set(key, response, ttl=effective_ttl)
        response["cached"] = False
        return response

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        bypass_cache: bool = False,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper for GET requests."""
        return self.request("GET", url, headers=headers, bypass_cache=bypass_cache, ttl=ttl)
