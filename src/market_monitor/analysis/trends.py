"""Historical change over time.

A lookback is a moment, not a row offset: runs get missed and markets close, so
"1 day ago" means the nearest stored observation to that instant, within a
tolerance, or nothing at all.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..storage.repositories import Repository

HORIZONS: dict[str, timedelta] = {
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def pct_change(current: float, past: float) -> float | None:
    if past == 0:
        return None
    return (current / past - 1.0) * 100.0


def trend(
    repo: Repository,
    metric_name: str,
    current: float,
    now: datetime,
    horizon: str,
    tolerance: timedelta,
) -> float | None:
    """Percentage change of one metric over one horizon, or None if no history."""
    delta = HORIZONS.get(horizon)
    if delta is None:
        raise KeyError(f"unknown horizon {horizon!r}")
    found = repo.metric_near(metric_name, now - delta, tolerance)
    if found is None:
        return None
    return pct_change(current, found[0])


def trends(
    repo: Repository,
    metric_name: str,
    current: float,
    now: datetime,
    horizons: tuple[str, ...] = ("1d", "3d", "7d"),
    tolerance: timedelta = timedelta(hours=12),
) -> dict[str, float | None]:
    return {h: trend(repo, metric_name, current, now, h, tolerance) for h in horizons}


def direction(change: float | None, tolerance_pct: float) -> str:
    """RISING / FALLING / STABLE / UNKNOWN — never a silent zero."""
    if change is None:
        return "UNKNOWN"
    if change > tolerance_pct:
        return "RISING"
    if change < -tolerance_pct:
        return "FALLING"
    return "STABLE"


def gap_momentum(current_gap_pct: float, past_gap_pct: float | None, tolerance_pct: float) -> str:
    """EXPANDING / CONTRACTING / STABLE, measured on distance from parity."""
    if past_gap_pct is None:
        return "UNKNOWN"
    change = abs(current_gap_pct) - abs(past_gap_pct)
    if change > tolerance_pct:
        return "EXPANDING"
    if change < -tolerance_pct:
        return "CONTRACTING"
    return "STABLE"
