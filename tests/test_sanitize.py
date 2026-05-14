"""Tests for apicache_proxy.sanitize."""

import pytest

from apicache_proxy.sanitize import (
    is_sensitive_header,
    redact_headers,
    redact_query_params,
    strip_sensitive_headers,
)


# ---------------------------------------------------------------------------
# redact_headers
# ---------------------------------------------------------------------------


def test_redact_headers_replaces_authorization():
    result = redact_headers({"Authorization": "Bearer secret", "Content-Type": "application/json"})
    assert result["Authorization"] == "REDACTED"
    assert result["Content-Type"] == "application/json"


def test_redact_headers_case_insensitive_key_match():
    result = redact_headers({"COOKIE": "session=abc"})
    assert result["COOKIE"] == "REDACTED"


def test_redact_headers_preserves_all_keys():
    headers = {"Authorization": "x", "Accept": "*/*"}
    result = redact_headers(headers)
    assert set(result.keys()) == {"Authorization", "Accept"}


def test_redact_headers_extra_sensitive():
    result = redact_headers({"X-Custom-Secret": "top"}, extra=["x-custom-secret"])
    assert result["X-Custom-Secret"] == "REDACTED"


def test_redact_headers_empty_input():
    assert redact_headers({}) == {}


# ---------------------------------------------------------------------------
# strip_sensitive_headers
# ---------------------------------------------------------------------------


def test_strip_removes_authorization():
    result = strip_sensitive_headers({"Authorization": "Bearer t", "Accept": "*/*"})
    assert "Authorization" not in result
    assert "Accept" in result


def test_strip_removes_cookie():
    result = strip_sensitive_headers({"Cookie": "a=b", "Host": "example.com"})
    assert "Cookie" not in result


def test_strip_extra_header():
    result = strip_sensitive_headers(
        {"X-Internal-Token": "secret", "Accept": "*/*"},
        extra=["x-internal-token"],
    )
    assert "X-Internal-Token" not in result
    assert "Accept" in result


def test_strip_empty_input():
    assert strip_sensitive_headers({}) == {}


# ---------------------------------------------------------------------------
# redact_query_params
# ---------------------------------------------------------------------------


def test_redact_params_replaces_api_key():
    params = [("api_key", "supersecret"), ("q", "python")]
    result = redact_query_params(params)
    assert ("api_key", "REDACTED") in result
    assert ("q", "python") in result


def test_redact_params_case_insensitive():
    params = [("API_KEY", "s3cr3t")]
    result = redact_query_params(params)
    assert result[0][1] == "REDACTED"


def test_redact_params_extra_param():
    params = [("my_secret", "val"), ("page", "1")]
    result = redact_query_params(params, extra=["my_secret"])
    assert ("my_secret", "REDACTED") in result
    assert ("page", "1") in result


def test_redact_params_empty_list():
    assert redact_query_params([]) == []


# ---------------------------------------------------------------------------
# is_sensitive_header
# ---------------------------------------------------------------------------


def test_is_sensitive_known_header():
    assert is_sensitive_header("Authorization") is True


def test_is_sensitive_case_insensitive():
    assert is_sensitive_header("x-api-key") is True
    assert is_sensitive_header("X-API-KEY") is True


def test_is_not_sensitive_normal_header():
    assert is_sensitive_header("Content-Type") is False


def test_is_sensitive_extra():
    assert is_sensitive_header("X-My-Token", extra=["x-my-token"]) is True
