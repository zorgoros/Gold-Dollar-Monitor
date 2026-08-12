"""Which market session the inputs belong to, and which ounce goes with them.

The defect this module exists to stop: TGJU's rial instruments only tick during
Tehran market hours, while `ons` ticks around the clock. Combining yesterday's
Iranian close with a live world ounce produces a ratio that is not a market
observation at all — it measures the ounce moving after Tehran shut. That
artifact is what made the Emami premium read −2.8% on 2026-08-12, a coin
apparently trading below its own metal content.

So the ounce is not taken live when the Iranian inputs are a previous close. It
is looked up from stored history at the Iranian session's own instant, and if no
sufficiently aligned observation exists the analysis is not published at all.
Snapshot reports are unaffected — they quote prices, they do not relate them.

Nothing here rewrites a quote. Source timestamps and quality flags are stored
exactly as the provider gave them; alignment is an analysis-time choice about
*which* stored observation to read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from ..domain.enums import AnalysisBasis, GateCode, Instrument
from ..domain.models import Quote
from ..storage.repositories import Repository
from ..timeutil import TEHRAN, to_tehran

# When TGJU reports a closed session it zeroes the clock: the session of
# 2026-08-11 is marked `2026-08-11 00:00:00`. That is a date, not a closing
# bell, and anchoring the ounce lookup on it would systematically pick an ounce
# from ~17 hours before the prices it is being paired with. The marker is
# therefore moved to the session's actual close before anything is aligned to
# it. Configurable, because it is an assumption about a market's hours.
DEFAULT_SESSION_CLOSE = time(17, 0)

# The metric key for the world ounce time series. Defined here rather than in
# engine.py because alignment reads it and engine imports it back — renaming it
# breaks every historical lookup, so it has exactly one home.
XAU_METRIC = "xau_usd"

# Instruments quoted by TGJU on the Tehran session clock. `xau_usd` is
# deliberately absent: it is the global input this module aligns *against*.
TEHRAN_SESSION_INSTRUMENTS = frozenset(
    {
        Instrument.USD_IRR_FREE,
        Instrument.GOLD_18K,
        Instrument.EMAMI_COIN,
        Instrument.AED_IRT,
        Instrument.EUR_IRT,
        Instrument.TRY_IRT,
        Instrument.JPY_IRT,
    }
)


@dataclass(frozen=True)
class Alignment:
    """The ounce the analysis must use, and the session it belongs to."""

    ok: bool
    basis: AnalysisBasis
    xau_usd: float
    xau_observed_at: datetime
    reference_at: datetime
    codes: list[GateCode]
    diagnostics: list[str]


def _fresh(quote: Quote, now: datetime, limits: dict[str, float], default: float = 20.0) -> bool:
    limit = timedelta(minutes=float(limits.get(quote.instrument.value, default)))
    return quote.age_seconds(now) <= limit.total_seconds()


def session_anchor(observed_at: datetime, close: time = DEFAULT_SESSION_CLOSE) -> datetime:
    """The instant a Tehran session's prices were actually set.

    A zeroed Tehran clock is TGJU's previous-close marker, so it is moved to the
    configured close time on that date. Any other timestamp is a real tick and
    is returned untouched.
    """
    local = to_tehran(observed_at)
    if (local.hour, local.minute, local.second) != (0, 0, 0):
        return observed_at
    return local.replace(hour=close.hour, minute=close.minute, tzinfo=TEHRAN)


def parse_close(text: str) -> time:
    hour, _, minute = str(text).partition(":")
    return time(int(hour), int(minute or 0))


def align(
    quotes: dict[Instrument, Quote],
    required: list[Instrument],
    repo: Repository,
    now: datetime,
    freshness: dict[str, float],
    session_window: timedelta,
    xau_tolerance: timedelta,
    session_close: time = DEFAULT_SESSION_CLOSE,
) -> Alignment:
    """Decide the analysis basis and pick the ounce that belongs to it.

    `required` names the instruments whose staleness may block publication —
    the inputs to the core USD/gold relationship. Section-level inputs such as
    AED and the coin are not listed: a stale dirham drops its own section
    rather than the whole report (§16, resolved 2026-08-12).
    """
    codes: list[GateCode] = []
    diagnostics: list[str] = []

    xau = quotes.get(Instrument.XAU_USD)
    session = [quotes[i] for i in required if i in quotes and i in TEHRAN_SESSION_INSTRUMENTS]
    if xau is None or not session:
        return Alignment(
            False,
            AnalysisBasis.LIVE,
            0.0,
            now,
            now,
            [GateCode.MISSING_MANDATORY],
            ["no world ounce or no Tehran-session input to align it to"],
        )

    observed = [q.observed_at for q in session]
    spread = max(observed) - min(observed)
    reference_at = session_anchor(max(observed), session_close)

    # Whatever the session, the Iranian inputs must agree with each other. A
    # dollar from today and a gold price from last week is not a market state.
    if spread > session_window:
        stale_pair = ", ".join(sorted(q.instrument.value for q in session))
        return Alignment(
            False,
            AnalysisBasis.LIVE,
            0.0,
            xau.observed_at,
            reference_at,
            [GateCode.SESSION_INCOHERENT],
            [f"Tehran inputs span {int(spread.total_seconds() / 60)} minutes ({stale_pair})"],
        )

    session_live = all(_fresh(q, now, freshness) for q in session)
    xau_live = _fresh(xau, now, freshness, default=30.0)

    if session_live and xau_live:
        return Alignment(
            True, AnalysisBasis.LIVE, xau.normalized_value, xau.observed_at, reference_at, codes, []
        )

    # Tehran is closed (or the ounce feed lagged). Do not reach for the live
    # ounce — find the one that was true when these Iranian prices were set.
    #
    # ponytail: `session_close` is a single configured hour, not a trading
    # calendar — it does not know holidays, Ramadan hours, or an early close, so
    # the anchor can be off by a couple of hours on an unusual day and
    # `xau_tolerance` absorbs that. Upgrade path if that proves too coarse: a
    # real Tehran session calendar mapping each date to its own close instant.
    aligned = repo.metric_near(XAU_METRIC, reference_at, xau_tolerance)
    if aligned is None:
        hours = int(xau_tolerance.total_seconds() / 3600)
        return Alignment(
            False,
            AnalysisBasis.LAST_CLOSE,
            0.0,
            xau.observed_at,
            reference_at,
            [GateCode.XAU_NOT_ALIGNED],
            [
                f"no stored xau_usd within {hours}h of the Tehran session at "
                f"{reference_at.isoformat()}; refusing to pair it with the live ounce"
            ],
        )

    value, at = aligned
    codes.append(GateCode.STALE_REQUIRED_INPUT)
    diagnostics.append(
        f"analysis on last close: Tehran session {reference_at.isoformat()}, "
        f"ounce aligned to {at.isoformat()} (live ounce {xau.normalized_value:,.2f} not used)"
    )
    return Alignment(True, AnalysisBasis.LAST_CLOSE, value, at, reference_at, codes, diagnostics)
