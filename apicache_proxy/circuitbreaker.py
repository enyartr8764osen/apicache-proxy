"""Simple circuit breaker to stop hammering failing upstream APIs."""

import time
from enum import Enum
from typing import Optional


class State(Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # failing; requests blocked
    HALF_OPEN = "half_open"  # probe request allowed


class CircuitBreaker:
    """Tracks consecutive failures and opens the circuit when the threshold
    is exceeded.  After *recovery_timeout* seconds the circuit moves to
    HALF_OPEN so that the next request can probe the upstream service.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout must be >= 0")
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state: State = State.CLOSED
        self._failures: int = 0
        self._opened_at: Optional[float] = None

    @property
    def state(self) -> State:
        if self._state is State.OPEN:
            if self._opened_at is not None:
                elapsed = time.monotonic() - self._opened_at
                if elapsed >= self.recovery_timeout:
                    self._state = State.HALF_OPEN
        return self._state

    def is_open(self) -> bool:
        """Return True when requests should be blocked."""
        return self.state is State.OPEN

    def record_success(self) -> None:
        """Call after a successful upstream response."""
        self._failures = 0
        self._opened_at = None
        self._state = State.CLOSED

    def record_failure(self) -> None:
        """Call after a failed upstream request."""
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = State.OPEN
            self._opened_at = time.monotonic()

    def reset(self) -> None:
        """Manually reset the breaker to CLOSED."""
        self._failures = 0
        self._opened_at = None
        self._state = State.CLOSED

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "failures": self._failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }
