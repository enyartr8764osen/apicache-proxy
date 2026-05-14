"""Per-request timeout configuration with sensible defaults."""
from __future__ import annotations

DEFAULT_CONNECT_TIMEOUT = 5.0   # seconds
DEFAULT_READ_TIMEOUT = 30.0     # seconds


class TimeoutConfig:
    """Holds connect and read timeout values for outbound HTTP requests."""

    def __init__(
        self,
        connect: float = DEFAULT_CONNECT_TIMEOUT,
        read: float = DEFAULT_READ_TIMEOUT,
    ) -> None:
        if connect <= 0:
            raise ValueError(f"connect timeout must be positive, got {connect}")
        if read <= 0:
            raise ValueError(f"read timeout must be positive, got {read}")
        self.connect = float(connect)
        self.read = float(read)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def as_tuple(self) -> tuple[float, float]:
        """Return ``(connect, read)`` suitable for *requests* library."""
        return (self.connect, self.read)

    def to_dict(self) -> dict[str, float]:
        return {"connect": self.connect, "read": self.read}

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "TimeoutConfig":
        return cls(connect=data["connect"], read=data["read"])

    @classmethod
    def from_args(
        cls,
        connect: float | None = None,
        read: float | None = None,
    ) -> "TimeoutConfig":
        """Build a ``TimeoutConfig`` from optional CLI / caller values,
        falling back to defaults for any ``None`` argument."""
        return cls(
            connect=connect if connect is not None else DEFAULT_CONNECT_TIMEOUT,
            read=read if read is not None else DEFAULT_READ_TIMEOUT,
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"TimeoutConfig(connect={self.connect}, read={self.read})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimeoutConfig):
            return NotImplemented
        return self.connect == other.connect and self.read == other.read
