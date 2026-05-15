"""A proxy that serves responses from a ReplayLibrary instead of the network."""
from __future__ import annotations

from typing import Dict, Optional

from .replay import ReplayEntry, ReplayLibrary


class _ReplayResponse:
    """Minimal response-like object returned by ReplayProxy."""

    def __init__(self, status_code: int, headers: Dict[str, str],
                 text: str) -> None:
        self.status_code = status_code
        self.headers = headers
        self.text = text

    def json(self):
        import json
        return json.loads(self.text)


class ReplayProxy:
    """Proxy that returns pre-recorded responses; raises on unknown requests."""

    def __init__(self, library: ReplayLibrary,
                 strict: bool = True) -> None:
        self._library = library
        self._strict = strict
        self._miss_count = 0

    @property
    def miss_count(self) -> int:
        return self._miss_count

    def get(self, url: str, **kwargs) -> _ReplayResponse:
        return self.request("GET", url, **kwargs)

    def request(self, method: str, url: str,
                **kwargs) -> _ReplayResponse:  # noqa: ARG002
        entry: Optional[ReplayEntry] = self._library.find(method, url)
        if entry is None:
            self._miss_count += 1
            if self._strict:
                raise KeyError(
                    f"No replay entry for {method} {url}"
                )
            return _ReplayResponse(
                status_code=404,
                headers={"Content-Type": "text/plain"},
                text="",
            )
        return _ReplayResponse(
            status_code=entry.status,
            headers=entry.headers,
            text=entry.body,
        )
