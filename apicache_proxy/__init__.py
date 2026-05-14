"""apicache-proxy: Lightweight local caching proxy for REST APIs."""

from apicache_proxy.cache import FileCache, CacheEntry, DEFAULT_CACHE_DIR, DEFAULT_TTL

__all__ = ["FileCache", "CacheEntry", "DEFAULT_CACHE_DIR", "DEFAULT_TTL"]
__version__ = "0.1.0"


def get_version() -> str:
    """Return the current version of apicache-proxy.

    Returns:
        str: The version string in semver format.

    Example:
        >>> import apicache_proxy
        >>> apicache_proxy.get_version()
        '0.1.0'
    """
    return __version__
