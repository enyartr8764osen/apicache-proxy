"""Tests for the 'stats' CLI command including metrics output."""
from __future__ import annotations

import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from apicache_proxy.cli import build_parser, cmd_stats
from apicache_proxy.metrics import Metrics


@pytest.fixture()
def parser():
    return build_parser()


def _make_metrics(hits=3, misses=2, bypasses=1, errors=0) -> Metrics:
    m = Metrics()
    for _ in range(hits):
        m.record_hit()
    for _ in range(misses):
        m.record_miss()
    for _ in range(bypasses):
        m.record_bypass()
    for _ in range(errors):
        m.record_error()
    return m


def test_metrics_to_dict_structure():
    m = _make_metrics()
    d = m.to_dict()
    assert d["hits"] == 3
    assert d["misses"] == 2
    assert d["bypasses"] == 1
    assert d["total"] == 6
    assert abs(d["hit_rate"] - 0.5) < 1e-4


def test_metrics_hit_rate_rounds_to_4dp():
    m = _make_metrics(hits=1, misses=2, bypasses=0)
    d = m.to_dict()
    # 1/3 rounded to 4 dp
    assert d["hit_rate"] == round(1 / 3, 4)


def test_metrics_reset_after_stats_call():
    m = _make_metrics(hits=5)
    m.reset()
    assert m.to_dict()["total"] == 0
    assert m.to_dict()["hit_rate"] == 0.0


def test_cmd_stats_prints_json(capsys):
    mock_storage = MagicMock()
    mock_storage.stats.return_value = {"entries": 4, "size_bytes": 1024}

    with patch("apicache_proxy.cli.DiskStorage", return_value=mock_storage):
        args = MagicMock()
        args.cache_dir = "/tmp/test_cache"
        cmd_stats(args)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "entries" in data
    assert data["entries"] == 4


def test_parser_stats_subcommand_exists(parser):
    args = parser.parse_args(["stats"])
    assert args.subcommand == "stats"
