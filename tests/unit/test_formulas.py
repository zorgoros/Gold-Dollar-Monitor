"""Golden vectors. The numbers come from ARCHITECTURE.md's own §15 example report."""

import pytest

from market_monitor.analysis.formulas import gap_pct, gold_implied_usd, theoretical_gold_18k
from market_monitor.domain.constants import GOLD_18_CONVERSION
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
