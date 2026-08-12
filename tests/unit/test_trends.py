from datetime import timedelta

import pytest

from market_monitor.analysis.trends import direction, gap_momentum, pct_change, trend, trends
from market_monitor.domain.models import Metric
from tests.conftest import AT


def seed(repo, snapshot, name: str, points: list[tuple[float, float]]) -> None:
    """points = [(days_ago, value)]"""
    sid = repo.save_snapshot(snapshot())
    for days_ago, value in points:
        repo.save_metrics(
            sid, [Metric(name, value, "toman/usd", "1.0")], AT - timedelta(days=days_ago)
        )


def test_pct_change_basic():
    assert pct_change(110.0, 100.0) == pytest.approx(10.0)
    assert pct_change(100.0, 0.0) is None


def test_trend_reads_the_nearest_observation(repo, snapshot):
    seed(repo, snapshot, "usd_market", [(1, 180_000.0), (3, 175_000.0)])
    assert trend(repo, "usd_market", 185_400.0, AT, "1d", timedelta(hours=12)) == pytest.approx(3.0)


def test_missing_history_returns_none_rather_than_zero(repo, snapshot):
    """A silent 0% would read as 'flat market' when it means 'we do not know'."""
    seed(repo, snapshot, "usd_market", [(1, 180_000.0)])
    result = trends(repo, "usd_market", 185_400.0, AT, ("1d", "3d", "7d"), timedelta(hours=12))
    assert result["1d"] is not None
    assert result["3d"] is None and result["7d"] is None


def test_unknown_horizon_is_a_programming_error(repo):
    with pytest.raises(KeyError):
        trend(repo, "usd_market", 1.0, AT, "42d", timedelta(hours=12))


@pytest.mark.parametrize(
    ("change", "expected"),
    [(1.0, "RISING"), (-1.0, "FALLING"), (0.1, "STABLE"), (None, "UNKNOWN")],
)
def test_direction_respects_tolerance(change, expected):
    assert direction(change, 0.25) == expected


def test_gap_momentum_measures_distance_from_parity_not_sign():
    # -2% -> -4% is the gap widening, even though the number got smaller.
    assert gap_momentum(-4.0, -2.0, 0.25) == "EXPANDING"
    assert gap_momentum(1.0, 3.0, 0.25) == "CONTRACTING"
    assert gap_momentum(2.0, 2.1, 0.25) == "STABLE"
    assert gap_momentum(2.0, None, 0.25) == "UNKNOWN"
