"""Replay recorded HTTP interactions from a fixture file."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


class ReplayEntry:
    """A single recorded request/response pair."""

    def __init__(self, method: str, url: str, status: int,
                 headers: Dict[str, str], body: str) -> None:
        self.method = method.upper()
        self.url = url
        self.status = status
        self.headers = headers
        self.body = body

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "url": self.url,
            "status": self.status,
            "headers": self.headers,
            "body": self.body,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayEntry":
        return cls(
            method=data["method"],
            url=data["url"],
            status=data["status"],
            headers=data.get("headers", {}),
            body=data.get("body", ""),
        )


class ReplayLibrary:
    """Load and query a collection of replay fixtures."""

    def __init__(self, entries: Optional[List[ReplayEntry]] = None) -> None:
        self._entries: List[ReplayEntry] = entries or []

    @classmethod
    def from_file(cls, path: str | Path) -> "ReplayLibrary":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = [ReplayEntry.from_dict(e) for e in data.get("entries", [])]
        return cls(entries)

    def save(self, path: str | Path) -> None:
        payload = {"entries": [e.to_dict() for e in self._entries]}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def record(self, entry: ReplayEntry) -> None:
        self._entries.append(entry)

    def find(self, method: str, url: str) -> Optional[ReplayEntry]:
        method = method.upper()
        for entry in self._entries:
            if entry.method == method and entry.url == url:
                return entry
        return None

    def __len__(self) -> int:
        return len(self._entries)
