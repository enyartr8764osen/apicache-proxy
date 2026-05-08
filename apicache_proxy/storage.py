"""Persistent disk-based storage backend for the cache."""

import json
import os
import logging
from pathlib import Path
from typing import Optional

from apicache_proxy.cache import CacheEntry

logger = logging.getLogger(__name__)


class DiskStorage:
    """Persists cache entries to a local directory as JSON files."""

    def __init__(self, cache_dir: str = ".apicache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("DiskStorage initialized at '%s'", self.cache_dir)

    def _entry_path(self, key: str) -> Path:
        """Return the file path for a given cache key."""
        safe_key = key.replace("/", "_").replace(":", "_").replace("?", "_")
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[CacheEntry]:
        """Load a CacheEntry from disk, or return None if not found."""
        path = self._entry_path(key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            entry = CacheEntry.from_dict(data)
            if entry.is_expired():
                logger.debug("Disk entry for '%s' is expired, removing.", key)
                path.unlink(missing_ok=True)
                return None
            return entry
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Failed to load cache entry for '%s': %s", key, exc)
            return None

    def set(self, key: str, entry: CacheEntry) -> None:
        """Persist a CacheEntry to disk."""
        path = self._entry_path(key)
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2)
            logger.debug("Persisted cache entry for '%s' to '%s'", key, path)
        except OSError as exc:
            logger.error("Could not write cache entry for '%s': %s", key, exc)

    def delete(self, key: str) -> bool:
        """Remove a cached entry from disk. Returns True if it existed."""
        path = self._entry_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        """Delete all cached entries. Returns the number of files removed."""
        removed = 0
        for json_file in self.cache_dir.glob("*.json"):
            json_file.unlink()
            removed += 1
        logger.debug("Cleared %d entries from disk cache.", removed)
        return removed

    def size(self) -> int:
        """Return the number of cached entry files on disk."""
        return len(list(self.cache_dir.glob("*.json")))
