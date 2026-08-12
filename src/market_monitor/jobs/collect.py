"""Fetch -> validate -> store. Raw observations are preserved even when the
snapshot is not publishable: a failed run is data too.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import timedelta

from ..domain.enums import Instrument
from ..domain.errors import InvalidQuote, MarketMonitorError
from ..domain.models import Quote, Snapshot
from ..normalization.validators import SnapshotVerdict, validate_quote, validate_snapshot
from ..providers.base import MarketDataProvider
from ..providers.gold_api import GoldApiProvider
from ..providers.tgju import TgjuProvider
from ..settings import Settings
from ..storage.repositories import Repository
from ..timeutil import now_utc

log = logging.getLogger(__name__)

PROVIDERS: dict[str, type[TgjuProvider] | type[GoldApiProvider]] = {
    "tgju": TgjuProvider,
    "gold-api": GoldApiProvider,
}


def build_chain(settings: Settings) -> list[MarketDataProvider]:
    """Distinct providers named in config, primaries first."""
    configured = settings.section("providers")
    ordered: list[str] = []
    for key in ("primary", "fallback"):
        for entry in configured.values():
            name = entry.get(key)
            if name and name not in ordered:
                ordered.append(name)
    return [PROVIDERS[name]() for name in ordered if name in PROVIDERS]


def collect(
    repo: Repository,
    settings: Settings,
    providers: list[MarketDataProvider] | None = None,
) -> tuple[Snapshot, SnapshotVerdict, int]:
    """Build one snapshot. Returns the snapshot, its verdict, and its row id."""
    chain = providers if providers is not None else build_chain(settings)
    mandatory = settings.instrument_list("instruments", "mandatory")
    optional = settings.instrument_list("instruments", "optional")
    # Collection is the widest of the three sets on purpose: an instrument that
    # is neither displayed nor analysed is still stored, because the one thing
    # that cannot be back-filled later is a price nobody wrote down (§27).
    wanted = mandatory + optional

    now = now_utc()
    freshness = settings.section("freshness")
    max_jump = float(settings.section("validation").get("max_jump_pct", 25.0))

    collected: dict[Instrument, Quote] = {}
    for provider in chain:
        missing = [i for i in wanted if i not in collected]
        if not missing:
            break
        try:
            fetched = provider.fetch_quotes(missing)
        except MarketMonitorError as exc:
            log.warning("provider_failed", extra={"provider": provider.name, "error": str(exc)})
            continue
        for instrument, quote in fetched.items():
            try:
                collected[instrument] = validate_quote(
                    quote,
                    now,
                    timedelta(minutes=float(freshness.get(instrument.value, 20))),
                    repo.last_value(instrument),
                    max_jump,
                )
            except InvalidQuote as exc:
                log.warning(
                    "quote_rejected", extra={"instrument": instrument.value, "error": str(exc)}
                )

    verdict = validate_snapshot(
        collected,
        mandatory,
        now,
        timedelta(minutes=float(freshness.get("snapshot_window_minutes", 15))),
    )
    snapshot = Snapshot(snapshot_at=now, quotes=collected, status=verdict.status)
    if not collected:
        return snapshot, verdict, 0
    snapshot_id = repo.save_snapshot(snapshot)
    # The id has to travel with the snapshot: everything downstream keys metrics
    # and signals off it, and a snapshot without one writes no time series at all.
    return replace(snapshot, id=snapshot_id), verdict, snapshot_id
