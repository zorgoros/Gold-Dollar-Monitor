"""Replay TGJU's daily closes into the observation history (§30).

Live collection only ever knows the moment it runs, so a fresh install has no
1d/3d/7d anything, no gap distribution to calibrate §7's provisional thresholds
against, and nothing for the §28 backtester to read. TGJU publishes a daily OHLC
series per symbol going back years (docs/PROVIDERS.md, endpoint 3); this replays
it through the same store-then-derive path the live pipeline uses, so the
imported series is the same shape as the collected one — same metric keys, same
formulas, same model version.

Two things it deliberately is not:

* **Not intraday.** One row per Tehran session, stamped at the configured close.
  That is the granularity TGJU publishes, and inventing anything finer would be
  inventing observations.
* **Not a second opinion on today.** The newest history row is the previous
  session's close. Current prices come from `collect`, and a session that is
  already stored is skipped rather than written twice.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

from ..analysis.engine import analyze
from ..analysis.session import DEFAULT_SESSION_CLOSE, parse_close, session_anchor
from ..domain.enums import Instrument, SnapshotStatus
from ..domain.models import Quote, Snapshot
from ..providers.tgju import TgjuProvider
from ..settings import Settings
from ..storage.repositories import Repository
from ..timeutil import TEHRAN, now_utc
from .report import store_analytics

log = logging.getLogger(__name__)

# What `analyze` cannot compute without (analysis/engine.py). A date missing
# either of them is not a session we can reconstruct, so it is skipped whole
# rather than half-imported.
REQUIRED = (Instrument.USD_IRR_FREE, Instrument.GOLD_18K)

# Tehran and the metal keep different weeks — Saturday to Wednesday against
# Monday to Friday — so only about two thirds of Iranian sessions have an ounce
# printed the same day. The honest ounce for a Saturday close is Friday's: the
# last one the world had set when those rial prices were struck. That is the
# same reasoning analysis/session.py applies live. Carried back, never
# interpolated, and never further than this.
MAX_OUNCE_CARRY = timedelta(days=4)


@dataclass(frozen=True)
class BackfillResult:
    sessions: int
    skipped_existing: int
    skipped_no_ounce: int
    first: date | None
    last: date | None


def _ounce_at(history: dict[date, Quote], day: date) -> Quote | None:
    """The ounce that was true at that Tehran close: same day, else carried back."""
    for back in range(MAX_OUNCE_CARRY.days + 1):
        quote = history.get(day - timedelta(days=back))
        if quote is not None:
            return quote
    return None


def backfill(
    repo: Repository,
    settings: Settings,
    days: int = 365,
    provider: TgjuProvider | None = None,
    dry_run: bool = False,
) -> BackfillResult:
    """Import one snapshot per Tehran session, oldest first, and derive its metrics.

    Oldest first is load-bearing: `analyze` reads the series it is extending, so
    a day's trends and gap momentum resolve against the days already imported.
    Running it newest-first would compute every trend against an empty history.
    """
    source = provider or TgjuProvider()
    wanted = settings.instrument_list("instruments", "mandatory") + settings.instrument_list(
        "instruments", "optional"
    )
    history = {instrument: source.fetch_history(instrument) for instrument in wanted}
    ounces = history.get(Instrument.XAU_USD, {})

    sessions = sorted(set.intersection(*(set(history.get(i, {})) for i in REQUIRED)))
    if days > 0:
        earliest = now_utc().date() - timedelta(days=days)
        sessions = [day for day in sessions if day >= earliest]

    analysis_cfg = settings.section("analysis")
    close = (
        parse_close(str(analysis_cfg["tehran_session_close"]))
        if "tehran_session_close" in analysis_cfg
        else DEFAULT_SESSION_CLOSE
    )
    mandatory = settings.instrument_list("instruments", "mandatory")

    written: list[date] = []
    skipped_existing = skipped_no_ounce = 0
    for day in sessions:
        quotes: dict[Instrument, Quote] = {
            instrument: quote
            for instrument, rows in history.items()
            if instrument is not Instrument.XAU_USD and (quote := rows.get(day)) is not None
        }
        ounce = _ounce_at(ounces, day)
        if ounce is None:
            skipped_no_ounce += 1
            continue
        quotes[Instrument.XAU_USD] = ounce

        at = session_anchor(datetime.combine(day, time(), tzinfo=TEHRAN), close)
        if repo.snapshot_at_exists(at):
            skipped_existing += 1
            continue

        snapshot = Snapshot(
            snapshot_at=at,
            quotes=quotes,
            status=SnapshotStatus.COMPLETE
            if all(i in quotes for i in mandatory)
            else SnapshotStatus.PARTIAL,
        )
        written.append(day)
        if dry_run:
            continue
        # ponytail: one analyze() per session, each running ~60 indexed metric
        # lookups — a decade of history is a few minutes, which is fine for a
        # command an operator runs once. If it ever needs to be routine, the
        # lookups are what to batch, not the storage.
        snapshot = replace(snapshot, id=repo.save_snapshot(snapshot))
        store_analytics(repo, snapshot, analyze(snapshot, repo, settings.config))

    log.info(
        "backfill_finished",
        extra={
            "sessions": len(written),
            "skipped_existing": skipped_existing,
            "skipped_no_ounce": skipped_no_ounce,
            "dry_run": dry_run,
        },
    )
    return BackfillResult(
        sessions=len(written),
        skipped_existing=skipped_existing,
        skipped_no_ounce=skipped_no_ounce,
        first=written[0] if written else None,
        last=written[-1] if written else None,
    )
