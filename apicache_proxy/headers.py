"""Utilities for filtering and normalising HTTP headers."""

from __future__ import annotations

from typing import Dict, Iterable, Mapping

# Headers that should never be stored in the cache or forwarded verbatim.
_HOP_BY_HOP = frozenset(
    [
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    ]
)

# Headers whose values should NOT be included when building a cache key so
# that cosmetic differences don't cause unnecessary cache misses.
_CACHE_KEY_EXCLUDE = frozenset(
    [
        "accept-encoding",
        "user-agent",
        "referer",
        "x-request-id",
        "x-forwarded-for",
    ]
)


def filter_hop_by_hop(headers: Mapping[str, str]) -> Dict[str, str]:
    """Return a copy of *headers* with hop-by-hop headers removed."""
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in _HOP_BY_HOP
    }


def normalise(headers: Mapping[str, str]) -> Dict[str, str]:
    """Return headers with lower-cased keys and stripped values."""
    return {k.lower().strip(): v.strip() for k, v in headers.items()}


def headers_for_cache_key(
    headers: Mapping[str, str],
    extra_exclude: Iterable[str] | None = None,
) -> Dict[str, str]:
    """Return a filtered, sorted dict suitable for inclusion in a cache key.

    Removes hop-by-hop headers, cache-key-excluded headers, and any
    caller-supplied *extra_exclude* names.
    """
    exclude = _HOP_BY_HOP | _CACHE_KEY_EXCLUDE
    if extra_exclude:
        exclude = exclude | frozenset(k.lower() for k in extra_exclude)
    normalised = normalise(headers)
    return {k: v for k, v in sorted(normalised.items()) if k not in exclude}
