"""Tests for the CLI module."""

import json
import pytest
from unittest.mock import MagicMock, patch

from apicache_proxy.cli import build_parser, main, cmd_get, cmd_clear, cmd_stats


@pytest.fixture
def parser():
    return build_parser()


def test_parser_get_defaults(parser):
    args = parser.parse_args(["get", "https://api.example.com/data"])
    assert args.url == "https://api.example.com/data"
    assert args.ttl == 300
    assert args.cache_dir == ".apicache"
    assert args.bypass is False
    assert args.headers == {}


def test_parser_get_custom_options(parser):
    args = parser.parse_args([
        "get", "https://api.example.com/data",
        "--ttl", "60",
        "--cache-dir", "/tmp/cache",
        "--bypass",
        "--headers", '{"X-Token": "abc"}',
    ])
    assert args.ttl == 60
    assert args.cache_dir == "/tmp/cache"
    assert args.bypass is True
    assert args.headers == {"X-Token": "abc"}


def test_parser_clear_defaults(parser):
    args = parser.parse_args(["clear"])
    assert args.command == "clear"
    assert args.cache_dir == ".apicache"


def test_parser_stats_defaults(parser):
    args = parser.parse_args(["stats"])
    assert args.command == "stats"


def test_cmd_get_calls_proxy(capsys):
    mock_response = {"status_code": 200, "body": {"id": 1}}
    with patch("apicache_proxy.cli.DiskStorage") as MockStorage, \
         patch("apicache_proxy.cli.CachingProxy") as MockProxy:
        instance = MockProxy.return_value
        instance.get.return_value = mock_response

        parser = build_parser()
        args = parser.parse_args(["get", "https://api.example.com"])
        result = cmd_get(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "status_code" in captured.out


def test_cmd_clear_output(capsys):
    with patch("apicache_proxy.cli.DiskStorage") as MockStorage:
        MockStorage.return_value.clear.return_value = 3
        parser = build_parser()
        args = parser.parse_args(["clear"])
        result = cmd_clear(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "3" in captured.out


def test_cmd_stats_output(capsys):
    fake_stats = {"total_entries": 5, "valid_entries": 4, "expired_entries": 1,
                  "total_size_bytes": 2048, "cache_dir": ".apicache"}
    with patch("apicache_proxy.cli.DiskStorage") as MockStorage:
        MockStorage.return_value.stats.return_value = fake_stats
        parser = build_parser()
        args = parser.parse_args(["stats"])
        result = cmd_stats(args)

    assert result == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_entries"] == 5


def test_main_dispatches_get(capsys):
    mock_response = {"ok": True}
    with patch("apicache_proxy.cli.DiskStorage"), \
         patch("apicache_proxy.cli.CachingProxy") as MockProxy:
        MockProxy.return_value.get.return_value = mock_response
        rc = main(["get", "https://example.com"])
    assert rc == 0
