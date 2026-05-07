"""apicache-proxy: Lightweight local caching proxy for REST APIs."""

from apicache_proxy.cache import FileCache, CacheEntry, DEFAULT_CACHE_DIR, DEFAULT_TTL

__all__ = ["FileCache", "CacheEntry", "DEFAULT_CACHE_DIR", "DEFAULT_TTL"]
__version__ = "0.1.0"
