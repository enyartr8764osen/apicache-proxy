"""
Simple per-host rate limiting to avoid hammering upstream APIs
during cache misses or bypass requests.
"""

import time
import threading
from collections import deque
from typing import Optional


class RateLimiter:
    """Token-bucket style rate limiter keyed by hostname.

    Parameters
    ----------
    requests_per_second:
        Maximum average request rate per host.  ``None`` disables limiting.
    burst:
        Maximum number of requests allowed in a single burst (defaults to
        ``requests_per_second`` rounded up, minimum 1).
    """

    def __init__(
        self,
        requests_per_second: Optional[float] = None,
        burst: Optional[int] = None,
    ) -> None:
        self.requests_per_second = requests_per_second
        if requests_per_second is not None:
            self.burst: int = burst if burst is not None else max(1, int(requests_per_second))
            self._window: float = 1.0 / requests_per_second
        else:
            self.burst = 0
            self._window = 0.0

        # Maps hostname -> deque of timestamps (oldest first)
        self._history: dict[str, deque] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def is_limited(self) -> bool:
        """Return *True* when rate limiting is active."""
        return self.requests_per_second is not None

    def acquire(self, host: str) -> float:
        """Block until the request is allowed and return the wait time in seconds.

        If rate limiting is disabled the call returns immediately with ``0.0``.
        """
        if not self.is_limited():
            return 0.0

        with self._lock:
            now = time.monotonic()
            timestamps = self._history.setdefault(host, deque())

            # Drop timestamps outside the rolling window
            cutoff = now - self.burst * self._window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.burst:
                # Must wait until the oldest slot expires
                wait = (timestamps[0] + self.burst * self._window) - now
                if wait > 0:
                    time.sleep(wait)
                    now = time.monotonic()

            timestamps.append(now)
            return max(0.0, now - (timestamps[-2] if len(timestamps) > 1 else now))

    def reset(self, host: Optional[str] = None) -> None:
        """Clear recorded history for *host*, or all hosts if *host* is ``None``."""
        with self._lock:
            if host is None:
                self._history.clear()
            else:
                self._history.pop(host, None)
