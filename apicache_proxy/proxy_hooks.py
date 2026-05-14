"""Integration helpers: wire a HookRegistry into CachingProxy calls.

This module provides ``HookedProxy`` — a thin subclass of ``CachingProxy``
that fires registered lifecycle hooks around every request.
"""
from __future__ import annotations

from typing import Optional

from apicache_proxy.proxy import CachingProxy
from apicache_proxy.hooks import HookRegistry


class HookedProxy(CachingProxy):
    """CachingProxy extended with pre/post hook support."""

    def __init__(self, *args, hooks: Optional[HookRegistry] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.hooks: HookRegistry = hooks or HookRegistry()

    # ------------------------------------------------------------------
    # Override request to fire hooks
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        bypass_cache: bool = False,
        **kwargs,
    ):
        headers = headers or {}
        cache_key = self._build_cache_key(method, url, headers)
        cached_entry = self.cache.get(cache_key)

        if cached_entry is not None and not bypass_cache:
            # Serve from cache — fire post hook only (no network call)
            self.hooks.fire_post_response(method, url, cached_entry.status_code, True)
            return self._entry_to_response(cached_entry)

        # About to hit the network
        self.hooks.fire_pre_request(method, url, headers)
        response = super().request(
            method, url, headers=headers, bypass_cache=bypass_cache, **kwargs
        )
        status = response.status_code if hasattr(response, "status_code") else 0
        self.hooks.fire_post_response(method, url, status, False)
        return response

    def _entry_to_response(self, entry):
        """Convert a CacheEntry back to a minimal response-like object."""
        import types
        r = types.SimpleNamespace()
        r.status_code = entry.status_code
        r.headers = dict(entry.headers)
        r.content = entry.body if isinstance(entry.body, bytes) else entry.body.encode()
        r.text = r.content.decode(errors="replace")
        return r
