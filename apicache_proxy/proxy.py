"""CachingProxy — wraps an HTTP client with cache + metrics."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

from .cache import Cache
from .headers import filter_hop_by_hop, headers_for_cache_key, normalise
from .metrics import Metrics
from .revalidation import conditional_headers, handle_304, has_validators
from .ttl import is_cacheable, resolve


class CachingProxy:
    """Fetch URLs through a local cache, recording metrics for each outcome."""

    def __init__(
        self,
        cache: Cache,
        default_ttl: int = 300,
        metrics: Optional[Metrics] = None,
    ) -> None:
        self._cache = cache
        self._default_ttl = default_ttl
        self.metrics: Metrics = metrics if metrics is not None else Metrics()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_cache_key(self, method: str, url: str, headers: Dict[str, str]) -> str:
        stable = headers_for_cache_key(normalise(headers))
        return f"{method.upper()}:{url}:{stable}"

    def _fetch(
        self, method: str, url: str, headers: Dict[str, str], **kwargs: Any
    ) -> requests.Response:
        resp = requests.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        bypass_cache: bool = False,
        ttl: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        headers = normalise(headers or {})
        key = self._build_cache_key(method, url, headers)

        if not bypass_cache:
            entry = self._cache.get(key)
            if entry is not None:
                cond = conditional_headers(entry)
                if cond and has_validators(entry):
                    try:
                        resp = self._fetch(method, url, {**headers, **cond}, **kwargs)
                        if resp.status_code == 304:
                            self.metrics.record_hit()
                            return handle_304(entry)
                    except requests.HTTPError:
                        pass
                else:
                    self.metrics.record_hit()
                    return entry.to_dict()
        else:
            self.metrics.record_bypass()

        # Cache miss (or bypass) — go to network
        try:
            resp = self._fetch(method, url, headers, **kwargs)
        except Exception:
            self.metrics.record_error()
            raise

        resp_headers = filter_hop_by_hop(dict(resp.headers))
        effective_ttl = resolve(ttl, resp_headers, self._default_ttl)

        if not bypass_cache and is_cacheable(resp.status_code, resp_headers):
            from .cache import CacheEntry  # local import to avoid circular

            entry = CacheEntry(
                key=key,
                status_code=resp.status_code,
                headers=resp_headers,
                body=resp.text,
                created_at=time.time(),
                ttl=effective_ttl,
            )
            self._cache.set(key, entry)

        if not bypass_cache:
            self.metrics.record_miss()

        return {
            "status_code": resp.status_code,
            "headers": resp_headers,
            "body": resp.text,
            "from_cache": False,
        }
