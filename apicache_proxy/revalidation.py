"""Conditional-request helpers for cache revalidation.

Supports ``ETag`` / ``If-None-Match`` and
``Last-Modified`` / ``If-Modified-Since`` round-trips.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from apicache_proxy.cache import CacheEntry


def conditional_headers(entry: CacheEntry) -> Dict[str, str]:
    """Build request headers that ask the server to revalidate *entry*.

    Returns an empty dict when the cached entry carries no validator.
    """
    headers: Dict[str, str] = {}
    resp_headers = {k.lower(): v for k, v in entry.response_headers.items()}

    etag = resp_headers.get("etag")
    if etag:
        headers["If-None-Match"] = etag

    last_modified = resp_headers.get("last-modified")
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    return headers


def handle_304(
    cached: CacheEntry,
    new_headers: Dict[str, str],
    new_ttl: int,
) -> CacheEntry:
    """Merge a 304 Not Modified response into *cached*.

    The server may return updated headers (e.g. a new ``Cache-Control``)
    alongside the 304.  We keep the original body but refresh the metadata.
    """
    merged_headers = dict(cached.response_headers)
    for key, value in new_headers.items():
        if key.lower() not in ("content-length",):
            merged_headers[key] = value

    return CacheEntry(
        status_code=cached.status_code,
        response_headers=merged_headers,
        body=cached.body,
        ttl=new_ttl,
    )


def has_validators(entry: CacheEntry) -> bool:
    """Return True when *entry* carries at least one revalidation header."""
    resp_headers = {k.lower(): v for k, v in entry.response_headers.items()}
    return bool(resp_headers.get("etag") or resp_headers.get("last-modified"))
