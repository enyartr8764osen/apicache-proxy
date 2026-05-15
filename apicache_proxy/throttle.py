"""Response throttling: artificially delay responses to simulate slow APIs."""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ThrottleConfig:
    """Configuration for response throttling."""

    delay: float = 0.0          # fixed delay in seconds applied to every response
    per_host: dict = field(default_factory=dict)  # host -> delay overrides

    def __post_init__(self) -> None:
        if self.delay < 0:
            raise ValueError("delay must be >= 0")
        for host, d in self.per_host.items():
            if d < 0:
                raise ValueError(f"per-host delay for {host!r} must be >= 0")

    def delay_for(self, url: str) -> float:
        """Return the effective delay for *url*, checking per-host overrides first."""
        host = _extract_host(url)
        return self.per_host.get(host, self.delay)

    def to_dict(self) -> dict:
        return {"delay": self.delay, "per_host": dict(self.per_host)}

    @classmethod
    def from_dict(cls, data: dict) -> "ThrottleConfig":
        return cls(
            delay=float(data.get("delay", 0.0)),
            per_host={k: float(v) for k, v in data.get("per_host", {}).items()},
        )


class ThrottledProxy:
    """Proxy wrapper that sleeps before forwarding each response."""

    def __init__(self, inner, config: Optional[ThrottleConfig] = None) -> None:
        self._inner = inner
        self.config = config or ThrottleConfig()

    # ------------------------------------------------------------------ #
    # Public API mirroring CachingProxy
    # ------------------------------------------------------------------ #

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def request(self, method: str, url: str, **kwargs):
        response = self._inner.request(method, url, **kwargs)
        delay = self.config.delay_for(url)
        if delay > 0:
            time.sleep(delay)
        return response


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _extract_host(url: str) -> str:
    """Very small host extractor — avoids a full urllib import for hot path."""
    # Strip scheme
    if "://" in url:
        url = url.split("://", 1)[1]
    # Strip path / query
    return url.split("/")[0].split("?")[0].split("#")[0]
