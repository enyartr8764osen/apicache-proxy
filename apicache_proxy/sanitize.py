"""
Request sanitization: strip or redact sensitive headers and query
parameters before they are forwarded upstream or stored in the cache.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Tuple

# Headers that commonly carry credentials and must never be cached.
_DEFAULT_SENSITIVE_HEADERS: frozenset[str] = frozenset(
    [
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
    ]
)

# Query-string parameter names whose values should be redacted in stored keys.
_DEFAULT_SENSITIVE_PARAMS: frozenset[str] = frozenset(
    [
        "api_key",
        "apikey",
        "access_token",
        "token",
        "secret",
        "password",
        "passwd",
    ]
)

_REDACTED = "REDACTED"


def redact_headers(
    headers: Dict[str, str],
    extra: Iterable[str] | None = None,
) -> Dict[str, str]:
    """Return a copy of *headers* with sensitive values replaced.

    Keys are compared case-insensitively.  Sensitive headers are kept in
    the returned dict so callers can see which keys were present, but
    their values are replaced with the string ``'REDACTED'``.
    """
    sensitive = _DEFAULT_SENSITIVE_HEADERS | (
        frozenset(h.lower() for h in extra) if extra else frozenset()
    )
    return {
        k: (_REDACTED if k.lower() in sensitive else v)
        for k, v in headers.items()
    }


def strip_sensitive_headers(
    headers: Dict[str, str],
    extra: Iterable[str] | None = None,
) -> Dict[str, str]:
    """Return a copy of *headers* with sensitive keys removed entirely."""
    sensitive = _DEFAULT_SENSITIVE_HEADERS | (
        frozenset(h.lower() for h in extra) if extra else frozenset()
    )
    return {k: v for k, v in headers.items() if k.lower() not in sensitive}


def redact_query_params(
    params: List[Tuple[str, str]],
    extra: Iterable[str] | None = None,
) -> List[Tuple[str, str]]:
    """Return a copy of *params* with sensitive values replaced.

    *params* is a list of ``(name, value)`` tuples as returned by
    ``urllib.parse.parse_qsl``.
    """
    sensitive = _DEFAULT_SENSITIVE_PARAMS | (
        frozenset(p.lower() for p in extra) if extra else frozenset()
    )
    return [
        (k, _REDACTED if k.lower() in sensitive else v)
        for k, v in params
    ]


def is_sensitive_header(name: str, extra: Iterable[str] | None = None) -> bool:
    """Return ``True`` if *name* is considered a sensitive header."""
    sensitive = _DEFAULT_SENSITIVE_HEADERS | (
        frozenset(h.lower() for h in extra) if extra else frozenset()
    )
    return name.lower() in sensitive
