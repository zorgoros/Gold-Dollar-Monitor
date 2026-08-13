"""Snapshot -> metrics, trends, signals. The one place the pieces are combined."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ..domain.constants import FORMULA_VERSION, USD_AED_PEG
from ..domain.enums import AnalysisBasis, Instrument, QualityStatus
from ..domain.models import Metric, Signal, Snapshot
from ..storage.repositories import Repository
from .formulas import (
    aed_implied_usd,
    emami_coin_intrinsic_domestic,
    emami_coin_intrinsic_world,
    gap_pct,
    gold_implied_usd,
    pure_gold_toman_per_gram,
    theoretical_gold_18k,
)
from .session import XAU_METRIC, Alignment
from .signals import Bands, coin_signal, gold_signal, usd_signal
from .trends import direction, gap_momentum, pct_change, trends

TREND_HORIZONS = ("1d", "3d", "7d")

# Metric names are the time-series keys. Renaming one breaks history, so they
# are written once here and read everywhere else.
#
# `usd_gap_pct` predates v1.1 and means the *gold* divergence. It keeps its name
# because 70 stored rows and every trend lookup depend on it; the AED
# divergence is a new series with an explicit name. docs/FORMULAS.md states the
# mapping so the two are never confused.
USD_MARKET = "usd_market"
USD_IMPLIED = "usd_gold_implied"
USD_GAP = "usd_gap_pct"
USD_AED_IMPLIED = "usd_aed_implied"
AED_GAP = "aed_usd_gap_pct"
GOLD_MARKET = "gold_18k_market"
GOLD_THEORETICAL = "gold_18_theoretical"
GOLD_GAP = "gold_gap_pct"
XAU = XAU_METRIC
COIN_MARKET = "coin_market"
GOLD_PURE = "gold_pure_domestic"
# v1.2 renamed the published coin series rather than changing what an existing
# key means. `coin_intrinsic` / `coin_premium_pct` are retired: rows written
# under them are model version 1.1 or earlier and stay valid on their own terms.
COIN_INTRINSIC_DOMESTIC = "coin_intrinsic_domestic"
COIN_PREMIUM_DOMESTIC = "coin_premium_domestic_pct"
# Computed and stored, never published. It inherits `gold_gap_pct` in full, so
# reading it beside the gold section double-counts one divergence
# (docs/FORMULAS.md, docs/BACKTESTING.md).
COIN_INTRINSIC_WORLD = "coin_intrinsic_world"
COIN_PREMIUM_WORLD = "coin_premium_world_pct"

# Display-and-history instruments (§13). Stored under their instrument symbol so
# the raw series is queryable later even while nothing analytical reads it.
FX_METRICS: dict[Instrument, str] = {
    Instrument.AED_IRT: Instrument.AED_IRT.value,
    Instrument.EUR_IRT: Instrument.EUR_IRT.value,
    Instrument.TRY_IRT: Instrument.TRY_IRT.value,
    Instrument.JPY_IRT: Instrument.JPY_IRT.value,
}

# Which time series carries each instrument's market price. One mapping, so a
# report surface never has to guess the key for an instrument.
INSTRUMENT_METRIC: dict[Instrument, str] = {
    Instrument.USD_IRR_FREE: USD_MARKET,
    Instrument.GOLD_18K: GOLD_MARKET,
    Instrument.XAU_USD: XAU,
    Instrument.EMAMI_COIN: COIN_MARKET,
    **FX_METRICS,
}

METRIC_UNITS: dict[str, str] = {
    USD_MARKET: "toman/usd",
    USD_IMPLIED: "toman/usd",
    USD_AED_IMPLIED: "toman/usd",
    GOLD_MARKET: "toman/gram",
    GOLD_THEORETICAL: "toman/gram",
    XAU: "usd/troy_oz",
    COIN_MARKET: "toman/coin",
    GOLD_PURE: "toman/gram",
    COIN_INTRINSIC_DOMESTIC: "toman/coin",
    COIN_INTRINSIC_WORLD: "toman/coin",
    Instrument.AED_IRT.value: "toman/aed",
    Instrument.EUR_IRT.value: "toman/eur",
    Instrument.TRY_IRT.value: "toman/try",
    Instrument.JPY_IRT.value: "toman/jpy",
}


@dataclass(frozen=True)
class Analysis:
    snapshot: Snapshot
    as_of: datetime
    metrics: dict[str, float]
    trends: dict[str, dict[str, float | None]]
    signals: list[Signal]
    model_version: str
    # Percentage change against the previously stored value of each metric —
    # "since the last report", which is a different question from a fixed 1d
    # lookback. None where there is no earlier observation (§18, §20).
    changes: dict[str, float | None] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    degraded: bool = False
    basis: AnalysisBasis = AnalysisBasis.LIVE
    # The instant the analysis describes. Equal to `as_of` for a live session;
    # the Tehran close instant when the basis is LAST_CLOSE.
    reference_at: datetime | None = None

    def metric_rows(self) -> list[Metric]:
        return [
            Metric(name, value, METRIC_UNITS.get(name, "pct"), self.model_version)
            for name, value in self.metrics.items()
        ]


def analyze(
    snapshot: Snapshot,
    repo: Repository,
    config: dict[str, Any],
    warnings: list[str] | None = None,
    alignment: Alignment | None = None,
) -> Analysis:
    """Compute every metric the report surfaces may consume.

    `alignment` carries the ounce chosen by `session.align` and the basis it
    belongs to. Passing None reads the snapshot's own ounce and calls it live —
    that path is for re-rendering a stored snapshot, never for the scheduled
    publication path, which gates first (jobs/report.py).
    """
    analysis_cfg = config.get("analysis", {})
    bands = Bands.from_config(analysis_cfg)
    tolerance_pct = float(analysis_cfg.get("gap_expansion_tolerance_pct", 0.25))
    trend_tolerance = timedelta(hours=float(analysis_cfg.get("trend_tolerance_hours", 12)))
    peg = float(config.get("peg", {}).get("usd_aed", USD_AED_PEG))
    model_version = str(config.get("model_version", FORMULA_VERSION))
    now = snapshot.snapshot_at

    usd = snapshot.require(Instrument.USD_IRR_FREE)
    gold = snapshot.require(Instrument.GOLD_18K)
    xau = alignment.xau_usd if alignment else snapshot.require(Instrument.XAU_USD)
    basis = alignment.basis if alignment else AnalysisBasis.LIVE
    reference_at = alignment.reference_at if alignment else now

    implied = gold_implied_usd(gold, xau)
    theoretical = theoretical_gold_18k(xau, usd)
    metrics: dict[str, float] = {
        USD_MARKET: usd,
        USD_IMPLIED: implied,
        USD_GAP: gap_pct(usd, implied),
        GOLD_MARKET: gold,
        GOLD_THEORETICAL: theoretical,
        GOLD_GAP: gap_pct(gold, theoretical),
        XAU: xau,
    }

    # AED is a section-level input: present it when it is there, drop the
    # section when it is not. It never blocks the gold relationship.
    aed = snapshot.value(Instrument.AED_IRT)
    if aed is not None:
        aed_implied = aed_implied_usd(aed, peg)
        metrics[USD_AED_IMPLIED] = aed_implied
        metrics[AED_GAP] = gap_pct(usd, aed_implied)

    coin = snapshot.value(Instrument.EMAMI_COIN)
    if coin is not None:
        # The published premium is against domestic gold; the world route is
        # stored beside it as a separate, non-public series (§23, EXTENSIONS Q).
        pure_gram = pure_gold_toman_per_gram(snapshot.value(Instrument.GOLD_24K), gold)
        domestic = emami_coin_intrinsic_domestic(pure_gram)
        world = emami_coin_intrinsic_world(xau, usd)
        metrics[COIN_MARKET] = coin
        metrics[GOLD_PURE] = pure_gram
        metrics[COIN_INTRINSIC_DOMESTIC] = domestic
        metrics[COIN_PREMIUM_DOMESTIC] = gap_pct(coin, domestic)
        metrics[COIN_INTRINSIC_WORLD] = world
        metrics[COIN_PREMIUM_WORLD] = gap_pct(coin, world)

    # Store what we do not yet analyse. Today these only reach the snapshot
    # board; the point is that the history exists when a cross-rate study wants
    # it (§27, EXTENSIONS cross-rate research).
    for instrument, name in FX_METRICS.items():
        value = snapshot.value(instrument)
        if value is not None:
            metrics[name] = value

    computed_trends = {
        name: trends(repo, name, value, now, TREND_HORIZONS, trend_tolerance)
        for name, value in metrics.items()
    }
    changes: dict[str, float | None] = {}
    for name, value in metrics.items():
        previous = repo.metric_before(name, now)
        changes[name] = pct_change(value, previous[0]) if previous else None

    degraded = any(q.quality_status is not QualityStatus.OK for q in snapshot.quotes.values())
    implied_dir = direction(computed_trends[USD_IMPLIED]["1d"], tolerance_pct)
    xau_dir = direction(computed_trends[XAU]["1d"], tolerance_pct)
    usd_dir = direction(computed_trends[USD_MARKET]["1d"], tolerance_pct)

    past_gap = repo.metric_near(USD_GAP, now - timedelta(days=1), trend_tolerance)
    momentum = gap_momentum(metrics[USD_GAP], past_gap[0] if past_gap else None, tolerance_pct)

    signals = [
        usd_signal(
            metrics[USD_GAP],
            implied_dir,
            momentum,
            bands,
            now,
            degraded,
            aed_gap=metrics.get(AED_GAP),
            basis=basis,
        ),
        gold_signal(metrics[GOLD_GAP], xau_dir, usd_dir, bands, now, degraded),
    ]
    if COIN_PREMIUM_DOMESTIC in metrics:
        signals.append(coin_signal(metrics[COIN_PREMIUM_DOMESTIC], bands, now, degraded))

    return Analysis(
        snapshot=snapshot,
        as_of=now,
        metrics=metrics,
        trends=computed_trends,
        signals=signals,
        model_version=model_version,
        changes=changes,
        warnings=list(warnings or []),
        degraded=degraded,
        basis=basis,
        reference_at=reference_at,
    )
