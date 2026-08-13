"""The price relationships (ARCHITECTURE.md §4). Pure, deterministic, no I/O.

Implied USD and theoretical gold are the same relationship read in opposite
directions — algebraic inversions. Never score them as independent evidence.

The AED-implied rate is the one genuinely *independent* reference added in
v1.1: it comes from a different market through a different mechanism (a
currency peg, not a metal content), so it and the gold-implied rate may be
compared with each other. They are still never averaged into one number — see
§11 and the composite entry in EXTENSIONS.md.
"""

from __future__ import annotations

from ..domain.constants import (
    EMAMI_COIN_PURE_GRAMS,
    GOLD_18_CONVERSION,
    GOLD_18_PURITY,
    TROY_OUNCE_GRAMS,
    USD_AED_PEG,
)
from ..domain.errors import AnalysisError


def _positive(name: str, value: float) -> float:
    if not isinstance(value, int | float) or value != value or value <= 0:
        raise AnalysisError(f"{name} must be a positive number, got {value!r}")
    return float(value)


def gold_implied_usd(gold_18k_toman_per_gram: float, xau_usd: float) -> float:
    """USD/toman rate embedded in the Iranian 18K market, given the world ounce.

    An implied rate — not an intrinsic or fair value for USD.
    """
    gold = _positive("gold_18k", gold_18k_toman_per_gram)
    xau = _positive("xau_usd", xau_usd)
    return gold * GOLD_18_CONVERSION / xau


def theoretical_gold_18k(xau_usd: float, usd_market_toman: float) -> float:
    """Toman per gram of 18K implied by the world ounce and the market USD rate."""
    xau = _positive("xau_usd", xau_usd)
    usd = _positive("usd_market", usd_market_toman)
    return xau * usd / GOLD_18_CONVERSION


def aed_implied_usd(aed_toman: float, peg: float = USD_AED_PEG) -> float:
    """USD/toman implied by the domestic dirham market and the USD/AED peg.

    An implied rate, like the gold one — the dirham's peg is a policy commitment
    of another central bank, not a guarantee about the toman.
    """
    aed = _positive("aed_irt", aed_toman)
    ratio = _positive("usd_aed_peg", peg)
    return aed * ratio


def gap_pct(market: float, reference: float) -> float:
    """Percentage by which a market price sits above (+) or below (-) a reference."""
    m = _positive("market", market)
    r = _positive("reference", reference)
    return (m / r - 1.0) * 100.0


def pure_gold_toman_per_gram(gold_24k_toman: float | None, gold_18k_toman: float) -> float:
    """Domestic price of one gram of pure gold.

    TGJU's `geram24` is the direct quote and the preferred input. It is itself
    derived from `geram18` — the two agree to 0.0007% — so the 18K fallback is
    *equivalent*, not degraded. It exists because a provider symbol can go
    missing, not because it is worse.
    """
    if gold_24k_toman is not None:
        return _positive("gold_24k", gold_24k_toman)
    return _positive("gold_18k", gold_18k_toman) / GOLD_18_PURITY


def emami_coin_intrinsic_domestic(pure_gold_toman_per_gram: float) -> float:
    """Gold content of one Emami coin at the price gold actually trades at in Tehran.

    This is the حباب Iranian market participants mean, and the number the report
    publishes. It is independent of the USD/gold divergence stated one section
    above, so coin and gold are two findings rather than one restated twice.

    Verified against TGJU's own `sekee_real` to within 0.001% (docs/FORMULAS.md).
    """
    per_gram = _positive("pure_gold_per_gram", pure_gold_toman_per_gram)
    return per_gram * EMAMI_COIN_PURE_GRAMS


def emami_coin_intrinsic_world(xau_usd: float, usd_market_toman: float) -> float:
    """The coin's gold valued through the world ounce at the market USD rate.

    **Not published.** It inherits `gold_gap_pct` in full, which is what made it
    read as a coin trading below its own metal content while the domestic route
    read a normal positive premium. Kept as an analytical series because
    "coin against world gold" is a real arbitrage measure — just not the حباب.
    """
    xau = _positive("xau_usd", xau_usd)
    usd = _positive("usd_market", usd_market_toman)
    toman_per_gram_pure = xau * usd / TROY_OUNCE_GRAMS
    return toman_per_gram_pure * EMAMI_COIN_PURE_GRAMS
