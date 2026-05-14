"""Proxy wrapper that enforces configurable request timeouts."""
from __future__ import annotations

import requests

from .proxy import CachingProxy
from .timeout import TimeoutConfig


class TimeoutProxy:
    """Wraps :class:`CachingProxy` and injects timeout values into every
    outbound network request.  Cache hits are returned immediately without
    touching the network, so the timeout only applies to actual HTTP calls.
    """

    def __init__(
        self,
        proxy: CachingProxy,
        timeout: TimeoutConfig | None = None,
    ) -> None:
        self._proxy = proxy
        self._timeout = timeout or TimeoutConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def timeout(self) -> TimeoutConfig:
        return self._timeout

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def request(self, method: str, url: str, **kwargs):
        """Forward to the inner proxy, ensuring *timeout* is set."""
        kwargs.setdefault("timeout", self._timeout.as_tuple)
        try:
            return self._proxy.request(method, url, **kwargs)
        except requests.exceptions.Timeout as exc:
            raise TimeoutError(
                f"{method} {url} timed out "
                f"(connect={self._timeout.connect}s, read={self._timeout.read}s)"
            ) from exc

    def stats(self) -> dict:
        """Delegate stats to the inner proxy if available."""
        inner = self._proxy
        if hasattr(inner, "stats"):
            return inner.stats()
        return {}
