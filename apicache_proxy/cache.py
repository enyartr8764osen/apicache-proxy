"""Simple file-based cache for HTTP responses."""

import hashlib
import json
import os
import time
from typing import Optional


DEFAULT_CACHE_DIR = ".apicache"
DEFAULT_TTL = 300  # seconds


class CacheEntry:
    def __init__(self, status_code: int, headers: dict, body: str, cached_at: float, ttl: int):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.cached_at = cached_at
        self.ttl = ttl

    def is_expired(self) -> bool:
        return (time.time() - self.cached_at) > self.ttl

    def to_dict(self) -> dict:
        return {
            "status_code": self.status_code,
            "headers": self.headers,
            "body": self.body,
            "cached_at": self.cached_at,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        return cls(
            status_code=data["status_code"],
            headers=data["headers"],
            body=data["body"],
            cached_at=data["cached_at"],
            ttl=data["ttl"],
        )


class FileCache:
    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR, ttl: int = DEFAULT_TTL):
        self.cache_dir = cache_dir
        self.ttl = ttl
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_key(self, method: str, url: str, body: Optional[str] = None) -> str:
        raw = f"{method.upper()}:{url}:{body or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, method: str, url: str, body: Optional[str] = None) -> Optional[CacheEntry]:
        key = self._cache_key(method, url, body)
        path = self._cache_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entry = CacheEntry.from_dict(data)
        if entry.is_expired():
            os.remove(path)
            return None
        return entry

    def set(self, method: str, url: str, status_code: int, headers: dict, body: str, body_key: Optional[str] = None) -> None:
        key = self._cache_key(method, url, body_key)
        path = self._cache_path(key)
        entry = CacheEntry(
            status_code=status_code,
            headers=headers,
            body=body,
            cached_at=time.time(),
            ttl=self.ttl,
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f, indent=2)

    def clear(self) -> int:
        removed = 0
        for fname in os.listdir(self.cache_dir):
            if fname.endswith(".json"):
                os.remove(os.path.join(self.cache_dir, fname))
                removed += 1
        return removed
