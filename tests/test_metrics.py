"""Tests for apicache_proxy.metrics."""
import pytest
from apicache_proxy.metrics import Metrics


@pytest.fixture()
def m() -> Metrics:
    return Metrics()


def test_initial_state_is_zero(m):
    assert m.hits == 0
    assert m.misses == 0
    assert m.bypasses == 0
    assert m.errors == 0


def test_total_sums_hits_misses_bypasses(m):
    m.record_hit()
    m.record_miss()
    m.record_bypass()
    assert m.total == 3
    assert m.errors not in [m.total]  # errors excluded from total


def test_errors_excluded_from_total(m):
    m.record_error()
    m.record_error()
    assert m.total == 0
    assert m.errors == 2


def test_hit_rate_zero_when_no_requests(m):
    assert m.hit_rate == 0.0


def test_hit_rate_all_hits(m):
    m.record_hit()
    m.record_hit()
    assert m.hit_rate == 1.0


def test_hit_rate_mixed(m):
    m.record_hit()
    m.record_miss()
    m.record_miss()
    assert abs(m.hit_rate - 1 / 3) < 1e-9


def test_to_dict_contains_expected_keys(m):
    m.record_hit()
    d = m.to_dict()
    assert set(d.keys()) == {"hits", "misses", "bypasses", "errors", "total", "hit_rate"}


def test_to_dict_values_consistent(m):
    m.record_hit()
    m.record_miss()
    d = m.to_dict()
    assert d["hits"] == 1
    assert d["misses"] == 1
    assert d["total"] == 2
    assert d["hit_rate"] == 0.5


def test_reset_clears_all_counters(m):
    m.record_hit()
    m.record_miss()
    m.record_bypass()
    m.record_error()
    m.reset()
    assert m.hits == m.misses == m.bypasses == m.errors == 0


def test_thread_safety_increments():
    """Concurrent increments should not lose counts."""
    import threading

    m = Metrics()
    threads = [threading.Thread(target=m.record_hit) for _ in range(200)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert m.hits == 200
