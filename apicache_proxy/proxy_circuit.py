"""CachingProxy wrapper that integrates a CircuitBreaker.

When the circuit is OPEN, requests are short-circuited and a synthetic
503 response is returned immediately without touching the network.
After the recovery timeout the circuit moves to HALF_OPEN and one probe
request is allowed through; success closes the circuit, failure reopens it.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from apicache_proxy.circuitbreaker import CircuitBreaker, State
from apicache_proxy.proxy import CachingProxy

_OPEN_BODY = b'{"error": "circuit open", "message": "upstream unavailable"}'


class CircuitBreakerProxy:
    """Wraps a :class:`CachingProxy` with circuit-breaker logic."""

    def __init__(
        self,
        proxy: CachingProxy,
        breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self._proxy = proxy
        self.breaker = breaker or CircuitBreaker()

    # ------------------------------------------------------------------
    # public API mirrors CachingProxy.request
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Forward *method*/*url* through the breaker-guarded proxy."""
        state = self.breaker.state

        if state is State.OPEN:
            return self._open_response()

        # CLOSED or HALF_OPEN — attempt the real request
        try:
            response = self._proxy.request(method, url, **kwargs)
        except Exception:
            self.breaker.record_failure()
            raise

        status = response.get("status_code", 200)
        if status >= 500:
            self.breaker.record_failure()
        else:
            self.breaker.record_success()

        return response

    def get(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        return self.request("GET", url, **kwargs)

    def stats(self) -> Dict[str, Any]:
        return self.breaker.to_dict()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _open_response() -> Dict[str, Any]:
        return {
            "status_code": 503,
            "headers": {"Content-Type": "application/json"},
            "body": _OPEN_BODY,
            "from_cache": False,
        }
