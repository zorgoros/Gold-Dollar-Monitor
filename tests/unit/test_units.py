import pytest

from market_monitor.domain.enums import Instrument, Unit
from market_monitor.domain.errors import UnitNormalizationError
from market_monitor.normalization.units import (
    ounce_to_gram,
    parse_number,
    rial_to_toman,
    to_canonical,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,854,000", 1_854_000.0),
        ("۱۹,۱۵۰,۰۰۰", 19_150_000.0),
        ("4382.5", 4382.5),
        (" 1 854 000 ", 1_854_000.0),
    ],
)
def test_parse_number_handles_separators_and_persian_digits(raw, expected):
    assert parse_number(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "abc", "12,3x4"])
def test_parse_number_rejects_junk_instead_of_guessing(raw):
    with pytest.raises(UnitNormalizationError):
        parse_number(raw)


def test_rial_to_toman_divides_by_ten():
    assert rial_to_toman(1_854_000.0) == 185_400.0


def test_ounce_to_gram_uses_the_troy_constant():
    assert ounce_to_gram(31.1034768) == pytest.approx(1.0)


def test_to_canonical_converts_rial_quotes():
    value, unit = to_canonical(Instrument.USD_IRR_FREE, 1_854_000.0, Unit.RIAL_PER_USD)
    assert (value, unit) == (185_400.0, Unit.TOMAN_PER_USD)


def test_to_canonical_passes_through_a_canonical_quote():
    value, unit = to_canonical(Instrument.XAU_USD, 4382.0, Unit.USD_PER_TROY_OUNCE)
    assert (value, unit) == (4382.0, Unit.USD_PER_TROY_OUNCE)


def test_to_canonical_refuses_a_conversion_it_does_not_know():
    with pytest.raises(UnitNormalizationError):
        to_canonical(Instrument.GOLD_18K, 4382.0, Unit.USD_PER_TROY_OUNCE)
