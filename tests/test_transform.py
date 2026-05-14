"""Tests for apicache_proxy.transform."""

import json
import pytest

from apicache_proxy.transform import (
    apply,
    inject_headers,
    strip_json_fields,
)


# ---------------------------------------------------------------------------
# strip_json_fields
# ---------------------------------------------------------------------------

def test_strip_no_fields_returns_original():
    body = b'{"a": 1}'
    assert strip_json_fields(body, [], "application/json") is body


def test_strip_non_json_content_type_returns_original():
    body = b'{"a": 1}'
    result = strip_json_fields(body, ["a"], "text/plain")
    assert result is body


def test_strip_invalid_json_returns_original():
    body = b"not json"
    result = strip_json_fields(body, ["a"], "application/json")
    assert result is body


def test_strip_top_level_field():
    body = json.dumps({"ts": "2024-01-01", "data": 42}).encode()
    result = strip_json_fields(body, ["ts"], "application/json")
    obj = json.loads(result)
    assert "ts" not in obj
    assert obj["data"] == 42


def test_strip_nested_field():
    body = json.dumps({"meta": {"request_id": "abc", "v": 1}, "x": 2}).encode()
    result = strip_json_fields(body, ["meta.request_id"], "application/json")
    obj = json.loads(result)
    assert "request_id" not in obj["meta"]
    assert obj["meta"]["v"] == 1


def test_strip_missing_field_is_silent():
    body = json.dumps({"a": 1}).encode()
    result = strip_json_fields(body, ["nonexistent"], "application/json")
    assert json.loads(result) == {"a": 1}


def test_strip_multiple_fields():
    body = json.dumps({"a": 1, "b": 2, "c": 3}).encode()
    result = strip_json_fields(body, ["a", "c"], "application/json")
    assert json.loads(result) == {"b": 2}


def test_strip_content_type_with_charset():
    body = json.dumps({"ts": "x", "v": 1}).encode()
    result = strip_json_fields(body, ["ts"], "application/json; charset=utf-8")
    obj = json.loads(result)
    assert "ts" not in obj


# ---------------------------------------------------------------------------
# inject_headers
# ---------------------------------------------------------------------------

def test_inject_none_returns_copy():
    h = {"Content-Type": "application/json"}
    result = inject_headers(h, None)
    assert result == h
    assert result is not h


def test_inject_adds_new_header():
    result = inject_headers({"A": "1"}, {"X-Cache": "HIT"})
    assert result["X-Cache"] == "HIT"
    assert result["A"] == "1"


def test_inject_overwrites_existing():
    result = inject_headers({"X-Foo": "old"}, {"X-Foo": "new"})
    assert result["X-Foo"] == "new"


# ---------------------------------------------------------------------------
# apply (integration)
# ---------------------------------------------------------------------------

def test_apply_strips_and_injects():
    body = json.dumps({"ts": "2024", "val": 7}).encode()
    headers = {"content-type": "application/json"}
    new_body, new_headers = apply(
        body, headers, strip_fields=["ts"], inject={"X-Transformed": "1"}
    )
    assert "ts" not in json.loads(new_body)
    assert new_headers["X-Transformed"] == "1"


def test_apply_no_options_passthrough():
    body = b"hello"
    headers = {"content-type": "text/plain"}
    new_body, new_headers = apply(body, headers)
    assert new_body == body
    assert new_headers == headers
