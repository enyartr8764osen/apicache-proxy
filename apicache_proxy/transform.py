"""Response body transformations applied before caching.

Supports optional JSON field filtering and header injection so callers
can strip noisy or volatile fields (e.g. timestamps, request-ids) that
would otherwise cause spurious cache misses.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Optional


def _delete_nested(obj: Any, path: str) -> None:
    """Delete a dot-separated key path from a nested dict, silently ignoring
    missing intermediate keys."""
    parts = path.split(".", 1)
    if not isinstance(obj, dict):
        return
    if len(parts) == 1:
        obj.pop(parts[0], None)
    else:
        _delete_nested(obj.get(parts[0]), parts[1])


def strip_json_fields(
    body: bytes,
    fields: Iterable[str],
    content_type: str = "",
) -> bytes:
    """Remove *fields* (dot-notation paths) from a JSON response body.

    Returns the original *body* unchanged when:
    - *fields* is empty
    - the content-type is not JSON
    - the body cannot be decoded as JSON
    """
    fields = list(fields)
    if not fields:
        return body
    if "json" not in content_type.lower():
        return body
    try:
        obj = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return body
    for field in fields:
        _delete_nested(obj, field)
    return json.dumps(obj, separators=(",", ":")).encode()


def inject_headers(
    headers: Dict[str, str],
    extra: Optional[Dict[str, str]],
) -> Dict[str, str]:
    """Return a *new* headers dict with *extra* entries merged in.

    Keys in *extra* overwrite existing keys (case-preserved).
    """
    if not extra:
        return dict(headers)
    merged = dict(headers)
    merged.update(extra)
    return merged


def apply(
    body: bytes,
    headers: Dict[str, str],
    *,
    strip_fields: Optional[Iterable[str]] = None,
    inject: Optional[Dict[str, str]] = None,
) -> tuple[bytes, Dict[str, str]]:
    """Apply all configured transformations and return ``(body, headers)``."""
    content_type = headers.get("content-type", headers.get("Content-Type", ""))
    body = strip_json_fields(body, strip_fields or [], content_type)
    headers = inject_headers(headers, inject)
    return body, headers
