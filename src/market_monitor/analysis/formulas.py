"""The four V1 relationships (ARCHITECTURE.md §4). Pure, deterministic, no I/O.

Implied USD and theoretical gold are the same relationship read in opposite
directions — algebraic inversions. Never score them as independent evidence.
"""

from __future__ import annotations

from ..domain.constants import (
    EMAMI_COIN_PURE_GRAMS,
    GOLD_18_CONVERSION,
    TROY_OUNCE_GRAMS,
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


def gap_pct(market: float, reference: float) -> float:
    """Percentage by which a market price sits above (+) or below (-) a reference."""
    m = _positive("market", market)
    r = _positive("reference", reference)
    return (m / r - 1.0) * 100.0


def emami_coin_intrinsic(xau_usd: float, usd_market_toman: float) -> float:
    """Gold content of one Emami coin valued at the world ounce and market USD.

    Melt value only — it excludes the minting and demand premium that makes up
    the coin's bubble, which is the point of comparing the two.
    """
    xau = _positive("xau_usd", xau_usd)
    usd = _positive("usd_market", usd_market_toman)
    toman_per_gram_pure = xau * usd / TROY_OUNCE_GRAMS
    return toman_per_gram_pure * EMAMI_COIN_PURE_GRAMS
