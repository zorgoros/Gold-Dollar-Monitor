"""Golden vectors. The numbers come from ARCHITECTURE.md's own §15 example report."""

import pytest

from market_monitor.analysis.formulas import (
    aed_implied_usd,
    emami_coin_intrinsic,
    gap_pct,
    gold_implied_usd,
    theoretical_gold_18k,
)
from market_monitor.domain.constants import (
    EMAMI_COIN_GRAMS,
    EMAMI_COIN_PURE_GRAMS,
    EMAMI_COIN_PURITY,
    GOLD_18_CONVERSION,
    USD_AED_PEG,
)
from market_monitor.domain.errors import AnalysisError

USD_MARKET = 185_400.0
GOLD_18K = 19_150_000.0
XAU = 4_382.0


def test_conversion_constant_is_derived_not_typed():
    assert GOLD_18_CONVERSION == pytest.approx(41.4713024, abs=1e-7)


def test_gold_implied_usd_matches_published_example():
    # §15 prints 181,200 toman (rounded to the hundred).
    assert gold_implied_usd(GOLD_18K, XAU) == pytest.approx(181_236.0, abs=50.0)


def test_theoretical_gold_matches_published_example():
    # §15 prints 19,590,000 toman per gram.
    assert theoretical_gold_18k(XAU, USD_MARKET) == pytest.approx(19_590_000.0, rel=1e-4)


def test_usd_gap_is_positive_when_market_above_implied():
    implied = gold_implied_usd(GOLD_18K, XAU)
    assert gap_pct(USD_MARKET, implied) == pytest.approx(2.30, abs=0.05)


def test_gold_gap_is_negative_when_market_below_theoretical():
    theoretical = theoretical_gold_18k(XAU, USD_MARKET)
    assert gap_pct(GOLD_18K, theoretical) == pytest.approx(-2.25, abs=0.05)


def test_the_two_formulas_are_one_relationship():
    """Round-tripping must return the input: they are algebraic inversions."""
    implied = gold_implied_usd(GOLD_18K, XAU)
    assert theoretical_gold_18k(XAU, implied) == pytest.approx(GOLD_18K, rel=1e-9)


def test_zero_gap_when_market_equals_reference():
    assert gap_pct(1000.0, 1000.0) == 0.0


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan")])
def test_non_positive_inputs_are_rejected_not_silently_computed(bad):
    with pytest.raises(AnalysisError):
        gold_implied_usd(bad, XAU)
    with pytest.raises(AnalysisError):
        theoretical_gold_18k(XAU, bad)
    with pytest.raises(AnalysisError):
        gap_pct(bad, 1.0)


# ------------------------------------------------- AED-implied USD (v1.1, §7)

AED_MARKET = 51_161.0  # toman per dirham, live 2026-08-12


def test_aed_implied_usd_uses_the_peg():
    """51,161 x 3.6725 = 187,889, against a market USD of 187,800 that day."""
    assert aed_implied_usd(AED_MARKET) == pytest.approx(187_889.0, abs=1.0)


def test_the_peg_default_is_the_cbuae_rate():
    assert USD_AED_PEG == 3.6725


def test_the_peg_is_a_parameter_not_a_literal():
    assert aed_implied_usd(50_000.0, peg=4.0) == 200_000.0


def test_aed_gap_against_the_live_market_is_small():
    """Sanity on the relationship itself: a pegged currency should imply a rate
    close to the free-market one, and on 2026-08-12 it did, to within 0.05%."""
    assert gap_pct(187_800.0, aed_implied_usd(AED_MARKET)) == pytest.approx(-0.047, abs=0.01)


def test_aed_implied_is_independent_of_the_gold_relationship():
    """Unlike implied USD and theoretical gold, these two are NOT inversions of
    one equation — which is why §9 may show them side by side."""
    from_gold = gold_implied_usd(GOLD_18K, XAU)
    from_aed = aed_implied_usd(AED_MARKET)
    assert from_gold != pytest.approx(from_aed, rel=1e-6)


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan")])
def test_aed_rejects_unusable_inputs(bad):
    with pytest.raises(AnalysisError):
        aed_implied_usd(bad)
    with pytest.raises(AnalysisError):
        aed_implied_usd(AED_MARKET, peg=bad)


# --------------------------------------------------- coin audit (v1.1, §23)


def test_coin_constants_match_the_bahar_azadi_specification():
    """8.133 g gross at 900 fineness = 7.3197 g of fine gold. Audited 2026-08-12."""
    assert EMAMI_COIN_GRAMS == 8.133
    assert EMAMI_COIN_PURITY == 0.900
    assert EMAMI_COIN_PURE_GRAMS == pytest.approx(7.3197, abs=1e-4)


def test_coin_value_is_its_fine_gold_content_at_the_market_rate():
    """Recomputed independently of the implementation, from first principles."""
    expected = (XAU * USD_MARKET / 31.1034768) * (8.133 * 0.900)
    assert emami_coin_intrinsic(XAU, USD_MARKET) == pytest.approx(expected, rel=1e-12)


def test_coin_value_scales_linearly_with_both_inputs():
    base = emami_coin_intrinsic(XAU, USD_MARKET)
    assert emami_coin_intrinsic(XAU * 2, USD_MARKET) == pytest.approx(base * 2)
    assert emami_coin_intrinsic(XAU, USD_MARKET * 2) == pytest.approx(base * 2)


def test_coin_premium_against_the_live_market_is_plausible():
    """Live 2026-08-12: coin 189,485,000 against ~195.0M of gold content.

    The negative premium is real and is a *temporal* artifact, not a formula
    error — `sekee` was yesterday's Tehran close while `ons` was live. It is the
    exact defect analysis/session.py refuses to publish (docs/FORMULAS.md).
    """
    intrinsic = emami_coin_intrinsic(4_412.73, 187_800.0)
    assert intrinsic == pytest.approx(195_023_653.0, rel=1e-4)
    assert gap_pct(189_485_000.0, intrinsic) == pytest.approx(-2.84, abs=0.05)
