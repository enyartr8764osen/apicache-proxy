"""Retry logic with exponential back-off for transient network failures."""

import time
import logging
from typing import Callable, Tuple, Type

log = logging.getLogger(__name__)

# HTTP status codes that are worth retrying
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class RetryConfig:
    """Immutable configuration for the retry policy."""

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_base: float = 0.5,
        backoff_max: float = 10.0,
        retryable_statuses: Tuple[int, ...] = tuple(RETRYABLE_STATUSES),
        retryable_exceptions: Tuple[Type[Exception], ...] = (OSError, TimeoutError),
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if backoff_base < 0:
            raise ValueError("backoff_base must be >= 0")
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.retryable_statuses = set(retryable_statuses)
        self.retryable_exceptions = retryable_exceptions

    def delay_for(self, attempt: int) -> float:
        """Return seconds to sleep before *attempt* (0-indexed)."""
        if attempt == 0:
            return 0.0
        delay = self.backoff_base * (2 ** (attempt - 1))
        return min(delay, self.backoff_max)


def with_retry(fn: Callable, config: RetryConfig, _sleep: Callable = time.sleep):
    """Call *fn* up to config.max_attempts times, returning its result.

    *fn* must return an object with a numeric ``.status_code`` attribute.
    Raises the last exception (or returns the last response) when retries
    are exhausted.
    """
    last_exc: Exception | None = None
    last_response = None

    for attempt in range(config.max_attempts):
        delay = config.delay_for(attempt)
        if delay:
            log.debug("retry attempt %d — sleeping %.2fs", attempt, delay)
            _sleep(delay)

        try:
            response = fn()
        except config.retryable_exceptions as exc:  # type: ignore[misc]
            log.warning("retryable exception on attempt %d: %s", attempt, exc)
            last_exc = exc
            continue

        if response.status_code not in config.retryable_statuses:
            return response

        log.warning(
            "retryable status %d on attempt %d", response.status_code, attempt
        )
        last_response = response

    if last_exc is not None:
        raise last_exc
    return last_response
