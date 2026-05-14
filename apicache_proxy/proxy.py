"""Caching proxy — forwards HTTP requests and caches responses.

This version integrates request sanitization so that credentials are
stripped from outgoing request headers and redacted from cached cache
keys derived from query strings.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .cache import Cache
from .metrics import Metrics
from .ratelimit import RateLimiter
from .retry import RetryConfig, with_retry
from .revalidation import conditional_headers, handle_304, has_validators
from .sanitize import redact_query_params, strip_sensitive_headers
from .ttl import is_cacheable, resolve


class CachingProxy:
    """Fetch URLs through a local cache."""

    def __init__(
        self,
        cache: Cache,
        default_ttl: int = 300,
        metrics: Optional[Metrics] = None,
        rate_limiter: Optional[RateLimiter] = None,
        retry_config: Optional[RetryConfig] = None,
        sensitive_headers: Optional[List[str]] = None,
        sensitive_params: Optional[List[str]] = None,
    ) -> None:
        self._cache = cache
        self._default_ttl = default_ttl
        self._metrics = metrics or Metrics()
        self._rate_limiter = rate_limiter or RateLimiter()
        self._retry = retry_config or RetryConfig()
        self._sensitive_headers = sensitive_headers or []
        self._sensitive_params = sensitive_params or []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        bypass_cache: bool = False,
        explicit_ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._do(
            "GET", url, headers=headers,
            bypass_cache=bypass_cache, explicit_ttl=explicit_ttl,
        )

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        bypass_cache: bool = False,
        explicit_ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._do(
            method, url, headers=headers,
            bypass_cache=bypass_cache, explicit_ttl=explicit_ttl,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_cache_key(self, method: str, url: str) -> str:
        """Build a cache key, redacting sensitive query parameters."""
        parsed = urllib.parse.urlsplit(url)
        params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        clean_params = redact_query_params(params, extra=self._sensitive_params)
        clean_query = urllib.parse.urlencode(clean_params)
        clean_url = parsed._replace(query=clean_query).geturl()
        return f"{method.upper()}:{clean_url}"

    def _fetch(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Perform a real HTTP request, stripping sensitive headers first."""
        safe_headers = strip_sensitive_headers(
            headers, extra=self._sensitive_headers
        )
        self._rate_limiter.acquire()
        req = urllib.request.Request(url, headers=safe_headers, method=method)
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            resp_headers = dict(resp.headers)
            return {
                "status": resp.status,
                "headers": resp_headers,
                "body": body,
            }

    def _do(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        bypass_cache: bool = False,
        explicit_ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        headers = headers or {}
        key = self._build_cache_key(method, url)

        if not bypass_cache:
            entry = self._cache.get(key)
            if entry is not None:
                if has_validators(entry):
                    cond = conditional_headers(entry)
                    merged = {**headers, **cond}
                    try:
                        result = with_retry(self._retry, self._fetch, method, url, merged)
                        if result["status"] == 304:
                            self._metrics.record_hit()
                            return handle_304(entry)
                    except urllib.error.HTTPError:
                        pass
                self._metrics.record_hit()
                return entry.to_dict()

        if bypass_cache:
            self._metrics.record_bypass()
        else:
            self._metrics.record_miss()

        try:
            result = with_retry(self._retry, self._fetch, method, url, headers)
        except Exception:
            self._metrics.record_error()
            raise

        if is_cacheable(result["status"]) and not bypass_cache:
            ttl = resolve(
                explicit_ttl,
                result["headers"],
                self._default_ttl,
            )
            if ttl > 0:
                self._cache.set(key, result, ttl)

        return result
