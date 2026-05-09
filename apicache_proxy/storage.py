"""Disk-backed persistent storage for cache entries."""

import json
import os
import time
from pathlib import Path
from typing import Optional

from apicache_proxy.cache import CacheEntry


class DiskStorage:
    """Stores cache entries as JSON files on disk."""

    def __init__(self, cache_dir: str = ".apicache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _entry_path(self, key: str) -> Path:
        safe_key = key.replace("/", "_").replace(":", "_").replace("?", "_")
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[CacheEntry]:
        path = self._entry_path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entry = CacheEntry.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            path.unlink(missing_ok=True)
            return None
        if entry.is_expired():
            path.unlink(missing_ok=True)
            return None
        return entry

    def set(self, key: str, entry: CacheEntry) -> None:
        path = self._entry_path(key)
        path.write_text(json.dumps(entry.to_dict(), default=str), encoding="utf-8")

    def delete(self, key: str) -> bool:
        path = self._entry_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        removed = 0
        for path in self.cache_dir.glob("*.json"):
            path.unlink(missing_ok=True)
            removed += 1
        return removed

    def stats(self) -> dict:
        total = 0
        expired = 0
        valid = 0
        total_size_bytes = 0
        for path in self.cache_dir.glob("*.json"):
            total += 1
            total_size_bytes += path.stat().st_size
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                entry = CacheEntry.from_dict(data)
                if entry.is_expired():
                    expired += 1
                else:
                    valid += 1
            except Exception:
                expired += 1
        return {
            "cache_dir": str(self.cache_dir),
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": expired,
            "total_size_bytes": total_size_bytes,
        }
