import hashlib
import json
import time
from typing import Optional

import requests

from .cache import Cache


class CachingProxy:
    """A lightweight caching proxy that intercepts HTTP requests and caches responses."""

    def __init__(self, ttl: int = 300, cache_dir: Optional[str] = None):
        """
        Initialize the caching proxy.

        Args:
            ttl: Time-to-live for cached responses in seconds (default: 300).
            cache_dir: Optional directory path for persistent cache storage.
        """
        self.ttl = ttl
        self.cache = Cache(default_ttl=ttl, cache_dir=cache_dir)

    def _build_cache_key(self, method: str, url: str, params: Optional[dict] = None, body: Optional[dict] = None) -> str:
        """Build a unique cache key from request components."""
        key_parts = {
            "method": method.upper(),
            "url": url,
            "params": params or {},
            "body": body or {},
        }
        key_str = json.dumps(key_parts, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        json_body: Optional[dict] = None,
        bypass_cache: bool = False,
        **kwargs,
    ) -> requests.Response:
        """
        Make an HTTP request, returning a cached response if available.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Target URL.
            params: Query parameters.
            headers: Request headers (not included in cache key).
            json_body: JSON request body.
            bypass_cache: If True, skip cache lookup and force a live request.
            **kwargs: Additional arguments passed to requests.

        Returns:
            A requests.Response object.
        """
        cache_key = self._build_cache_key(method, url, params, json_body)

        if not bypass_cache:
            cached = self.cache.get(method, cache_key)
            if cached is not None:
                return cached

        response = requests.request(
            method,
            url,
            params=params,
            headers=headers,
            json=json_body,
            **kwargs,
        )

        if response.ok:
            self.cache.set(method, cache_key, response, ttl=self.ttl)

        return response

    def get(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for GET requests."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for POST requests."""
        return self.request("POST", url, **kwargs)

    def invalidate(self, method: str, url: str, params: Optional[dict] = None, body: Optional[dict] = None) -> bool:
        """Remove a specific entry from the cache."""
        cache_key = self._build_cache_key(method, url, params, body)
        return self.cache.delete(method, cache_key)

    def clear(self) -> None:
        """Clear all cached responses."""
        self.cache.clear()
