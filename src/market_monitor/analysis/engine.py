"""Snapshot -> metrics, trends, signals. The one place the pieces are combined."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ..domain.constants import FORMULA_VERSION
from ..domain.enums import Instrument, QualityStatus
from ..domain.models import Metric, Signal, Snapshot
from ..storage.repositories import Repository
from .formulas import emami_coin_intrinsic, gap_pct, gold_implied_usd, theoretical_gold_18k
from .signals import Bands, coin_signal, gold_signal, usd_signal
from .trends import direction, gap_momentum, trends

TREND_HORIZONS = ("1d", "3d", "7d")

# Metric names are the time-series keys. Renaming one breaks history, so they
# are written once here and read everywhere else.
USD_MARKET = "usd_market"
USD_IMPLIED = "usd_gold_implied"
USD_GAP = "usd_gap_pct"
GOLD_MARKET = "gold_18k_market"
GOLD_THEORETICAL = "gold_18_theoretical"
GOLD_GAP = "gold_gap_pct"
XAU = "xau_usd"
COIN_MARKET = "coin_market"
COIN_INTRINSIC = "coin_intrinsic"
COIN_PREMIUM = "coin_premium_pct"


@dataclass(frozen=True)
class Analysis:
    snapshot: Snapshot
    as_of: datetime
    metrics: dict[str, float]
    trends: dict[str, dict[str, float | None]]
    signals: list[Signal]
    model_version: str
    warnings: list[str] = field(default_factory=list)
    degraded: bool = False

    def metric_rows(self) -> list[Metric]:
        units = {
            USD_MARKET: "toman/usd",
            USD_IMPLIED: "toman/usd",
            GOLD_MARKET: "toman/gram",
            GOLD_THEORETICAL: "toman/gram",
            XAU: "usd/troy_oz",
            COIN_MARKET: "toman/coin",
            COIN_INTRINSIC: "toman/coin",
        }
        return [
            Metric(name, value, units.get(name, "pct"), self.model_version)
            for name, value in self.metrics.items()
        ]


def analyze(
    snapshot: Snapshot,
    repo: Repository,
    config: dict[str, Any],
    warnings: list[str] | None = None,
) -> Analysis:
    analysis_cfg = config.get("analysis", {})
    bands = Bands.from_config(analysis_cfg)
    tolerance_pct = float(analysis_cfg.get("gap_expansion_tolerance_pct", 0.25))
    trend_tolerance = timedelta(hours=float(analysis_cfg.get("trend_tolerance_hours", 12)))
    model_version = str(config.get("model_version", FORMULA_VERSION))
    now = snapshot.snapshot_at

    usd = snapshot.require(Instrument.USD_IRR_FREE)
    gold = snapshot.require(Instrument.GOLD_18K)
    xau = snapshot.require(Instrument.XAU_USD)

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

    coin = snapshot.value(Instrument.EMAMI_COIN)
    if coin is not None:
        intrinsic = emami_coin_intrinsic(xau, usd)
        metrics[COIN_MARKET] = coin
        metrics[COIN_INTRINSIC] = intrinsic
        metrics[COIN_PREMIUM] = gap_pct(coin, intrinsic)

    computed_trends = {
        name: trends(repo, name, value, now, TREND_HORIZONS, trend_tolerance)
        for name, value in metrics.items()
    }

    degraded = any(q.quality_status is not QualityStatus.OK for q in snapshot.quotes.values())
    implied_dir = direction(computed_trends[USD_IMPLIED]["1d"], tolerance_pct)
    xau_dir = direction(computed_trends[XAU]["1d"], tolerance_pct)
    usd_dir = direction(computed_trends[USD_MARKET]["1d"], tolerance_pct)

    past_gap = repo.metric_near(USD_GAP, now - timedelta(days=1), trend_tolerance)
    momentum = gap_momentum(metrics[USD_GAP], past_gap[0] if past_gap else None, tolerance_pct)

    signals = [
        usd_signal(metrics[USD_GAP], implied_dir, momentum, bands, now, degraded),
        gold_signal(metrics[GOLD_GAP], xau_dir, usd_dir, bands, now, degraded),
    ]
    if COIN_PREMIUM in metrics:
        signals.append(coin_signal(metrics[COIN_PREMIUM], bands, now, degraded))

    return Analysis(
        snapshot=snapshot,
        as_of=now,
        metrics=metrics,
        trends=computed_trends,
        signals=signals,
        model_version=model_version,
        warnings=list(warnings or []),
        degraded=degraded,
    )
