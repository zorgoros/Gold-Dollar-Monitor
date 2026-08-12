"""The temporal gate (§14, §16), resolved 2026-08-12.

The rule these tests pin down: a closed Tehran session may never be paired with
a live world ounce. Either an ounce observation exists near that session in
stored history, or the analysis is not published.
"""

from datetime import timedelta

import pytest

from market_monitor.analysis.session import XAU_METRIC, align, parse_close, session_anchor
from market_monitor.domain.enums import AnalysisBasis, GateCode, Instrument
from market_monitor.domain.models import Metric
from market_monitor.timeutil import TEHRAN, to_tehran
from tests.conftest import AT, make_quote

REQUIRED = [Instrument.USD_IRR_FREE, Instrument.GOLD_18K, Instrument.XAU_USD]
FRESHNESS = {"usd_irr_free": 20, "gold_18k": 20, "xau_usd": 30}
SESSION_WINDOW = timedelta(minutes=20)
XAU_TOLERANCE = timedelta(hours=12)


def quotes_at(offset=timedelta(0), xau_offset=None):
    at = AT - offset
    xau_at = AT - (xau_offset if xau_offset is not None else offset)
    return {
        Instrument.USD_IRR_FREE: make_quote(Instrument.USD_IRR_FREE, 187_800.0, at),
        Instrument.GOLD_18K: make_quote(Instrument.GOLD_18K, 19_205_600.0, at),
        Instrument.XAU_USD: make_quote(Instrument.XAU_USD, 4_412.73, xau_at),
    }


def run(repo, quotes):
    return align(quotes, REQUIRED, repo, AT, FRESHNESS, SESSION_WINDOW, XAU_TOLERANCE)


def test_a_live_session_uses_the_live_ounce(repo):
    result = run(repo, quotes_at())
    assert result.ok
    assert result.basis is AnalysisBasis.LIVE
    assert result.xau_usd == 4_412.73


def test_a_closed_session_with_a_live_ounce_is_refused(repo):
    """The defect this module exists for: yesterday's Tehran close times a live
    ounce is not a market observation, and no history exists to fix it."""
    result = run(repo, quotes_at(offset=timedelta(hours=30), xau_offset=timedelta(0)))
    assert not result.ok
    assert GateCode.XAU_NOT_ALIGNED in result.codes
    assert "refusing to pair it with the live ounce" in result.diagnostics[0]


def test_a_closed_session_publishes_with_an_aligned_ounce_from_history(repo, snapshot):
    session_offset = timedelta(hours=30)
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(
        sid, [Metric(XAU_METRIC, 4_393.47, "usd/troy_oz", "1.1")], AT - session_offset
    )

    result = run(repo, quotes_at(offset=session_offset, xau_offset=timedelta(0)))
    assert result.ok
    assert result.basis is AnalysisBasis.LAST_CLOSE
    # the historical ounce, not the live 4,412.73 sitting in the snapshot
    assert result.xau_usd == 4_393.47
    assert result.reference_at == AT - session_offset


def test_history_outside_the_tolerance_does_not_count_as_aligned(repo, snapshot):
    session_offset = timedelta(hours=30)
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(
        sid,
        [Metric(XAU_METRIC, 4_393.47, "usd/troy_oz", "1.1")],
        AT - session_offset - timedelta(hours=20),
    )
    result = run(repo, quotes_at(offset=session_offset, xau_offset=timedelta(0)))
    assert not result.ok
    assert GateCode.XAU_NOT_ALIGNED in result.codes


def test_tehran_inputs_from_different_sessions_are_refused(repo):
    quotes = quotes_at()
    quotes[Instrument.GOLD_18K] = make_quote(
        Instrument.GOLD_18K, 19_205_600.0, AT - timedelta(days=7)
    )
    result = run(repo, quotes)
    assert not result.ok
    assert GateCode.SESSION_INCOHERENT in result.codes
    assert "span" in result.diagnostics[0]


def test_a_stale_ounce_with_a_live_session_also_looks_for_alignment(repo, snapshot):
    """Freshness is checked on both sides; the ounce feed can be the laggard."""
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(sid, [Metric(XAU_METRIC, 4_400.0, "usd/troy_oz", "1.1")], AT)

    result = run(repo, quotes_at(offset=timedelta(0), xau_offset=timedelta(hours=6)))
    assert result.ok
    assert result.basis is AnalysisBasis.LAST_CLOSE
    assert result.xau_usd == 4_400.0


def test_a_missing_ounce_cannot_be_aligned_at_all(repo):
    quotes = quotes_at()
    del quotes[Instrument.XAU_USD]
    result = run(repo, quotes)
    assert not result.ok
    assert GateCode.MISSING_MANDATORY in result.codes


def test_alignment_never_mutates_the_stored_quotes(repo, snapshot):
    """Source timestamps and quality flags are preserved exactly (§14 answer)."""
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(
        sid, [Metric(XAU_METRIC, 4_393.47, "usd/troy_oz", "1.1")], AT - timedelta(hours=30)
    )
    quotes = quotes_at(offset=timedelta(hours=30), xau_offset=timedelta(0))
    before = {i: (q.normalized_value, q.observed_at, q.quality_status) for i, q in quotes.items()}

    run(repo, quotes)

    after = {i: (q.normalized_value, q.observed_at, q.quality_status) for i, q in quotes.items()}
    assert before == after
    assert quotes[Instrument.XAU_USD].normalized_value == 4_412.73


@pytest.mark.parametrize("hours", [1, 11.9])
def test_alignment_accepts_history_inside_the_window(repo, snapshot, hours):
    session_offset = timedelta(hours=30)
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(
        sid,
        [Metric(XAU_METRIC, 4_000.0, "usd/troy_oz", "1.1")],
        AT - session_offset + timedelta(hours=hours),
    )
    result = run(repo, quotes_at(offset=session_offset, xau_offset=timedelta(0)))
    assert result.ok and result.xau_usd == 4_000.0


# ------------------------------------------------------- the session anchor


def test_a_zeroed_tehran_clock_is_moved_to_the_session_close():
    """TGJU's '2026-08-11 00:00:00' means the session of 11 August, not midnight.
    Anchoring on midnight would pair those prices with an ounce ~17h too early."""
    from datetime import datetime

    marker = datetime(2026, 8, 11, 0, 0, tzinfo=TEHRAN)
    anchored = session_anchor(marker)
    assert to_tehran(anchored).hour == 17
    assert to_tehran(anchored).date() == marker.date()


def test_a_real_tick_is_never_moved():
    from datetime import datetime

    tick = datetime(2026, 8, 12, 10, 12, 15, tzinfo=TEHRAN)
    assert session_anchor(tick) == tick


def test_the_close_hour_is_configurable():
    from datetime import datetime, time

    marker = datetime(2026, 8, 11, 0, 0, tzinfo=TEHRAN)
    assert to_tehran(session_anchor(marker, time(14, 30))).hour == 14
    assert parse_close("14:30") == time(14, 30)


def test_the_anchor_lets_a_closed_session_find_the_prior_evening_ounce(repo, snapshot):
    """Steady state: 21:00 and 09:00 runs bracket a 17:00 close within tolerance."""
    from datetime import datetime

    from market_monitor.timeutil import now_utc

    session_marker = datetime(2026, 8, 11, 0, 0, tzinfo=TEHRAN)
    evening_run = datetime(2026, 8, 11, 21, 0, tzinfo=TEHRAN)
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(sid, [Metric(XAU_METRIC, 4_393.47, "usd/troy_oz", "1.1")], evening_run)

    quotes = {
        Instrument.USD_IRR_FREE: make_quote(Instrument.USD_IRR_FREE, 187_800.0, session_marker),
        Instrument.GOLD_18K: make_quote(Instrument.GOLD_18K, 19_205_600.0, session_marker),
        Instrument.XAU_USD: make_quote(Instrument.XAU_USD, 4_412.73, now_utc()),
    }
    result = align(
        quotes,
        REQUIRED,
        repo,
        datetime(2026, 8, 12, 16, 0, tzinfo=TEHRAN),
        FRESHNESS,
        SESSION_WINDOW,
        XAU_TOLERANCE,
    )
    assert result.ok
    assert result.basis is AnalysisBasis.LAST_CLOSE
    assert result.xau_usd == 4_393.47
