"""Caching proxy — wraps an HTTP client with cache + optional retry logic."""

import logging
from typing import Optional

import requests

from .cache import InMemoryCache
from .headers import filter_hop_by_hop, normalise, headers_for_cache_key
from .ttl import resolve, is_cacheable
from .revalidation import conditional_headers, handle_304, has_validators
from .metrics import Metrics
from .ratelimit import RateLimiter
from .retry import RetryConfig, with_retry

log = logging.getLogger(__name__)


class CachingProxy:
    def __init__(
        self,
        cache=None,
        storage=None,
        default_ttl: Optional[int] = None,
        metrics: Optional[Metrics] = None,
        rate_limiter: Optional[RateLimiter] = None,
        retry_config: Optional[RetryConfig] = None,
        session: Optional[requests.Session] = None,
    ):
        self._cache = cache or InMemoryCache()
        self._storage = storage
        self._default_ttl = default_ttl
        self._metrics = metrics or Metrics()
        self._rate_limiter = rate_limiter
        self._retry_config = retry_config
        self._session = session or requests.Session()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_cache_key(self, method: str, url: str, headers: dict) -> str:
        norm = headers_for_cache_key(normalise(headers))
        return f"{method.upper()}:{url}:{sorted(norm.items())}"

    def _fetch(self, method: str, url: str, **kwargs) -> requests.Response:
        """Issue the real HTTP request, honouring retry config if set."""
        if self._rate_limiter:
            self._rate_limiter.acquire()

        def _do():
            return self._session.request(method, url, **kwargs)

        if self._retry_config:
            return with_retry(_do, self._retry_config)
        return _do()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        bypass_cache: bool = False,
        ttl: Optional[int] = None,
        **kwargs,
    ) -> requests.Response:
        headers = normalise(headers or {})
        key = self._build_cache_key(method, url, headers)

        if bypass_cache:
            self._metrics.record_bypass()
            return self._fetch(method, url, headers=headers, **kwargs)

        entry = self._cache.get(key)
        if entry is None and self._storage:
            entry = self._storage.get(key)

        if entry is not None:
            if has_validators(entry):
                cond = conditional_headers(entry)
                resp = self._fetch(method, url, headers={**headers, **cond}, **kwargs)
                if resp.status_code == 304:
                    self._metrics.record_hit()
                    return handle_304(entry, resp)

            self._metrics.record_hit()
            log.debug("cache hit: %s", key)
            return entry.as_response()

        try:
            resp = self._fetch(method, url, headers=headers, **kwargs)
        except Exception as exc:
            self._metrics.record_error()
            raise

        self._metrics.record_miss()

        effective_ttl = resolve(
            ttl if ttl is not None else self._default_ttl,
            dict(resp.headers),
        )
        if is_cacheable(resp.status_code, effective_ttl):
            from .cache import CacheEntry
            entry = CacheEntry.from_response(resp, ttl=effective_ttl)
            self._cache.set(key, entry)
            if self._storage:
                self._storage.set(key, entry)

        return resp
