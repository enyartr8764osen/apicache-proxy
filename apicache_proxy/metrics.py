"""In-memory metrics collector for cache hit/miss/bypass tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict


@dataclass
class Metrics:
    """Thread-safe counters for proxy request outcomes."""

    hits: int = 0
    misses: int = 0
    bypasses: int = 0
    errors: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    # ------------------------------------------------------------------ #
    # Mutators
    # ------------------------------------------------------------------ #

    def record_hit(self) -> None:
        with self._lock:
            self.hits += 1

    def record_miss(self) -> None:
        with self._lock:
            self.misses += 1

    def record_bypass(self) -> None:
        with self._lock:
            self.bypasses += 1

    def record_error(self) -> None:
        with self._lock:
            self.errors += 1

    # ------------------------------------------------------------------ #
    # Derived properties
    # ------------------------------------------------------------------ #

    @property
    def total(self) -> int:
        return self.hits + self.misses + self.bypasses

    @property
    def hit_rate(self) -> float:
        """Return hit rate in [0.0, 1.0]; 0.0 when no requests recorded."""
        if self.total == 0:
            return 0.0
        return self.hits / self.total

    # ------------------------------------------------------------------ #
    # Serialisation
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, object]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "bypasses": self.bypasses,
            "errors": self.errors,
            "total": self.total,
            "hit_rate": round(self.hit_rate, 4),
        }

    def reset(self) -> None:
        with self._lock:
            self.hits = 0
            self.misses = 0
            self.bypasses = 0
            self.errors = 0
