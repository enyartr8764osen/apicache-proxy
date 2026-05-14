"""Request/response hook system for apicache-proxy.

Allows users to register callables that are invoked at key points in the
request lifecycle: before a network request is made and after a response
(cached or live) is returned.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

# Hook signatures:
#   pre_request(method: str, url: str, headers: dict) -> None
#   post_response(method: str, url: str, status: int, cached: bool) -> None

PreRequestHook = Callable[[str, str, Dict], None]
PostResponseHook = Callable[[str, str, int, bool], None]


class HookRegistry:
    """Holds and dispatches lifecycle hooks."""

    def __init__(self) -> None:
        self._pre_request: List[PreRequestHook] = []
        self._post_response: List[PostResponseHook] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_pre_request(self, fn: PreRequestHook) -> None:
        """Register a hook called before every network request."""
        if not callable(fn):
            raise TypeError("pre_request hook must be callable")
        self._pre_request.append(fn)

    def register_post_response(self, fn: PostResponseHook) -> None:
        """Register a hook called after every response (cached or live)."""
        if not callable(fn):
            raise TypeError("post_response hook must be callable")
        self._post_response.append(fn)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def fire_pre_request(
        self, method: str, url: str, headers: Optional[Dict] = None
    ) -> None:
        headers = headers or {}
        for fn in self._pre_request:
            try:
                fn(method, url, headers)
            except Exception:  # pragma: no cover – hooks must not crash proxy
                pass

    def fire_post_response(
        self, method: str, url: str, status: int, cached: bool
    ) -> None:
        for fn in self._post_response:
            try:
                fn(method, url, status, cached)
            except Exception:  # pragma: no cover
                pass

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def pre_request_count(self) -> int:
        return len(self._pre_request)

    def post_response_count(self) -> int:
        return len(self._post_response)

    def clear(self) -> None:
        """Remove all registered hooks."""
        self._pre_request.clear()
        self._post_response.clear()
