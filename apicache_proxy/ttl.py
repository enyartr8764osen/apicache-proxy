"""TTL (time-to-live) resolution helpers.

Priority order for determining TTL:
  1. Explicit ``ttl`` kwarg passed by the caller
  2. ``Cache-Control: max-age=N`` response header
  3. ``Expires`` response header
  4. Configured default TTL
"""

from __future__ import annotations

import email.utils
import time
from typing import Mapping, Optional

DEFAULT_TTL: int = 300  # seconds


def resolve(
    headers: Mapping[str, str],
    *,
    explicit_ttl: Optional[int] = None,
    default_ttl: int = DEFAULT_TTL,
) -> int:
    """Return the TTL in seconds for a response.

    Parameters
    ----------
    headers:
        Response headers (case-insensitive mapping is fine; we normalise
        internally).
    explicit_ttl:
        If provided, this value wins unconditionally.
    default_ttl:
        Fallback when no cache directive is found in the headers.
    """
    if explicit_ttl is not None:
        return max(0, explicit_ttl)

    normalised = {k.lower(): v for k, v in headers.items()}

    # 1. Cache-Control: max-age
    cc = normalised.get("cache-control", "")
    for directive in cc.split(","):
        directive = directive.strip()
        if directive.lower().startswith("max-age="):
            try:
                return max(0, int(directive.split("=", 1)[1].strip()))
            except (ValueError, IndexError):
                pass

    # 2. Expires header
    expires_str = normalised.get("expires", "")
    if expires_str:
        try:
            expires_ts = email.utils.parsedate_to_datetime(expires_str).timestamp()
            ttl = int(expires_ts - time.time())
            return max(0, ttl)
        except Exception:  # noqa: BLE001
            pass

    return default_ttl


def is_cacheable(headers: Mapping[str, str]) -> bool:
    """Return False when response headers explicitly forbid caching."""
    normalised = {k.lower(): v for k, v in headers.items()}
    cc = normalised.get("cache-control", "")
    directives = {d.strip().lower() for d in cc.split(",")}
    return not directives.intersection({"no-store", "no-cache", "private"})
